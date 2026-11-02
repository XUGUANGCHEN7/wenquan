from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.common import utcnow


class RechargeActivity(Base):
    __tablename__ = "recharge_activities"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    principal_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    gift_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class TicketPriceRule(Base):
    __tablename__ = "ticket_price_rules"

    visit_date: Mapped[date] = mapped_column(Date, primary_key=True)
    adult_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    child_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    is_holiday: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note: Mapped[str] = mapped_column(String(200), default="", nullable=False)


class BusinessConfig(Base):
    __tablename__ = "business_configs"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
