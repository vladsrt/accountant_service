"""Service for preparing invoice payload data for downstream LLM/RAG.

Includes PII masking to prevent sensitive personal data (PESEL, NIP, email,
phone numbers) from being sent to external AI services.
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.invoice import Invoice, InvoiceStatus

# ---------------------------------------------------------------------------
# PII Masking
# ---------------------------------------------------------------------------

# PESEL: exactly 11 digits (standalone or in context)
_RE_PESEL = re.compile(r"\b\d{11}\b")

# NIP: 10 digits optionally formatted as NNN-NNN-NN-NN or NNN-NN-NN-NNN
_RE_NIP = re.compile(r"\b\d{3}-\d{3}-\d{2}-\d{2}\b|\b\d{3}-\d{2}-\d{2}-\d{3}\b|\b\d{10}\b")

# Email
_RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Polish phone: optional +48 or 48 prefix, then 9 digits (with optional spaces/dashes)
_RE_PHONE = re.compile(r"(?:\+48|48)?[\s-]?\d{3}[\s-]?\d{3}[\s-]?\d{3}\b")


def mask_pii(text: str) -> str:
    """Mask personally identifiable information in text before sending to LLM.

    Replaces:
    - PESEL (11 digits) → [REDACTED_PESEL]
    - NIP (10 digits / NNN-NNN-NN-NN) → [REDACTED_NIP]
    - Email → [REDACTED_EMAIL]
    - Polish phone numbers → [REDACTED_PHONE]
    """
    # Order matters: NIP (10 digits) must be checked before PESEL (11 digits)
    # because a PESEL could contain a 10-digit substring. We mask longer first.
    text = _RE_PESEL.sub("[REDACTED_PESEL]", text)
    text = _RE_NIP.sub("[REDACTED_NIP]", text)
    text = _RE_EMAIL.sub("[REDACTED_EMAIL]", text)
    text = _RE_PHONE.sub("[REDACTED_PHONE]", text)
    return text


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class LLMPayloadService:
    @staticmethod
    async def get_unclassified_payload(company_id: int, db: AsyncSession) -> list[dict[str, Any]]:
        """Fetch all unclassified incoming/outgoing invoices and return minimal JSON representation.

        Filters for invoices where `is_classified` == False and status is PARSED.
        Converts the results into a flat list of dicts suitable for LLM context processing.
        All P_7 descriptions are PII-masked before being returned.
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

            # Mask PII in P_7 descriptions before they reach the LLM
            raw_descriptions = parsed.get("p7_descriptions", [])
            masked_descriptions = [mask_pii(desc) for desc in raw_descriptions]

            payloads.append(
                {
                    "invoice_id": invoice.id,
                    "invoice_number": invoice.invoice_number or parsed.get("invoice_number"),
                    "total_gross": gross_value,
                    "p7_descriptions": masked_descriptions,
                }
            )

        return payloads
