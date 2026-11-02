from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.auth import AuthContext, CurrentAuth, OperationsAuth, Role
from app.core.config import Settings, get_settings
from app.core.database import Base, engine
from app.core.errors import ApiError, install_error_handling


class DevLoginRequest(BaseModel):
    role: Literal["member", "frontdesk", "merchant", "finance", "admin"] = "member"


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        import app.models  # noqa: F401

        if not settings.is_production:
            Base.metadata.create_all(engine)
            from app.core.database import SessionLocal
            from app.modules.seed import seed_development_data

            with SessionLocal() as session:
                seed_development_data(session)
        yield

    app = FastAPI(
        title="Shunan Hot Spring Operations API",
        version="0.1.0",
        description="Phase-one API. Development payment and device adapters are simulations.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handling(app)

    @app.get("/api/v1/health", tags=["system"])
    def health():
        return {"status": "ok", "version": "v1", "environment": settings.app_env}

    @app.post("/api/v1/auth/dev", tags=["auth"])
    def development_login(
        payload: DevLoginRequest,
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        if settings.is_production or not settings.dev_auth_enabled:
            raise ApiError(403, "DEV_AUTH_DISABLED", "Development authentication is disabled")
        tokens = {
            "member": settings.dev_member_token,
            "frontdesk": settings.dev_frontdesk_token,
            "merchant": settings.dev_merchant_token,
            "finance": settings.dev_finance_token,
            "admin": settings.dev_admin_token,
        }
        return {
            "access_token": tokens[payload.role],
            "token_type": "bearer",
            "role": payload.role,
            "member_id": "member-demo" if payload.role == "member" else None,
            "mode": "development",
        }

    @app.get("/api/v1/auth/me", tags=["auth"])
    def me(auth: CurrentAuth):
        return {"role": auth.role, "member_id": auth.member_id, "appid": auth.appid}

    @app.get("/api/v1/members/{member_id}/profile", tags=["members"])
    def member_profile(member_id: str, auth: CurrentAuth):
        if auth.role != Role.MEMBER or auth.member_id != member_id:
            raise ApiError(403, "RESOURCE_FORBIDDEN", "You can only access your own member profile")
        return {"member_id": member_id, "nickname": "温泉旅人", "mode": "development"}

    @app.get("/api/v1/operations/status", tags=["operations"])
    def operations_status(auth: OperationsAuth):
        return {
            "status": "ok",
            "role": auth.role,
            "payment_mode": settings.payment_provider,
            "device_mode": "mock",
        }

    from app.api import api_router

    app.include_router(api_router)
    return app


app = create_app()
