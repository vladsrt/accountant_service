from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base, bigint_pk

if TYPE_CHECKING:
    from app.db.models.company import Company


class KsefSession(Base):
    __tablename__ = "ksef_sessions"

    id: Mapped[bigint_pk]
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), unique=True
    )
    access_token: Mapped[str] = mapped_column(String)
    refresh_token: Mapped[str] = mapped_column(String)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Back-reference to Company (one-to-one)
    company: Mapped[Company] = relationship(back_populates="ksef_session")

    def __repr__(self) -> str:
        return f"<KsefSession(id={self.id}, company_id={self.company_id})>"
