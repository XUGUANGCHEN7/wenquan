from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.common import utcnow


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (CheckConstraint("amount_cents >= 0", name="ck_order_amount_nonnegative"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_no: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    member_id: Mapped[str | None] = mapped_column(ForeignKey("members.id"), index=True, nullable=True)
    order_type: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    business_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), index=True, default="PENDING", nullable=False)
    payment_method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount_cents >= 0", name="ck_payment_amount_nonnegative"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payment_no: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), unique=True, nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="PENDING", nullable=False)
    channel_transaction_id: Mapped[str | None] = mapped_column(String(96), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    refund_no: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    payment_id: Mapped[str] = mapped_column(ForeignKey("payments.id"), index=True, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="ACCEPTED", nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    channel_reference: Mapped[str | None] = mapped_column(String(96), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    actor: Mapped[str] = mapped_column(String(96), nullable=False)
    action: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(96), nullable=False)
    before_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    after_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True, nullable=False)
