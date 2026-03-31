"""
Invoice Sync Service for KSeF 2.0.

Orchestrates batch export of invoices from KSeF, parses FA(3) XML,
and upserts results into the local PostgreSQL database.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from ksef2 import Client
from ksef2.domain.models import InvoicesFilter
from sqlalchemy import Row, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models.company import Company
from app.services.fa3_parser import FA3ParseError, FA3Parser
from app.services.ksef_auth import CryptoUtil, _resolve_environment

logger = logging.getLogger(__name__)


InvoicesRole = Literal["buyer", "seller", "third_subject", "authorized_subject"]

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class InvoiceSyncError(Exception):
    """Raised when the invoice sync process encounters an unrecoverable error."""


class InvoiceSyncPermanentError(InvoiceSyncError):
    """Raised for failures that must never be retried (bad config, missing entity, wrong key)."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class InvoiceSyncService:
    """Async service that synchronises invoices from KSeF into the local DB.

    Workflow per company:
      1. Authenticate with KSeF via the ksef2 SDK.
      2. Export invoices for both *seller* and *buyer* roles.
      3. Download the encrypted ZIP, decrypt, and iterate XML files.
      4. Parse each XML with :class:`FA3Parser`.
      5. Upsert parsed data into the ``invoices`` table.
      6. Advance the high-water-mark (``last_sync_hwm_date``).
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._environment = _resolve_environment(settings.KSEF_BASE_URL)
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Date watermark
    # ------------------------------------------------------------------

    def _get_date_from(self, company_row: Row) -> datetime:
        """Return the start date for the next sync window.

        Uses ``last_sync_hwm_date`` if available, otherwise falls back
        to :pyattr:`Settings.KSEF_SYNC_DATE_FROM`.
        """
        last_hwm = company_row[2]  # last_sync_hwm_date
        if last_hwm is not None:
            # Ensure timezone-aware
            if last_hwm.tzinfo is None:
                return last_hwm.replace(tzinfo=timezone.utc)
            return last_hwm

        # First-time sync: January 1st of the current year in UTC
        current_year = datetime.now(timezone.utc).year
        return datetime(current_year, 1, 1, tzinfo=timezone.utc)

    # ------------------------------------------------------------------
    # Date range splitting
    # ------------------------------------------------------------------

    @staticmethod
    def _split_date_range(
        date_from: datetime,
        date_to: datetime,
        max_days: int = 90,
    ) -> list[tuple[datetime, datetime]]:
        """Split a date range into chunks of *max_days* each.

        KSeF API allows a maximum of ~3 months (90 days) per export
        request, so longer windows must be broken into sequential chunks.

        Args:
            date_from: Start date (inclusive).
            date_to: End date (inclusive).
            max_days: Maximum days per chunk (default 90).

        Returns:
            List of ``(chunk_start, chunk_end)`` tuples. Chunks are
            contiguous: ``chunk[i].end == chunk[i+1].start``.
        """
        chunks: list[tuple[datetime, datetime]] = []
        current = date_from
        delta = timedelta(days=max_days)

        while current < date_to:
            chunk_end = min(current + delta, date_to)
            chunks.append((current, chunk_end))
            current = chunk_end

        return chunks

    # ------------------------------------------------------------------
    # Role-level sync (seller / buyer)
    # ------------------------------------------------------------------

    async def _sync_role(
        self,
        auth: Any,
        role: Literal["seller", "buyer"],
        date_from: datetime,
        date_to: datetime,
        company_id: int,
        company_nip: str,
        db: AsyncSession,
    ) -> tuple[list[dict], datetime | None]:
        """Export, download, parse and upsert invoices for a single role.

        Args:
            auth: Authenticated SDK object (``client.authentication.with_token(...)``).
            role: ``"seller"`` or ``"buyer"``.
            date_from: Start of the invoice date window (inclusive).
            date_to: End of the invoice date window (inclusive).
            company_id: Local company PK.
            company_nip: Company NIP (for logging).
            db: Active async DB session.

        Returns:
            Tuple of:
              - List of parsed invoice dicts produced by :meth:`FA3Parser.parse`.
              - Maximum ``permanentStorageHwmDate`` encountered (or None if no files).
        """
        self.logger.info(
            "Starting %s sync for company_id=%d (NIP=%s) [%s → %s]",
            role,
            company_id,
            company_nip,
            date_from.isoformat(),
            date_to.isoformat(),
        )

        # Split the date range into ≤90-day chunks (KSeF API limitation)
        chunks = self._split_date_range(date_from, date_to)
        self.logger.info("Date range split into %d chunk(s) for role=%s", len(chunks), role)

        parsed_results: list[dict] = []
        max_hwm: datetime | None = None

        for chunk_idx, (chunk_from, chunk_to) in enumerate(chunks, 1):
            # Pagination loop for when a chunk exceeds 10,000 files
            current_date_from = chunk_from
            page_idx = 1

            while True:
                self.logger.info(
                    "Processing chunk %d/%d page %d [%s → %s] (role=%s)",
                    chunk_idx,
                    len(chunks),
                    page_idx,
                    current_date_from.isoformat(),
                    chunk_to.isoformat(),
                    role,
                )

                # 1. Schedule export for this chunk page
                export = await asyncio.to_thread(
                    auth.invoices.schedule_export,
                    filters=InvoicesFilter(
                        role=role,
                        date_type="permanent_storage",
                        date_from=current_date_from,
                        date_to=chunk_to,
                        amount_type="brutto",
                        restrict_to_permanent_storage_hwm_date=True,
                    ),
                )
                self.logger.info(
                    "Export scheduled (role=%s, chunk=%d, page=%d, ref=%s)",
                    role,
                    chunk_idx,
                    page_idx,
                    export.reference_number,
                )

                # 2. Wait for the export package to be ready
                package = await asyncio.to_thread(
                    auth.invoices.wait_for_export_package,
                    reference_number=export.reference_number,
                    timeout=self._settings.KSEF_EXPORT_TIMEOUT,
                    poll_interval=self._settings.KSEF_EXPORT_POLL_INTERVAL,
                )
                self.logger.info(
                    "Export package ready (role=%s, chunk=%d, page=%d)", role, chunk_idx, page_idx
                )

                # 3. Download and decrypt the ZIP
                download_dir = Path(self._settings.KSEF_DOWNLOAD_DIR) / str(company_id) / role
                download_dir.mkdir(parents=True, exist_ok=True)

                paths: list[Path] = await asyncio.to_thread(
                    lambda: list(
                        auth.invoices.fetch_package(
                            package=package,
                            export=export,
                            target_directory=download_dir,
                        )
                    ),
                )
                self.logger.info(
                    "Downloaded %d file(s) for role=%s chunk=%d page=%d",
                    len(paths),
                    role,
                    chunk_idx,
                    page_idx,
                )

                is_truncated = False
                last_storage_date: datetime | None = None

                # 4. Parse files and map metadata
                # Collect paths first; a try/finally guarantees cleanup even if
                # an unexpected exception fires mid-loop (e.g. DB crash).
                try:
                    for path in paths:
                        # Parse metadata JSON
                        if "metadata" in path.name.lower() and path.suffix == ".json":
                            try:
                                meta = json.loads(path.read_text(encoding="utf-8"))

                                # Extract permanentStorageHwmDate
                                hwm_str = meta.get("permanentStorageHwmDate")
                                if hwm_str:
                                    hwm_dt = datetime.fromisoformat(hwm_str).replace(
                                        tzinfo=timezone.utc
                                    )
                                    if max_hwm is None or hwm_dt > max_hwm:
                                        max_hwm = hwm_dt

                                # Extract pagination indicators
                                is_truncated = meta.get("isTruncated", False)
                                last_date_str = meta.get("lastPermanentStorageDate")
                                if last_date_str:
                                    last_storage_date = datetime.fromisoformat(
                                        last_date_str
                                    ).replace(tzinfo=timezone.utc)

                            except Exception:
                                self.logger.exception(
                                    "Failed to parse metadata file %s", path.name
                                )
                            continue

                        # Parse XML file
                        xml_content = path.read_text(encoding="utf-8")

                        try:
                            parsed = FA3Parser.parse(xml_content)
                        except FA3ParseError:
                            self.logger.exception(
                                "Failed to parse XML file %s — skipping", path.name
                            )
                            ksef_ref = path.stem
                            await self._upsert_error_invoice(
                                company_id=company_id,
                                ksef_reference_number=ksef_ref,
                                xml_content=xml_content,
                                db=db,
                            )
                            continue

                        if not parsed.get("ksef_reference_number"):
                            parsed["ksef_reference_number"] = path.stem

                        await self._upsert_invoice(
                            company_id=company_id,
                            parsed=parsed,
                            xml_content=xml_content,
                            db=db,
                        )
                        parsed_results.append(parsed)

                finally:
                    for path in paths:
                        try:
                            path.unlink(missing_ok=True)
                        except OSError:
                            self.logger.warning("Could not delete temp file %s", path)

                # 5. Handle pagination
                if is_truncated and last_storage_date:
                    self.logger.info(
                        "Package truncated. Shifting next page date_from to %s",
                        last_storage_date.isoformat(),
                    )
                    current_date_from = last_storage_date
                    page_idx += 1
                else:
                    break  # Done with this 90-day chunk

        return parsed_results, max_hwm

    # ------------------------------------------------------------------
    # DB upsert helpers
    # ------------------------------------------------------------------

    async def _upsert_invoice(
        self,
        company_id: int,
        parsed: dict,
        xml_content: str,
        db: AsyncSession,
    ) -> None:
        """Insert or update a parsed invoice row."""
        stmt = text("""
            INSERT INTO invoices (
                company_id,
                ksef_reference_number,
                invoice_number,
                issue_date,
                seller_nip,
                buyer_nip,
                total_gross,
                xml_raw,
                status,
                parsed_payload
            ) VALUES (
                :company_id,
                :ksef_reference_number,
                :invoice_number,
                :issue_date,
                :seller_nip,
                :buyer_nip,
                :total_gross,
                :xml_raw,
                'PARSED',
                :parsed_payload
            )
            ON CONFLICT (ksef_reference_number) DO UPDATE SET
                invoice_number  = EXCLUDED.invoice_number,
                issue_date      = EXCLUDED.issue_date,
                seller_nip      = EXCLUDED.seller_nip,
                buyer_nip       = EXCLUDED.buyer_nip,
                total_gross     = EXCLUDED.total_gross,
                xml_raw         = EXCLUDED.xml_raw,
                status          = EXCLUDED.status,
                parsed_payload  = EXCLUDED.parsed_payload
        """)

        await db.execute(
            stmt,
            {
                "company_id": company_id,
                "ksef_reference_number": parsed["ksef_reference_number"],
                "invoice_number": parsed.get("invoice_number"),
                "issue_date": parsed.get("issue_date"),
                "seller_nip": parsed.get("seller_nip"),
                "buyer_nip": parsed.get("buyer_nip"),
                "total_gross": parsed.get("total_gross"),
                "xml_raw": xml_content,
                "parsed_payload": json.dumps(parsed, ensure_ascii=False),
            },
        )

    async def _upsert_error_invoice(
        self,
        company_id: int,
        ksef_reference_number: str,
        xml_content: str,
        db: AsyncSession,
    ) -> None:
        """Insert or update an invoice row with ERROR status."""
        stmt = text("""
            INSERT INTO invoices (
                company_id,
                ksef_reference_number,
                xml_raw,
                status
            ) VALUES (
                :company_id,
                :ksef_reference_number,
                :xml_raw,
                'ERROR'
            )
            ON CONFLICT (ksef_reference_number) DO UPDATE SET
                xml_raw = EXCLUDED.xml_raw,
                status  = EXCLUDED.status
        """)

        await db.execute(
            stmt,
            {
                "company_id": company_id,
                "ksef_reference_number": ksef_reference_number,
                "xml_raw": xml_content,
            },
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def sync_company(
        self,
        company_id: int,
        db: AsyncSession,
    ) -> dict:
        """Synchronise all invoices for a single company from KSeF.

        This is the **main entry point**. It:
          1. Loads the company record and decrypts the ``ksef_token``.
          2. Authenticates with the ksef2 SDK.
          3. Runs export + parse for both *seller* and *buyer* roles.
          4. Advances the high-water-mark date.
          5. Commits the transaction.

        Args:
            company_id: PK of the company in the ``companies`` table.
            db: Active :class:`AsyncSession`.

        Returns:
            Summary dict with counts and date range.

        Raises:
            InvoiceSyncError: On any unrecoverable failure.
        """
        self.logger.info("Starting sync for company_id=%d", company_id)

        # 1. Load company
        stmt = select(
            Company.nip,
            Company.ksef_token,
            Company.last_sync_hwm_date,
        ).where(Company.id == company_id)

        result = await db.execute(stmt)
        company_row = result.fetchone()

        if company_row is None:
            raise InvoiceSyncPermanentError(f"Company with id={company_id} not found")

        nip: str = company_row[0]
        encrypted_token: str = company_row[1]

        # 2. Decrypt ksef_token
        self.logger.info("Decrypting ksef_token for company_id=%d", company_id)
        try:
            decrypted_token = CryptoUtil.decrypt(
                encrypted_token, self._settings.ENCRYPTION_MASTER_KEY
            )
        except Exception as exc:
            # Wrong key or corrupt ciphertext — permanent, no point retrying
            raise InvoiceSyncPermanentError(
                f"Failed to decrypt ksef_token for company_id={company_id}"
            ) from exc

        # 3. Authenticate with SDK
        self.logger.info(
            "Authenticating with KSeF SDK (NIP=%s, env=%s)",
            nip,
            self._environment.name,
        )
        try:
            client = Client(environment=self._environment)
            auth = await asyncio.to_thread(
                client.authentication.with_token,
                ksef_token=decrypted_token,
                nip=nip,
            )
        except Exception as exc:
            # Do NOT interpolate exc — the SDK may embed the decrypted token in its repr
            raise InvoiceSyncError(
                f"KSeF authentication failed for company_id={company_id}"
            ) from exc
        finally:
            del decrypted_token

        # 4. Determine date window
        date_from = self._get_date_from(company_row)
        date_to = datetime.now(timezone.utc)

        self.logger.info("Sync window: %s → %s", date_from.isoformat(), date_to.isoformat())

        # 5. Sync seller invoices
        try:
            seller_results, seller_hwm = await self._sync_role(
                auth=auth,
                role="seller",
                date_from=date_from,
                date_to=date_to,
                company_id=company_id,
                company_nip=nip,
                db=db,
            )
        except Exception as exc:
            raise InvoiceSyncError(
                f"Seller export failed for company_id={company_id}: {exc}"
            ) from exc

        # 6. Determine exact HWM to persist
        final_hwm = seller_hwm if seller_hwm is not None else date_to

        # 7. Update high-water-mark
        hwm_stmt = text("""
            UPDATE companies
            SET last_sync_hwm_date = :hwm
            WHERE id = :company_id
        """)
        await db.execute(
            hwm_stmt,
            {"hwm": final_hwm, "company_id": company_id},
        )

        # 8. Commit
        await db.commit()

        summary = {
            "company_id": company_id,
            "seller_invoices": len(seller_results),
            "buyer_invoices": 0,  # Deprecated per MVP scope
            "sync_date_from": date_from.isoformat(),
            "sync_date_to": date_to.isoformat(),
        }

        self.logger.info("Sync completed for company_id=%d: %s", company_id, summary)
        return summary
