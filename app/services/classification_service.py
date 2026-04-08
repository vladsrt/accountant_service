"""Service for classifying invoice line items using the AI classifier pipeline."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.invoice import Invoice
from app.db.models.invoice_line_classification import InvoiceLineClassification
from app.services.llm_payload_service import LLMPayloadService

logger = logging.getLogger(__name__)


class ClassificationService:
    """Bridge between async SQLAlchemy app and sync AI classifier (src.pipeline)."""

    @staticmethod
    async def _classify_single_p7(p7_text: str, user_context: str | None = None) -> dict[str, Any]:
        """Run the async classifier pipeline, optionally with user context."""
        from src.pipeline import classify

        result = await classify(p7_text, use_cache=True, user_context=user_context)
        return {
            "verdict": result.verdict.value,
            "rate_percent": result.rate_percent,
            "pkwiu_code": result.pkwiu_code,
            "pkwiu_description": result.pkwiu_description,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "ambiguity_flags": result.ambiguity_flags,
            "clarification_question": result.clarification_question,
            "corridor": result.corridor,
            "llm_calls_count": result.llm_calls_count,
            "is_threshold_dependent": result.is_threshold_dependent,
        }

    @staticmethod
    async def classify_invoice(
        invoice_id: int,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Classify all P_7 line items of a single invoice.

        Returns a summary dict: {"lines_classified": int, "verdict": str}
        """
        stmt = select(Invoice).where(Invoice.id == invoice_id)
        result = await db.execute(stmt)
        invoice = result.scalar_one_or_none()
        if invoice is None:
            logger.warning("Invoice %d not found", invoice_id)
            return {"lines_classified": 0, "verdict": "NOT_FOUND"}

        parsed = invoice.parsed_payload or {}
        p7_descriptions: list[str] = parsed.get("p7_descriptions", [])

        if not p7_descriptions:
            # No line items to classify — mark as classified
            invoice.is_classified = True
            await db.flush()
            return {"lines_classified": 0, "verdict": "NO_LINES"}

        # Check which lines are already classified (idempotency)
        existing_stmt = select(InvoiceLineClassification.line_index).where(
            InvoiceLineClassification.invoice_id == invoice_id
        )
        existing_result = await db.execute(existing_stmt)
        already_done: set[int] = {row[0] for row in existing_result.all()}

        classified_count = 0
        has_error = False

        for idx, p7_text in enumerate(p7_descriptions):
            if idx in already_done:
                classified_count += 1
                continue

            try:
                cls_result = await ClassificationService._classify_single_p7(p7_text)
            except Exception:
                logger.exception(
                    "Classification failed for invoice %d, line %d",
                    invoice_id,
                    idx,
                )
                has_error = True
                continue

            # Upsert classification result
            values = {
                "invoice_id": invoice_id,
                "line_index": idx,
                "p7_text": p7_text,
                "verdict": cls_result["verdict"],
                "rate_percent": cls_result["rate_percent"],
                "pkwiu_code": cls_result["pkwiu_code"],
                "pkwiu_description": cls_result["pkwiu_description"],
                "confidence": cls_result["confidence"],
                "reasoning": cls_result["reasoning"],
                "ambiguity_flags": cls_result["ambiguity_flags"],
                "clarification_question": cls_result["clarification_question"],
                "corridor": cls_result["corridor"],
                "llm_calls_count": cls_result["llm_calls_count"],
            }
            upsert_stmt = (
                pg_insert(InvoiceLineClassification)
                .values(**values)
                .on_conflict_do_nothing(constraint="uq_invoice_line")
            )
            await db.execute(upsert_stmt)
            classified_count += 1

        # Resolve invoice-level classification status
        if not has_error and classified_count == len(p7_descriptions):
            # All lines processed — check results
            all_lines_stmt = select(InvoiceLineClassification).where(
                InvoiceLineClassification.invoice_id == invoice_id
            )
            all_lines_result = await db.execute(all_lines_stmt)
            all_lines = all_lines_result.scalars().all()

            all_accepted = all(line.verdict == "ACCEPTED" for line in all_lines)
            if all_accepted:
                rates = {line.rate_percent for line in all_lines if line.rate_percent is not None}
                if len(rates) == 1:
                    invoice.tax_rate = Decimal(str(rates.pop()))
                else:
                    # Multiple different rates — leave NULL, per-line detail available
                    invoice.tax_rate = None
                invoice.is_classified = True
            else:
                # At least one NEEDS_CLARIFICATION — don't mark as classified
                invoice.is_classified = False
                invoice.tax_rate = None

        await db.flush()

        return {
            "lines_classified": classified_count,
            "total_lines": len(p7_descriptions),
            "has_error": has_error,
        }

    @staticmethod
    async def classify_company_invoices(company_id: int, db: AsyncSession) -> dict[str, Any]:
        """Classify all unclassified invoices for a company.

        Returns summary: {"total_invoices": N, "classified": M, "needs_clarification": K, "errors": E}
        """
        payloads = await LLMPayloadService.get_unclassified_payload(company_id, db)
        if not payloads:
            logger.info("No unclassified invoices for company %d", company_id)
            return {
                "total_invoices": 0,
                "classified": 0,
                "needs_clarification": 0,
                "errors": 0,
            }

        logger.info("Classifying %d invoices for company %d", len(payloads), company_id)

        classified = 0
        needs_clarification = 0
        errors = 0

        for payload in payloads:
            invoice_id = payload["invoice_id"]
            try:
                result = await ClassificationService.classify_invoice(invoice_id, db)
                if result.get("has_error"):
                    errors += 1
                else:
                    # Reload invoice to check final status
                    inv_stmt = select(Invoice.is_classified).where(Invoice.id == invoice_id)
                    inv_result = await db.execute(inv_stmt)
                    is_done = inv_result.scalar_one_or_none()
                    if is_done:
                        classified += 1
                    else:
                        needs_clarification += 1
            except Exception:
                logger.exception("Failed to classify invoice %d", invoice_id)
                errors += 1

        await db.commit()

        summary = {
            "total_invoices": len(payloads),
            "classified": classified,
            "needs_clarification": needs_clarification,
            "errors": errors,
        }
        logger.info("Classification complete for company %d: %s", company_id, summary)
        return summary

    @staticmethod
    async def resolve_classification(
        db: AsyncSession,
        company_id: int,
        invoice_id: int,
        line_index: int,
        user_answer: str,
    ) -> dict[str, Any]:
        """Resolve a NEEDS_CLARIFICATION line using the user's answer.

        Re-runs the pipeline with user_context and updates the DB row.
        Returns a summary dict.
        """
        # Fetch the line via JOIN with Invoice — enforces company_id ownership (IDOR protection)
        stmt = (
            select(InvoiceLineClassification)
            .join(Invoice, InvoiceLineClassification.invoice_id == Invoice.id)
            .where(
                InvoiceLineClassification.invoice_id == invoice_id,
                InvoiceLineClassification.line_index == line_index,
                Invoice.company_id == company_id,
            )
        )
        result = await db.execute(stmt)
        line = result.scalar_one_or_none()

        if line is None:
            return {
                "status": "NOT_FOUND",
                "detail": "Line classification not found or access denied",
            }

        # Re-classify with user context
        cls_result = await ClassificationService._classify_single_p7(
            line.p7_text, user_context=user_answer
        )

        # Update the existing row
        line.verdict = cls_result["verdict"]
        line.rate_percent = cls_result["rate_percent"]
        line.pkwiu_code = cls_result["pkwiu_code"]
        line.pkwiu_description = cls_result["pkwiu_description"]
        line.confidence = cls_result["confidence"]
        line.reasoning = cls_result["reasoning"]
        line.ambiguity_flags = cls_result["ambiguity_flags"]
        line.clarification_question = cls_result["clarification_question"]
        line.corridor = cls_result["corridor"]
        line.llm_calls_count += cls_result["llm_calls_count"]

        # Check if the entire invoice is now fully classified
        remaining_stmt = select(InvoiceLineClassification).where(
            InvoiceLineClassification.invoice_id == invoice_id,
            InvoiceLineClassification.verdict == "NEEDS_CLARIFICATION",
            InvoiceLineClassification.line_index != line_index,
        )
        remaining_result = await db.execute(remaining_stmt)
        still_pending = remaining_result.scalars().all()

        # If no more pending lines and this line is now ACCEPTED, mark invoice classified
        if not still_pending and cls_result["verdict"] == "ACCEPTED":
            inv_stmt = select(Invoice).where(Invoice.id == invoice_id)
            inv_result = await db.execute(inv_stmt)
            invoice = inv_result.scalar_one_or_none()
            if invoice:
                invoice.is_classified = True
                # Set tax_rate if single rate
                all_lines_stmt = select(InvoiceLineClassification).where(
                    InvoiceLineClassification.invoice_id == invoice_id
                )
                all_lines_result = await db.execute(all_lines_stmt)
                all_lines = all_lines_result.scalars().all()
                rates = {line.rate_percent for line in all_lines if line.rate_percent is not None}
                invoice.tax_rate = Decimal(str(rates.pop())) if len(rates) == 1 else None

        await db.commit()

        return {
            "status": "RESOLVED",
            "verdict": cls_result["verdict"],
            "invoice_id": invoice_id,
            "line_index": line_index,
        }
