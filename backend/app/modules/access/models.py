from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.common import utcnow


class DepositGroup(Base):
    __tablename__ = "deposit_groups"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), unique=True, nullable=False)
    payer_member_id: Mapped[str] = mapped_column(ForeignKey("members.id"), nullable=False)
    unit_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    deposits: Mapped[list["Deposit"]] = relationship(lazy="selectin")


class Deposit(Base):
    __tablename__ = "deposits"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("deposit_groups.id"), index=True, nullable=False)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), unique=True, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="PENDING", nullable=False)
    refund_id: Mapped[str | None] = mapped_column(ForeignKey("refunds.id"), nullable=True)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    binding: Mapped["CardBinding"] = relationship(lazy="joined", uselist=False)


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), unique=True, nullable=False)
    member_id: Mapped[str] = mapped_column(ForeignKey("members.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="PENDING", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    physical_uid: Mapped[str] = mapped_column(String(96), unique=True, nullable=False)
    logical_card_id: Mapped[str] = mapped_column(String(96), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="AVAILABLE", nullable=False)


class Locker(Base):
    __tablename__ = "lockers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    number: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="FREE", nullable=False)


class CardBinding(Base):
    __tablename__ = "card_bindings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    visit_id: Mapped[str] = mapped_column(ForeignKey("visits.id"), unique=True, nullable=False)
    card_id: Mapped[str] = mapped_column(ForeignKey("cards.id"), index=True, nullable=False)
    locker_id: Mapped[str] = mapped_column(ForeignKey("lockers.id"), index=True, nullable=False)
    deposit_id: Mapped[str] = mapped_column(ForeignKey("deposits.id"), unique=True, nullable=False)
    room_use_id: Mapped[str | None] = mapped_column(ForeignKey("room_uses.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="ISSUING", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    bound_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class LockerReservation(Base):
    __tablename__ = "locker_reservations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    locker_id: Mapped[str] = mapped_column(ForeignKey("lockers.id"), index=True, nullable=False)
    binding_id: Mapped[str] = mapped_column(ForeignKey("card_bindings.id"), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="RESERVED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
