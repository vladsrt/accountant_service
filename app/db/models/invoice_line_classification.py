"""InvoiceLineClassification model — stores AI classification results per P_7 line item."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Float, ForeignKey, Numeric, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime

from app.db.database import Base, bigint_pk

if TYPE_CHECKING:
    from app.db.models.invoice import Invoice


class InvoiceLineClassification(Base):
    __tablename__ = "invoice_line_classifications"
    __table_args__ = (UniqueConstraint("invoice_id", "line_index", name="uq_invoice_line"),)

    id: Mapped[bigint_pk]
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), index=True
    )
    line_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    p7_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Classification results
    verdict: Mapped[str] = mapped_column(String(30), nullable=False)
    rate_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    pkwiu_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pkwiu_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    ambiguity_flags: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    clarification_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    corridor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    llm_calls_count: Mapped[int] = mapped_column(SmallInteger, default=0)

    # Metadata
    classified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Back-reference to Invoice (many-to-one)
    invoice: Mapped[Invoice] = relationship(back_populates="line_classifications")

    def __repr__(self) -> str:
        return (
            f"<InvoiceLineClassification(id={self.id}, "
            f"invoice_id={self.invoice_id}, line={self.line_index}, "
            f"verdict={self.verdict!r})>"
        )
