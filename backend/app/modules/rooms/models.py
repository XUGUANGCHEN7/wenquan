from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.common import utcnow


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    number: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RoomBlock(Base):
    __tablename__ = "room_blocks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id"), index=True, nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class PrivateBooking(Base):
    __tablename__ = "private_bookings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), unique=True, nullable=False)
    member_id: Mapped[str] = mapped_column(ForeignKey("members.id"), index=True, nullable=False)
    internal_room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id"), index=True, nullable=False)
    visit_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    slot_indices: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    slot_count: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    cleaning_end_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expected_arrival_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(24), index=True, default="HELD", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class RoomUse(Base):
    __tablename__ = "room_uses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    booking_id: Mapped[str] = mapped_column(ForeignKey("private_bookings.id"), unique=True, nullable=False)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id"), index=True, nullable=False)
    member_id: Mapped[str] = mapped_column(ForeignKey("members.id"), index=True, nullable=False)
    actual_start_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    actual_end_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    cleaning_end_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(24), index=True, default="ACTIVE", nullable=False)
    room: Mapped[Room] = relationship(lazy="joined")


class RoomExtension(Base):
    __tablename__ = "room_extensions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    room_use_id: Mapped[str] = mapped_column(ForeignKey("room_uses.id"), index=True, nullable=False)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), unique=True, nullable=False)
    binding_id: Mapped[str] = mapped_column(ForeignKey("card_bindings.id"), nullable=False)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="PENDING", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class CleaningRecord(Base):
    __tablename__ = "cleaning_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    room_use_id: Mapped[str] = mapped_column(ForeignKey("room_uses.id"), unique=True, nullable=False)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id"), index=True, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    operator: Mapped[str] = mapped_column(String(96), nullable=False)
