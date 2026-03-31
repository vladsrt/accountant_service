"""
Bank Statement CSV parsing and ingestion service.

Wraps the bank2ynab library to detect Polish bank CSV formats
(mBank, PKO BP, Bank Pekao, Alior Bank, and others) and convert them
into a standardised list of YNAB-format dicts.

Extends parsing with YTD validation, outflow filtering, SHA-256
deduplication, and idempotent PostgreSQL upserts.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import shutil
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
from bank2ynab.config_handler import ConfigHandler
from bank2ynab.dataframe_handler import DataframeHandler
from bank2ynab.transactionfile_reader import detect_encoding, get_files
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.bank_transaction import BankTransaction

logger = logging.getLogger(__name__)

STANDARD_COLUMNS = ["Date", "Payee", "Memo", "Outflow", "Inflow"]


class BankStatementParseError(Exception):
    """Raised when no bank2ynab configuration matches the uploaded filename."""


class BankStatementValidationError(Exception):
    """Raised when the uploaded statement fails YTD coverage validation."""


class BankStatementService:
    """
    Parses raw CSV bank statement exports into standardised YNAB-format dicts,
    then filters, validates, deduplicates, and upserts them into PostgreSQL.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def process_statement(
        self,
        company_id: int,
        company_registration_date: date | None,
        file_content: bytes,
        filename: str,
        db: AsyncSession,
    ) -> dict[str, int]:
        """Full ingestion pipeline: parse → validate → filter → hash → upsert.

        Args:
            company_id: FK of the owning company.
            company_registration_date: Optional company registration date.
                Used to relax the YTD validation start boundary.
            file_content: Raw bytes of the uploaded CSV file.
            filename: Original filename for bank2ynab format detection.
            db: Active async database session.

        Returns:
            Summary dict with ``total_parsed``, ``new_inserted``, and
            ``duplicates_ignored`` counts.

        Raises:
            BankStatementParseError: If the CSV cannot be parsed.
            BankStatementValidationError: If the statement does not cover
                the required YTD date range.
        """
        # 1. Parse
        rows = await self.parse_csv(file_content, filename)
        total_parsed = len(rows)

        if total_parsed == 0:
            return {"total_parsed": 0, "new_inserted": 0, "duplicates_ignored": 0}

        # 2. Hard validation (Story 3) — YTD coverage check
        self._validate_ytd_coverage(rows, company_registration_date)

        # 3. Filtering (Story 2) — keep only positive inflows
        filtered = self._filter_inflows(rows)

        if not filtered:
            return {"total_parsed": total_parsed, "new_inserted": 0, "duplicates_ignored": 0}

        # 4. Hashing & Deduplication (Story 4)
        records = self._prepare_records(filtered, company_id)

        # 5. Database upsert
        new_inserted = await self._bulk_upsert(records, db)

        duplicates_ignored = len(records) - new_inserted

        return {
            "total_parsed": total_parsed,
            "new_inserted": new_inserted,
            "duplicates_ignored": duplicates_ignored,
        }

    async def parse_csv(self, file_content: bytes, filename: str) -> list[dict]:
        """Parse a raw CSV bank statement and return standardised rows.

        The bank format is auto-detected from the filename using bank2ynab's
        built-in configuration (no manual bank selection required).

        Args:
            file_content: Raw bytes of the uploaded CSV file.
            filename: Original filename — used by bank2ynab for format detection
                      via its filename-pattern rules (e.g. regex against
                      ``eKonto_*`` for mBank, ``history_csv_*`` for PKO BP).

        Returns:
            List of dicts, each with keys: ``Date``, ``Payee``, ``Memo``,
            ``Outflow``, ``Inflow``.  Dates are ISO-8601 strings (``YYYY-MM-DD``).
            Monetary values are floats.

        Raises:
            BankStatementParseError: If no configured bank format matches the
                filename, or if bank2ynab's configuration file cannot be found.
        """
        return await asyncio.to_thread(self._parse_sync, file_content, filename)

    # ------------------------------------------------------------------
    # Pipeline steps (private)
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_ytd_coverage(
        rows: list[dict],
        company_registration_date: date | None,
    ) -> None:
        """Validate that the statement covers the required YTD start date.

        Raises:
            BankStatementValidationError: If the earliest row date is
                strictly after the required start date.
        """
        # Determine required start date
        jan_1 = date(datetime.now(timezone.utc).year, 1, 1)
        required_start = jan_1

        if company_registration_date is not None and company_registration_date > jan_1:
            required_start = company_registration_date

        # Find MIN(Date) from rows
        dates: list[date] = []
        for row in rows:
            raw_date = row.get("Date")
            if raw_date:
                if isinstance(raw_date, str):
                    dates.append(date.fromisoformat(raw_date))
                elif isinstance(raw_date, date):
                    dates.append(raw_date)

        if not dates:
            return  # No dates to validate — pass through

        min_date = min(dates)

        if min_date > required_start:
            raise BankStatementValidationError(
                "Для 100% гарантии правильности налогов, "
                "пожалуйста, загрузите выписку строго с начала года "
                "(или с даты регистрации)."
            )

    @staticmethod
    def _filter_inflows(rows: list[dict]) -> list[dict]:
        """Keep only rows with positive Inflow and zero/no Outflow."""
        filtered: list[dict] = []
        for row in rows:
            outflow = float(row.get("Outflow") or 0)
            inflow = float(row.get("Inflow") or 0)

            if outflow > 0 or inflow <= 0:
                continue

            filtered.append(row)

        return filtered

    @staticmethod
    def _compute_hash(company_id: int, row: dict) -> str:
        """Compute a deterministic SHA-256 hash for a transaction row.

        Format: ``{company_id}|{date}|{amount}|{payee or ''}|{memo or ''}``
        """
        raw = (
            f"{company_id}"
            f"|{row.get('Date', '')}"
            f"|{row.get('Inflow', '')}"
            f"|{row.get('Payee') or ''}"
            f"|{row.get('Memo') or ''}"
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def _prepare_records(cls, rows: list[dict], company_id: int) -> list[dict[str, Any]]:
        """Transform filtered rows into DB-ready dicts with hashes."""
        records: list[dict[str, Any]] = []
        for row in rows:
            tx_hash = cls._compute_hash(company_id, row)
            records.append(
                {
                    "company_id": company_id,
                    "date": row["Date"],
                    "amount": Decimal(str(row["Inflow"])),
                    "payee": row.get("Payee"),
                    "memo": row.get("Memo"),
                    "transaction_hash": tx_hash,
                    "status": "UNMATCHED",
                }
            )
        return records

    @staticmethod
    async def _bulk_upsert(records: list[dict[str, Any]], db: AsyncSession) -> int:
        """Bulk insert with ON CONFLICT DO NOTHING for idempotency.

        Returns:
            Number of rows actually inserted (excludes duplicates).
        """
        stmt = pg_insert(BankTransaction).values(records)
        stmt = stmt.on_conflict_do_nothing(index_elements=["transaction_hash"])

        result = await db.execute(stmt)
        await db.commit()

        return result.rowcount  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # CSV parsing internals
    # ------------------------------------------------------------------

    def _parse_sync(self, file_content: bytes, filename: str) -> list[dict]:
        """Synchronous core invoked inside a thread by parse_csv."""
        safe_name = Path(filename).name
        tmp_dir = tempfile.mkdtemp(prefix="bank_stmt_")
        try:
            tmp_file = Path(tmp_dir) / safe_name
            tmp_file.write_bytes(file_content)
            return self._detect_and_parse(str(tmp_file), tmp_dir, safe_name)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _detect_and_parse(
        self,
        tmp_file_path: str,
        tmp_dir: str,
        filename: str,
    ) -> list[dict]:
        """Match the file to a bank configuration and run the parser.

        Iterates over every section in bank2ynab.conf. For each section the
        library's own get_files() is used to test whether the filename matches
        the configured pattern, keeping the detection logic identical to the
        CLI tool's behaviour.

        Args:
            tmp_file_path: Absolute path to the temp copy of the uploaded file.
            tmp_dir: Directory that contains tmp_file_path.
            filename: Safe (basename-only) version of the original filename.

        Returns:
            Standardised list of dicts (see parse_csv docstring).

        Raises:
            BankStatementParseError: If no section matches or config is missing.
        """
        try:
            config_handler = ConfigHandler()
        except FileNotFoundError as exc:
            raise BankStatementParseError("bank2ynab configuration file not found") from exc

        for section in config_handler.config.sections():
            config_dict = config_handler.fix_conf_params(section)

            matching = get_files(
                name=config_dict["bank_name"],
                file_pattern=config_dict["input_filename"],
                try_path=tmp_dir,
                regex_active=config_dict["regex"],
                ext=config_dict["ext"],
                prefix=config_dict["fixed_prefix"],
            )

            if not matching:
                continue

            logger.info("Matched bank format '%s' for file '%s'", section, filename)

            src_file = matching[0]
            encod = detect_encoding(src_file)

            df_handler = DataframeHandler()
            try:
                df_handler.run(
                    file_path=src_file,
                    delim=config_dict["input_delimiter"],
                    header_rows=int(config_dict["header_rows"]),
                    footer_rows=int(config_dict["footer_rows"]),
                    encod=encod,
                    input_columns=config_dict["input_columns"],
                    output_columns=config_dict["output_columns"],
                    api_columns=config_dict["api_columns"],
                    cd_flags=config_dict["cd_flags"],
                    date_format=config_dict["date_format"],
                    date_dedupe=config_dict["date_dedupe"],
                    fill_memo=config_dict["payee_to_memo"],
                    currency_fix=config_dict["currency_mult"],
                )
            except ValueError as exc:
                raise BankStatementParseError(
                    f"bank2ynab could not parse '{filename}' as '{section}': {exc}"
                ) from exc

            if df_handler.df.empty:
                logger.info("No transactions found in '%s' for bank '%s'", filename, section)
                return []

            available = [c for c in STANDARD_COLUMNS if c in df_handler.output_df.columns]
            return df_handler.output_df[available].replace({np.nan: None}).to_dict(orient="records")

        raise BankStatementParseError(
            f"No bank2ynab configuration matched filename: '{filename}'. "
            "Ensure the filename follows one of the supported bank export patterns "
            "(e.g. eKonto_* for mBank, history_csv_* for PKO BP)."
        )
