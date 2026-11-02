from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.core.errors import ApiError


class Role(StrEnum):
    MEMBER = "member"
    FRONTDESK = "frontdesk"
    MERCHANT = "merchant"
    FINANCE = "finance"
    ADMIN = "admin"
    DEVICE = "device"


@dataclass(frozen=True)
class AuthContext:
    role: Role
    member_id: str | None = None
    appid: str | None = None
    subject: str = ""


bearer = HTTPBearer(auto_error=False)


def _token_context(token: str, settings: Settings) -> AuthContext | None:
    if settings.is_production or not settings.dev_auth_enabled:
        return None
    values = [
        (settings.dev_member_token, Role.MEMBER, "member-demo"),
        (settings.dev_frontdesk_token, Role.FRONTDESK, None),
        (settings.dev_merchant_token, Role.MERCHANT, None),
        (settings.dev_finance_token, Role.FINANCE, None),
        (settings.dev_admin_token, Role.ADMIN, None),
        (settings.device_service_token, Role.DEVICE, None),
    ]
    for expected, role, member_id in values:
        if token == expected:
            return AuthContext(role=role, member_id=member_id, appid="dev-app", subject=role)
    return None


def get_current_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthContext:
    if credentials is None:
        raise ApiError(401, "AUTH_REQUIRED", "Authentication is required")
    context = _token_context(credentials.credentials, settings)
    if context is None:
        raise ApiError(401, "AUTH_INVALID", "Authentication credentials are invalid")
    return context


CurrentAuth = Annotated[AuthContext, Depends(get_current_auth)]


def get_optional_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthContext | None:
    if credentials is None:
        return None
    context = _token_context(credentials.credentials, settings)
    if context is None:
        raise ApiError(401, "AUTH_INVALID", "Authentication credentials are invalid")
    return context


OptionalAuth = Annotated[AuthContext | None, Depends(get_optional_auth)]


def require_roles(*roles: Role):
    def dependency(auth: CurrentAuth) -> AuthContext:
        if auth.role not in roles:
            raise ApiError(403, "RESOURCE_FORBIDDEN", "This role cannot access the resource")
        return auth

    return dependency


OperationsAuth = Annotated[
    AuthContext, Depends(require_roles(Role.FRONTDESK, Role.MERCHANT, Role.FINANCE, Role.ADMIN))
]
