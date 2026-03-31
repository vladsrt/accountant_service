"""Unit tests for BankStatementService ingestion pipeline."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.services.bank_statement_service import (
    BankStatementService,
    BankStatementValidationError,
)

# ---------------------------------------------------------------------------
# Test Data
# ---------------------------------------------------------------------------


def get_current_year_jan_1() -> date:
    return date(datetime.now(timezone.utc).year, 1, 1)


# ---------------------------------------------------------------------------
# Tests: Story 3 - YTD Coverage Validation
# ---------------------------------------------------------------------------


def test_validate_ytd_coverage_raises_when_after_jan_1():
    jan_1 = get_current_year_jan_1()
    # The earliest row is Feb 1st, so it's strictly > Jan 1st.
    rows = [{"Date": jan_1 + timedelta(days=31)}]

    with pytest.raises(BankStatementValidationError, match="строго с начала года"):
        BankStatementService._validate_ytd_coverage(rows, company_registration_date=None)


def test_validate_ytd_coverage_passes_for_jan_1():
    jan_1 = get_current_year_jan_1()
    rows = [{"Date": jan_1}, {"Date": jan_1 + timedelta(days=5)}]

    # Should not raise
    BankStatementService._validate_ytd_coverage(rows, company_registration_date=None)


def test_validate_ytd_coverage_allows_later_if_registration_date_provided():
    jan_1 = get_current_year_jan_1()
    reg_date = jan_1 + timedelta(days=60)  # March 2nd

    # Earliest row is March 2nd. Normally invalid, but reg date covers it.
    rows = [{"Date": reg_date}]

    # Should not raise
    BankStatementService._validate_ytd_coverage(rows, company_registration_date=reg_date)


def test_validate_ytd_coverage_raises_if_after_registration_date():
    jan_1 = get_current_year_jan_1()
    reg_date = jan_1 + timedelta(days=60)  # March 2nd

    # Earliest row is March 5th (after reg date). Should raise!
    rows = [{"Date": reg_date + timedelta(days=3)}]

    with pytest.raises(BankStatementValidationError, match="строго с начала года"):
        BankStatementService._validate_ytd_coverage(rows, company_registration_date=reg_date)


def test_validate_ytd_coverage_empty_rows():
    # Defensive - should just pass through
    BankStatementService._validate_ytd_coverage([], company_registration_date=None)


# ---------------------------------------------------------------------------
# Tests: Story 2 - Filtering
# ---------------------------------------------------------------------------


def test_filter_inflows_discards_outflows():
    rows = [
        {"Inflow": 500, "Outflow": 0},  # Valid
        {"Inflow": 0, "Outflow": 100},  # Discard: pure outflow
        {"Inflow": 1000, "Outflow": 100},  # Discard: has outflow > 0
    ]

    filtered = BankStatementService._filter_inflows(rows)
    assert len(filtered) == 1
    assert filtered[0]["Inflow"] == 500


def test_filter_inflows_discards_zero_or_negative_inflows():
    rows = [
        {"Inflow": 1500, "Outflow": 0},  # Valid
        {"Inflow": 0, "Outflow": 0},  # Discard: zero inflow
        {"Inflow": -50, "Outflow": 0},  # Discard: negative inflow
        {"Inflow": None, "Outflow": None},  # Discard: handles None
    ]

    filtered = BankStatementService._filter_inflows(rows)
    assert len(filtered) == 1
    assert filtered[0]["Inflow"] == 1500


# ---------------------------------------------------------------------------
# Tests: Story 4 - Hashing Determinism
# ---------------------------------------------------------------------------


def test_compute_hash_determinism():
    row1 = {"Date": "2026-03-15", "Inflow": 150.50, "Payee": "ACME", "Memo": "Invoice"}
    row2 = {"Date": "2026-03-15", "Inflow": 150.50, "Payee": "ACME", "Memo": "Invoice"}

    hash1 = BankStatementService._compute_hash(company_id=1, row=row1)
    hash2 = BankStatementService._compute_hash(company_id=1, row=row2)

    assert hash1 == hash2
    assert isinstance(hash1, str)
    assert len(hash1) == 64  # SHA-256


def test_compute_hash_cross_company_isolation():
    row = {"Date": "2026-03-15", "Inflow": 150.50, "Payee": "ACME", "Memo": "Invoice"}

    hash1 = BankStatementService._compute_hash(company_id=1, row=row)
    hash2 = BankStatementService._compute_hash(company_id=2, row=row)

    assert hash1 != hash2


def test_compute_hash_handles_nones_safely():
    # If payee/memo are missing, it should format as empty strings
    row1 = {"Date": "2026-03-15", "Inflow": 150.50, "Payee": None, "Memo": None}
    row2 = {"Date": "2026-03-15", "Inflow": 150.50, "Payee": "", "Memo": ""}

    hash1 = BankStatementService._compute_hash(company_id=1, row=row1)
    hash2 = BankStatementService._compute_hash(company_id=1, row=row2)

    assert hash1 == hash2


# ---------------------------------------------------------------------------
# Tests: Orchestration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_statement_orchestration():
    service = BankStatementService()
    mock_db = AsyncMock()

    jan_1 = get_current_year_jan_1()

    raw_rows = [
        {"Date": jan_1.isoformat(), "Inflow": 500, "Outflow": 0, "Payee": "P1"},
        {"Date": jan_1.isoformat(), "Inflow": 0, "Outflow": 100, "Payee": "P2"},  # filtered
        {"Date": jan_1.isoformat(), "Inflow": 1500, "Outflow": 0, "Payee": "P3"},
    ]

    with patch.object(service, "parse_csv", return_value=raw_rows) as mock_parse_csv:
        with patch.object(service, "_bulk_upsert", return_value=1) as mock_bulk_upsert:
            summary = await service.process_statement(
                company_id=1,
                company_registration_date=None,
                file_content=b"dummy_data",
                filename="statement.csv",
                db=mock_db,
            )

            # 1. Assert CSV parsing called
            mock_parse_csv.assert_called_once_with(b"dummy_data", "statement.csv")

            # 2. Assert Upsert got exactly 2 records (1 was filtered out due to outflow)
            mock_bulk_upsert.assert_called_once()
            records_passed_to_upsert = mock_bulk_upsert.call_args[0][0]
            assert len(records_passed_to_upsert) == 2

            # 3. Check records structure
            rec1 = records_passed_to_upsert[0]
            assert rec1["company_id"] == 1
            assert rec1["amount"] == Decimal("500")
            assert "transaction_hash" in rec1
            assert rec1["status"] == "UNMATCHED"

            # 4. Check return summary
            assert summary["total_parsed"] == 3
            assert summary["new_inserted"] == 1
            assert summary["duplicates_ignored"] == 1  # 2 passed to upsert, 1 inserted, 1 ignored


@pytest.mark.asyncio
async def test_process_statement_empty_handling():
    service = BankStatementService()
    mock_db = AsyncMock()

    with patch.object(service, "parse_csv", return_value=[]) as mock_parse_csv:
        summary = await service.process_statement(
            company_id=1,
            company_registration_date=None,
            file_content=b"",
            filename="empty.csv",
            db=mock_db,
        )
        assert summary["total_parsed"] == 0
        assert summary["new_inserted"] == 0
        assert summary["duplicates_ignored"] == 0

        mock_parse_csv.assert_called_once_with(b"", "empty.csv")
