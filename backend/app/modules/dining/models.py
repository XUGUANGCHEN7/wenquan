from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.common import utcnow
from app.modules.rooms.models import Room


class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="热销推荐", nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    stock: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RoomQrCode(Base):
    __tablename__ = "room_qr_codes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id"), index=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    printed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class FoodOrder(Base):
    __tablename__ = "food_orders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), unique=True, nullable=False)
    room_use_id: Mapped[str] = mapped_column(ForeignKey("room_uses.id"), index=True, nullable=False)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id"), index=True, nullable=False)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), index=True, nullable=False)
    fulfillment_status: Mapped[str] = mapped_column(String(24), index=True, default="NOT_READY", nullable=False)
    exception_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    items: Mapped[list["FoodOrderItem"]] = relationship(lazy="selectin")
    room: Mapped[Room] = relationship(lazy="joined")


class FoodOrderItem(Base):
    __tablename__ = "food_order_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    food_order_id: Mapped[str] = mapped_column(ForeignKey("food_orders.id"), index=True, nullable=False)
    menu_item_id: Mapped[str] = mapped_column(ForeignKey("menu_items.id"), nullable=False)
    name_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
