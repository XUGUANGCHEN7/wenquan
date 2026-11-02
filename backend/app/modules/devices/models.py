from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.common import utcnow


class DeviceTask(Base):
    __tablename__ = "device_tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_no: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    task_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), index=True, default="PENDING", nullable=False)
    operator: Mapped[str] = mapped_column(String(96), nullable=False)
    reader_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    binding_id: Mapped[str | None] = mapped_column(ForeignKey("card_bindings.id"), index=True, nullable=True)
    card_id: Mapped[str | None] = mapped_column(ForeignKey("cards.id"), nullable=True)
    locker_id: Mapped[str | None] = mapped_column(ForeignKey("lockers.id"), nullable=True)
    room_id: Mapped[str | None] = mapped_column(ForeignKey("rooms.id"), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    raw_error: Mapped[str] = mapped_column(Text, default="", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
