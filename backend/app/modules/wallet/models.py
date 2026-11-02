from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.common import utcnow


class MemberAccount(Base):
    __tablename__ = "member_accounts"
    __table_args__ = (
        CheckConstraint("principal_cents >= 0", name="ck_account_principal_nonnegative"),
        CheckConstraint("gift_cents >= 0", name="ck_account_gift_nonnegative"),
    )

    member_id: Mapped[str] = mapped_column(ForeignKey("members.id"), primary_key=True)
    principal_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gift_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class LedgerEntry(Base):
    __tablename__ = "wallet_ledger_entries"
    __table_args__ = (
        UniqueConstraint("member_id", "entry_type", "reference", name="uq_ledger_member_type_reference"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    member_id: Mapped[str] = mapped_column(ForeignKey("members.id"), index=True, nullable=False)
    entry_type: Mapped[str] = mapped_column(String(24), nullable=False)
    reference: Mapped[str] = mapped_column(String(96), nullable=False)
    principal_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    gift_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    principal_after: Mapped[int] = mapped_column(Integer, nullable=False)
    gift_after: Mapped[int] = mapped_column(Integer, nullable=False)
    original_entry_id: Mapped[str | None] = mapped_column(ForeignKey("wallet_ledger_entries.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
