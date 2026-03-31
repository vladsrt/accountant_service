"""BankTransaction model — stores parsed and deduplicated bank statement rows."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base, bigint_pk

if TYPE_CHECKING:
    from app.db.models.company import Company


class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id: Mapped[bigint_pk]
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payee: Mapped[str | None] = mapped_column(String, nullable=True)
    memo: Mapped[str | None] = mapped_column(String, nullable=True)
    transaction_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String, default="UNMATCHED", nullable=False)

    # Back-reference to Company (many-to-one)
    company: Mapped[Company] = relationship(back_populates="bank_transactions")

    def __repr__(self) -> str:
        return (
            f"<BankTransaction(id={self.id}, "
            f"date={self.date}, amount={self.amount}, "
            f"hash={self.transaction_hash[:12]}...)>"
        )
