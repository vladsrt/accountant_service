"""Unit tests for date-related logic in InvoiceSyncService."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core.config import Settings
from app.services.invoice_sync import InvoiceSyncService

# ---------------------------------------------------------------------------
# TestSplitDateRange
# ---------------------------------------------------------------------------


class TestSplitDateRange:
    """Tests for InvoiceSyncService._split_date_range()."""

    def test_range_within_90_days(self) -> None:
        """A 59-day range should produce exactly 1 chunk."""
        date_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
        date_to = datetime(2026, 3, 1, tzinfo=timezone.utc)
        chunks = InvoiceSyncService._split_date_range(date_from, date_to)
        assert len(chunks) == 1

    def test_range_within_90_days_boundaries(self) -> None:
        """Single chunk should span the entire requested range."""
        date_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
        date_to = datetime(2026, 3, 1, tzinfo=timezone.utc)
        chunks = InvoiceSyncService._split_date_range(date_from, date_to)
        assert chunks[0] == (date_from, date_to)

    def test_range_exactly_90_days(self) -> None:
        """A 90-day range should produce exactly 1 chunk."""
        date_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
        date_to = datetime(2026, 4, 1, tzinfo=timezone.utc)  # 90 days
        chunks = InvoiceSyncService._split_date_range(date_from, date_to)
        assert len(chunks) == 1

    def test_range_91_days(self) -> None:
        """A 91-day range should produce exactly 2 chunks."""
        date_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
        date_to = datetime(2026, 4, 2, tzinfo=timezone.utc)  # 91 days
        chunks = InvoiceSyncService._split_date_range(date_from, date_to)
        assert len(chunks) == 2

    def test_range_6_months(self) -> None:
        """A ~6-month range (181 days) should produce 3 chunks."""
        date_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
        date_to = datetime(2026, 7, 1, tzinfo=timezone.utc)
        chunks = InvoiceSyncService._split_date_range(date_from, date_to)
        assert len(chunks) == 3

    def test_range_6_months_last_chunk_end(self) -> None:
        """The last chunk must end at date_to."""
        date_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
        date_to = datetime(2026, 7, 1, tzinfo=timezone.utc)
        chunks = InvoiceSyncService._split_date_range(date_from, date_to)
        assert chunks[-1][1] == date_to

    def test_range_full_year(self) -> None:
        """A full year should produce 4 or 5 chunks of max 90 days each."""
        date_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
        date_to = datetime(2026, 12, 31, tzinfo=timezone.utc)
        chunks = InvoiceSyncService._split_date_range(date_from, date_to)
        assert len(chunks) in (4, 5)

    def test_range_full_year_last_chunk(self) -> None:
        """Full year: the last chunk must end at 2026-12-31."""
        date_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
        date_to = datetime(2026, 12, 31, tzinfo=timezone.utc)
        chunks = InvoiceSyncService._split_date_range(date_from, date_to)
        assert chunks[-1][1] == date_to

    def test_range_full_year_max_chunk_size(self) -> None:
        """Full year: every chunk must span at most 90 days."""
        date_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
        date_to = datetime(2026, 12, 31, tzinfo=timezone.utc)
        chunks = InvoiceSyncService._split_date_range(date_from, date_to)
        for start, end in chunks:
            assert (end - start).days <= 90

    def test_chunks_are_contiguous(self) -> None:
        """Adjacent chunks must share a boundary (no gaps)."""
        date_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
        date_to = datetime(2026, 12, 31, tzinfo=timezone.utc)
        chunks = InvoiceSyncService._split_date_range(date_from, date_to)
        for i in range(len(chunks) - 1):
            assert chunks[i][1] == chunks[i + 1][0]

    def test_no_overlap_between_chunks(self) -> None:
        """No chunk end should exceed the next chunk's start."""
        date_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
        date_to = datetime(2026, 12, 31, tzinfo=timezone.utc)
        chunks = InvoiceSyncService._split_date_range(date_from, date_to)
        for i in range(len(chunks) - 1):
            assert chunks[i][1] <= chunks[i + 1][0]


# ---------------------------------------------------------------------------
# TestGetDateFrom
# ---------------------------------------------------------------------------


class TestGetDateFrom:
    """Tests for InvoiceSyncService._get_date_from()."""

    @pytest.fixture()
    def service(self, mock_settings: Settings) -> InvoiceSyncService:
        """Create a service instance with mock settings."""
        return InvoiceSyncService(mock_settings)

    def test_first_run_no_hwm(self, service: InvoiceSyncService) -> None:
        """When HWM is None, should return Jan 1st of the current UTC year."""
        # company_row: (nip, ksef_token, last_sync_hwm_date)
        company_row = ("1234567890", "encrypted_token", None)
        result = service._get_date_from(company_row)

        current_year = datetime.now(timezone.utc).year
        expected_date = datetime(current_year, 1, 1, tzinfo=timezone.utc)
        assert result == expected_date

    def test_subsequent_run_with_hwm(self, service: InvoiceSyncService) -> None:
        """When HWM is set, should return the HWM datetime."""
        hwm = datetime(2026, 3, 15, tzinfo=timezone.utc)
        company_row = ("1234567890", "encrypted_token", hwm)
        result = service._get_date_from(company_row)
        assert result == datetime(2026, 3, 15, tzinfo=timezone.utc)

    def test_hwm_without_timezone(self, service: InvoiceSyncService) -> None:
        """A naive HWM datetime must be made timezone-aware (UTC)."""
        naive_hwm = datetime(2026, 3, 15)  # no tzinfo
        company_row = ("1234567890", "encrypted_token", naive_hwm)
        result = service._get_date_from(company_row)
        assert result.tzinfo is not None
        assert result == datetime(2026, 3, 15, tzinfo=timezone.utc)

    def test_date_from_is_always_timezone_aware_no_hwm(self, service: InvoiceSyncService) -> None:
        """Result must always have tzinfo set (no HWM case)."""
        company_row = ("1234567890", "encrypted_token", None)
        result = service._get_date_from(company_row)
        assert result.tzinfo is not None

    def test_date_from_is_always_timezone_aware_with_hwm(self, service: InvoiceSyncService) -> None:
        """Result must always have tzinfo set (with HWM case)."""
        hwm = datetime(2026, 6, 1, tzinfo=timezone.utc)
        company_row = ("1234567890", "encrypted_token", hwm)
        result = service._get_date_from(company_row)
        assert result.tzinfo is not None
