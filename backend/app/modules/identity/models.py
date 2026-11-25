from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.common import utcnow


class Member(Base):
    __tablename__ = "members"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    nickname: Mapped[str] = mapped_column(String(80), default="温泉旅人")
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", server_default="ACTIVE", nullable=False)
    __table_args__ = (UniqueConstraint("phone", name="uq_member_phone"),)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class Identity(Base):
    __tablename__ = "member_identities"
    __table_args__ = (UniqueConstraint("appid", "openid", name="uq_identity_appid_openid"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    appid: Mapped[str] = mapped_column(String(64), nullable=False)
    openid: Mapped[str] = mapped_column(String(128), nullable=False)
    member_id: Mapped[str] = mapped_column(ForeignKey("members.id"), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class MemberSession(Base):
    __tablename__ = "member_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    appid: Mapped[str] = mapped_column(String(64), nullable=False)
    openid: Mapped[str] = mapped_column(String(128), nullable=False)
    member_id: Mapped[str | None] = mapped_column(ForeignKey("members.id"), nullable=True)
    purpose: Mapped[str] = mapped_column(String(16), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
