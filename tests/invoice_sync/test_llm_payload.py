"""Unit tests for the LLMPayloadService."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models.invoice import Invoice, InvoiceStatus
from app.services.llm_payload_service import LLMPayloadService


@pytest.mark.asyncio
async def test_get_unclassified_payload_success() -> None:
    """Test standard unclassified invoice retrieval and payload flattening."""

    mock_db = AsyncMock()

    # Setup mock invoices
    inv1 = Invoice(
        id=101,
        company_id=1,
        invoice_number="FV/2026/01",
        total_gross=Decimal("1500.50"),
        is_classified=False,
        status=InvoiceStatus.PARSED,
        parsed_payload={
            "invoice_number": "FV/2026/01",
            "total_gross": "1500.50",
            "p7_descriptions": ["Konsultacje IT", "Licencja"],
        },
    )

    inv2 = Invoice(
        id=102,
        company_id=1,
        invoice_number=None,  # Should fallback to parsed_payload
        total_gross=None,  # Should fallback to parsed_payload
        is_classified=False,
        status=InvoiceStatus.PARSED,
        parsed_payload={
            "invoice_number": "FV/2026/02",
            "total_gross": "300.00",
            "p7_descriptions": ["Hosting"],
        },
    )

    # Mock SQLAlchemy result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [inv1, inv2]
    mock_db.execute.return_value = mock_result

    payloads = await LLMPayloadService.get_unclassified_payload(company_id=1, db=mock_db)

    assert len(payloads) == 2

    assert payloads[0]["invoice_id"] == 101
    assert payloads[0]["invoice_number"] == "FV/2026/01"
    assert payloads[0]["total_gross"] == "1500.50"
    assert payloads[0]["p7_descriptions"] == ["Konsultacje IT", "Licencja"]

    assert payloads[1]["invoice_id"] == 102
    assert payloads[1]["invoice_number"] == "FV/2026/02"
    assert payloads[1]["total_gross"] == "300.00"
    assert payloads[1]["p7_descriptions"] == ["Hosting"]


@pytest.mark.asyncio
async def test_get_unclassified_payload_empty() -> None:
    """Test behavior when no unclassified invoices are found."""
    mock_db = AsyncMock()

    # Mock empty result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    payloads = await LLMPayloadService.get_unclassified_payload(company_id=1, db=mock_db)
    assert len(payloads) == 0
