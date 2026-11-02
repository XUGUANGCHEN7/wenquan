from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.modules.common import new_id
from app.modules.identity.models import Identity, Member


class IdentityService:
    @staticmethod
    def bind(session: Session, *, appid: str, openid: str, member_id: str, verified: bool) -> Identity:
        if not verified:
            raise ApiError(403, "IDENTITY_NOT_VERIFIED", "Identity ownership must be verified before binding")
        if session.get(Member, member_id) is None:
            raise ApiError(404, "MEMBER_NOT_FOUND", "Member not found")
        existing = session.scalar(select(Identity).where(Identity.appid == appid, Identity.openid == openid))
        if existing:
            if existing.member_id != member_id:
                raise ApiError(409, "IDENTITY_ALREADY_BOUND", "This login identity belongs to another member")
            return existing
        identity = Identity(id=new_id("idn"), appid=appid, openid=openid, member_id=member_id)
        session.add(identity)
        session.flush()
        return identity
