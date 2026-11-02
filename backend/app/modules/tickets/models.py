from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.common import utcnow


class TicketBatch(Base):
    __tablename__ = "ticket_batches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), unique=True, nullable=False)
    visit_date: Mapped[date] = mapped_column(Date, nullable=False)
    adult_count: Mapped[int] = mapped_column(Integer, nullable=False)
    child_count: Mapped[int] = mapped_column(Integer, nullable=False)
    adult_unit_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    child_unit_cents: Mapped[int] = mapped_column(Integer, nullable=False)


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (UniqueConstraint("batch_id", "visitor_index", name="uq_ticket_batch_visitor"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("ticket_batches.id"), index=True, nullable=False)
    ticket_no: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    visitor_index: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="UNUSED", nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    used_by: Mapped[str | None] = mapped_column(String(96), nullable=True)


class Admission(Base):
    __tablename__ = "admissions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), unique=True, nullable=False)
    operator: Mapped[str] = mapped_column(String(96), nullable=False)
    request_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    admitted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
