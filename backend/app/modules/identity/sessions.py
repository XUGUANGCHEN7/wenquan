import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.modules.common import utcnow
from app.modules.identity.models import Member, MemberSession


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_session(db: Session, *, appid: str, openid: str, member_id: str | None,
                  purpose: str, seconds: int) -> tuple[str, MemberSession]:
    now = utcnow()
    db.execute(delete(MemberSession).where(MemberSession.expires_at <= now))
    if purpose == 'REGISTER':
        db.execute(delete(MemberSession).where(MemberSession.appid == appid,
                   MemberSession.openid == openid, MemberSession.purpose == 'REGISTER'))
    token = secrets.token_urlsafe(32)
    record = MemberSession(token_hash=token_hash(token), appid=appid, openid=openid,
                           member_id=member_id, purpose=purpose,
                           expires_at=now + timedelta(seconds=seconds))
    db.add(record)
    db.flush()
    return token, record


def require_session(db: Session, token: str, purpose: str, *, lock=False) -> MemberSession:
    statement = select(MemberSession).where(MemberSession.token_hash == token_hash(token))
    if lock:
        statement = statement.with_for_update()
    record = db.scalar(statement)
    if record is None or record.purpose != purpose or record.expires_at <= utcnow():
        raise ApiError(401, 'AUTH_INVALID', '登录凭证已失效，请重新登录')
    return record


def require_active(member: Member | None) -> Member:
    if member is None:
        raise ApiError(401, 'AUTH_INVALID', '会员账户不存在，请重新登录')
    if member.status != 'ACTIVE':
        raise ApiError(403, 'MEMBER_DISABLED', '会员账户已停用，请联系商家')
    return member


def profile(member: Member) -> dict:
    phone = member.phone or ''
    local = phone[3:] if phone.startswith('+86') else phone
    masked = local[:3] + '****' + local[-4:] if len(local) >= 7 else ''
    return {'member_id': member.id, 'nickname': member.nickname,
            'phone_masked': masked, 'phone_verified': member.phone_verified_at is not None}
