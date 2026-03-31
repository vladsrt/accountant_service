"""Unit tests for InvoiceSyncService ingestion refactoring.

Testing _metadata.json extraction (HWM and isTruncated pagination).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.services.invoice_sync import InvoiceSyncService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_db() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def mock_auth() -> MagicMock:
    auth = MagicMock()
    # Mock schedule_export
    mock_export = MagicMock()
    mock_export.reference_number = "TEST-REF-123"
    auth.invoices.schedule_export.return_value = mock_export
    # Mock wait_for_export_package
    mock_package = MagicMock()
    auth.invoices.wait_for_export_package.return_value = mock_package
    return auth


@pytest.fixture()
def sync_service(mock_settings: Settings) -> InvoiceSyncService:
    return InvoiceSyncService(mock_settings)


@pytest.fixture()
def mock_company_row() -> tuple:
    return ("1234567890", "encrypted_token", datetime(2026, 1, 1, tzinfo=timezone.utc))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_role_metadata_hwm_extraction(
    sync_service: InvoiceSyncService,
    mock_auth: MagicMock,
    mock_db: AsyncMock,
    tmp_path: Path,
) -> None:
    """_sync_role should read _metadata.json and return the highest HWM."""

    # 1. Setup mock files simulating a downloaded KSeF package
    # A valid _metadata.json
    meta_path = tmp_path / "package_metadata.json"
    hwm_date_str = "2026-03-15T10:00:00Z"
    meta_path.write_text(
        json.dumps({"permanentStorageHwmDate": hwm_date_str, "isTruncated": False})
    )

    # A dummy XML file
    xml_path = tmp_path / "1234.xml"
    xml_path.write_text("<Faktura><Fa><P_1>2026-03-01</P_1></Fa></Faktura>")

    # 2. Mock fetch_package to return these files
    mock_auth.invoices.fetch_package.return_value = iter([meta_path, xml_path])

    # 3. Call _sync_role
    date_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
    date_to = datetime(2026, 3, 31, tzinfo=timezone.utc)

    # We mock FA3Parser and DB calls to isolate metadata logic
    with patch(
        "app.services.fa3_parser.FA3Parser.parse", return_value={"ksef_reference_number": "1234"}
    ):
        results, max_hwm = await sync_service._sync_role(
            auth=mock_auth,
            role="seller",
            date_from=date_from,
            date_to=date_to,
            company_id=1,
            company_nip="1234567890",
            db=mock_db,
        )

    # 4. Assertions
    assert len(results) == 1
    assert max_hwm is not None
    assert max_hwm == datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc)

    # Verify the correct date_type was used
    mock_auth.invoices.schedule_export.assert_called_once()
    call_kwargs = mock_auth.invoices.schedule_export.call_args.kwargs
    filters = call_kwargs["filters"]
    assert (
        filters.date_type.value == "permanent_storage"
        if hasattr(filters.date_type, "value")
        else filters.date_type == "permanent_storage"
    )
    assert filters.restrict_to_permanent_storage_hwm_date is True


@pytest.mark.asyncio
async def test_sync_role_truncation_loop(
    sync_service: InvoiceSyncService,
    mock_auth: MagicMock,
    mock_db: AsyncMock,
    tmp_path: Path,
) -> None:
    """_sync_role should loop if _metadata.json indicates isTruncated=True."""

    # We will simulate 2 pages.
    # Page 1: isTruncated=True, returns HWM 1 and last date
    meta_page1 = tmp_path / "meta1_metadata.json"
    meta_page1.write_text(
        json.dumps(
            {
                "isTruncated": True,
                "lastPermanentStorageDate": "2026-02-15T12:00:00Z",
                "permanentStorageHwmDate": "2026-02-15T12:00:00Z",
            }
        )
    )

    # Page 2: isTruncated=False, returns HWM 2
    meta_page2 = tmp_path / "meta2_metadata.json"
    meta_page2.write_text(
        json.dumps(
            {
                "isTruncated": False,
                "permanentStorageHwmDate": "2026-03-31T23:59:59Z",
            }
        )
    )

    # We need fetch_package to return page 1 on first call, page 2 on second call
    fetch_calls = 0

    def mock_fetch_package(*args, **kwargs):
        nonlocal fetch_calls
        fetch_calls += 1
        if fetch_calls == 1:
            return iter([meta_page1])
        return iter([meta_page2])

    mock_auth.invoices.fetch_package.side_effect = mock_fetch_package

    date_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
    date_to = datetime(2026, 3, 31, tzinfo=timezone.utc)  # Exactly 90 days, 1 chunk

    results, max_hwm = await sync_service._sync_role(
        auth=mock_auth,
        role="seller",
        date_from=date_from,
        date_to=date_to,
        company_id=1,
        company_nip="1234567890",
        db=mock_db,
    )

    # 1. We expected schedule_export to be called TWICE for the SAME chunk due to truncation
    assert mock_auth.invoices.schedule_export.call_count == 2

    # 2. Check the date_from for the second call
    calls = mock_auth.invoices.schedule_export.call_args_list
    first_filters = calls[0].kwargs["filters"]
    second_filters = calls[1].kwargs["filters"]

    assert first_filters.date_from == date_from
    assert second_filters.date_from == datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)

    # Both should have the same date_to
    assert first_filters.date_to == date_to
    assert second_filters.date_to == date_to

    # 3. Assert the max HWM is from Page 2
    assert max_hwm == datetime(2026, 3, 31, 23, 59, 59, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_sync_company_hwm_update(
    sync_service: InvoiceSyncService,
    mock_db: AsyncMock,
) -> None:
    """sync_company should update DB with max HWM from the chunks, not datetime.now()."""

    # 1. Mock DB select for company
    mock_select_result = MagicMock()
    mock_select_result.fetchone.return_value = ("1234567890", "encrypted_token", None)
    mock_db.execute.return_value = mock_select_result

    # 2. Mock cryptography
    with patch("app.services.ksef_auth.CryptoUtil.decrypt", return_value="plain_token"):
        # 3. Mock KSeF auth client
        with patch("app.services.invoice_sync.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_auth = MagicMock()
            mock_client.authentication.with_token.return_value = mock_auth

            # 4. Mock _sync_role to return specific HWM for seller
            seller_hwm = datetime(2026, 5, 10, tzinfo=timezone.utc)

            with patch.object(
                sync_service,
                "_sync_role",
                return_value=([], seller_hwm),
            ):
                summary = await sync_service.sync_company(1, mock_db)
                assert summary["company_id"] == 1

                # Check DB update was called with seller_hwm
                # The execute call for update is the last one before commit
                execute_calls = mock_db.execute.call_args_list
                update_call = execute_calls[-1]  # The last execute call

                query_params = update_call.args[1]
                assert query_params["hwm"] == seller_hwm
                assert query_params["company_id"] == 1
