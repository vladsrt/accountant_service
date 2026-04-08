"""Pydantic schemas for classification API endpoints."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class LineClassificationResponse(BaseModel):
    """Single P_7 line item classification result."""

    id: int
    line_index: int
    p7_text: str
    verdict: str
    rate_percent: Decimal | None
    pkwiu_code: str | None
    pkwiu_description: str | None
    confidence: float
    reasoning: str | None
    ambiguity_flags: list[str] | None
    clarification_question: str | None
    corridor: str | None
    llm_calls_count: int
    classified_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceClassificationResponse(BaseModel):
    """Classification results for an entire invoice."""

    invoice_id: int
    invoice_number: str | None
    is_classified: bool
    tax_rate: Decimal | None
    lines: list[LineClassificationResponse]

    model_config = ConfigDict(from_attributes=True)


class PendingLineResponse(BaseModel):
    """A single line that needs user clarification."""

    line_index: int
    p7_text: str
    clarification_question: str | None
    ambiguity_flags: list[str] | None


class PendingInvoiceResponse(BaseModel):
    """Invoice with NEEDS_CLARIFICATION lines — for UI to show questions."""

    invoice_id: int
    invoice_number: str | None
    questions: list[PendingLineResponse]


class ClassificationTriggerResponse(BaseModel):
    """Response after triggering classification."""

    status: str
    task_id: str | None = None


class ClassificationSummaryResponse(BaseModel):
    """Summary of classification results for a company."""

    total_invoices: int
    classified: int
    needs_clarification: int
    errors: int


class ClarificationResolveRequest(BaseModel):
    """Request to resolve a NEEDS_CLARIFICATION line with user's answer."""

    invoice_id: int
    line_index: int
    user_answer: str
