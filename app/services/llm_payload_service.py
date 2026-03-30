"""Service for preparing invoice payload data for downstream LLM/RAG."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.invoice import Invoice, InvoiceStatus


class LLMPayloadService:
    @staticmethod
    async def get_unclassified_payload(company_id: int, db: AsyncSession) -> list[dict[str, Any]]:
        """Fetch all unclassified incoming/outgoing invoices and return minimal JSON representation.

        Filters for invoices where `is_classified` == False and status is PARSED.
        Converts the results into a flat list of dicts suitable for LLM context processing.
        """
        stmt = select(Invoice).where(
            Invoice.company_id == company_id,
            Invoice.is_classified == False,  # noqa: E712
            Invoice.status == InvoiceStatus.PARSED,  # We only want successfully parsed invoices
        )

        result = await db.execute(stmt)
        invoices = result.scalars().all()

        payloads = []
        for invoice in invoices:
            parsed = invoice.parsed_payload or {}
            gross_value = (
                str(invoice.total_gross)
                if invoice.total_gross is not None
                else parsed.get("total_gross")
            )

            payloads.append(
                {
                    "invoice_id": invoice.id,
                    "invoice_number": invoice.invoice_number or parsed.get("invoice_number"),
                    "total_gross": gross_value,
                    "p7_descriptions": parsed.get("p7_descriptions", []),
                }
            )

        return payloads
