from __future__ import annotations

import enum
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime

from app.db.database import Base, bigint_pk

if TYPE_CHECKING:
    from app.db.models.company import Company
    from app.db.models.invoice_line_classification import InvoiceLineClassification


class InvoiceStatus(str, enum.Enum):
    PENDING_DOWNLOAD = "PENDING_DOWNLOAD"
    DOWNLOADED = "DOWNLOADED"
    PARSED = "PARSED"
    ERROR = "ERROR"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[bigint_pk]
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    ksef_reference_number: Mapped[str] = mapped_column(String, unique=True, index=True)
    invoice_number: Mapped[str | None] = mapped_column(String, nullable=True)
    issue_date: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    seller_nip: Mapped[str | None] = mapped_column(String(10), nullable=True)
    buyer_nip: Mapped[str | None] = mapped_column(String(10), nullable=True)
    total_gross: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    xml_file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    xml_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoicestatus"),
        default=InvoiceStatus.PENDING_DOWNLOAD,
        index=True,
    )
    parsed_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # AI Classification Prep Fields
    tax_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    is_classified: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)

    # Back-reference to Company (many-to-one)
    company: Mapped[Company] = relationship(back_populates="invoices")

    # AI classification results (one-to-many)
    line_classifications: Mapped[list[InvoiceLineClassification]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Invoice(id={self.id}, "
            f"ksef_ref={self.ksef_reference_number!r}, "
            f"status={self.status!r})>"
        )
