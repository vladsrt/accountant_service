from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base, bigint_pk

from datetime import datetime

if TYPE_CHECKING:
    from app.db.models.invoice import Invoice
    from app.db.models.ksef import KsefSession


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[bigint_pk]
    nip: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    ksef_token: Mapped[str] = mapped_column(String)
    last_sync_hwm_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # One-to-one relationship with KsefSession
    ksef_session: Mapped[KsefSession | None] = relationship(
        back_populates="company", uselist=False, cascade="all, delete-orphan"
    )

    # One-to-many relationship with Invoice
    invoices: Mapped[list[Invoice]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Company(id={self.id}, nip={self.nip!r})>"
