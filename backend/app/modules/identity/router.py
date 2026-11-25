from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import CurrentAuth, Role, bearer
from app.core.database import get_db
from app.core.errors import ApiError
from app.core.config import get_settings
from app.modules.common import new_id, utcnow
from app.modules.identity.models import Identity, Member
from app.modules.identity.sessions import issue_session, require_session, require_active, profile
from app.modules.identity.wechat import WechatClient, get_wechat_client
from app.modules.wallet.models import MemberAccount

router = APIRouter(prefix='/api/v1', tags=['member-auth'])
Wechat = Annotated[WechatClient, Depends(get_wechat_client)]


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    code: str = Field(min_length=1, max_length=256)


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    registration_token: str = Field(min_length=20, max_length=256)
    phone_code: str = Field(min_length=1, max_length=256)
    nickname: str = Field(default='', max_length=80)
    consent: Literal[True]


def authenticated(db: Session, member: Member, *, appid: str, openid: str) -> dict:
    seconds = get_settings().member_session_seconds
    token, _ = issue_session(db, appid=appid, openid=openid, member_id=member.id,
                             purpose='MEMBER', seconds=seconds)
    return {'status': 'AUTHENTICATED', 'access_token': token, 'token_type': 'bearer',
            'expires_in': seconds, **profile(member)}


@router.post('/auth/wechat/login')
def login(payload: LoginRequest, wechat: Wechat, db: Session = Depends(get_db)):
    openid = wechat.exchange_login(payload.code)
    identity = db.scalar(select(Identity).where(Identity.appid == wechat.appid, Identity.openid == openid))
    member = require_active(db.get(Member, identity.member_id)) if identity else None
    if member and member.phone and member.phone_verified_at:
        result = authenticated(db, member, appid=wechat.appid, openid=openid)
    else:
        token, _ = issue_session(db, appid=wechat.appid, openid=openid,
                                 member_id=member.id if member else None,
                                 purpose='REGISTER', seconds=600)
        result = {'status': 'REGISTER_REQUIRED', 'registration_token': token, 'expires_in': 600}
    db.commit()
    return result


@router.post('/auth/wechat/register')
def register(payload: RegisterRequest, wechat: Wechat, db: Session = Depends(get_db)):
    pending = require_session(db, payload.registration_token, 'REGISTER', lock=True)
    if pending.appid != wechat.appid:
        raise ApiError(401, 'AUTH_INVALID', '登录配置已变化，请重新登录')
    phone = wechat.exchange_phone(payload.phone_code)
    identity = db.scalar(select(Identity).where(Identity.appid == pending.appid, Identity.openid == pending.openid))
    member = require_active(db.get(Member, identity.member_id)) if identity else None
    owner = db.scalar(select(Member).where(Member.phone == phone))
    if owner and (not member or owner.id != member.id):
        raise ApiError(409, 'PHONE_ALREADY_REGISTERED', '手机号已关联其他会员，请联系商家核验，余额不会自动合并')
    if member and member.phone and member.phone != phone:
        raise ApiError(409, 'PHONE_CHANGE_NOT_ALLOWED', '请通过商家核验变更手机号')
    try:
        if member is None:
            member = Member(id=new_id('member'))
            db.add(member)
            db.flush()
            db.add(MemberAccount(member_id=member.id, principal_cents=0, gift_cents=0))
            db.add(Identity(id=new_id('idn'), appid=pending.appid, openid=pending.openid, member_id=member.id))
        member.phone = phone
        member.phone_verified_at = utcnow()
        member.nickname = payload.nickname.strip() or (member.nickname if identity else '会员' + phone[-4:])
        appid, openid = pending.appid, pending.openid
        db.delete(pending)
        result = authenticated(db, member, appid=appid, openid=openid)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, 'REGISTRATION_CONFLICT', '注册状态已变化，请重新登录；不会重复创建账户') from None
    return result


@router.get('/members/me')
def me(auth: CurrentAuth, db: Session = Depends(get_db)):
    if auth.role != Role.MEMBER:
        raise ApiError(403, 'RESOURCE_FORBIDDEN', '仅会员可以访问自己的资料')
    return profile(require_active(db.get(Member, auth.member_id)))


@router.post('/auth/logout')
def logout(auth: CurrentAuth, credentials=Depends(bearer), db: Session = Depends(get_db)):
    if auth.role != Role.MEMBER:
        raise ApiError(403, 'RESOURCE_FORBIDDEN', '仅会员可以退出会员登录')
    record = require_session(db, credentials.credentials, 'MEMBER')
    db.delete(record)
    db.commit()
    return {'status': 'LOGGED_OUT'}
