from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import OptionalAuth
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.modules.payments.service import PaymentService

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post("/{payment_no}/mock-confirm")
def mock_confirm(
    payment_no: str,
    auth: OptionalAuth,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    enabled = settings.dev_auth_enabled and not settings.is_production and settings.payment_provider == "mock"
    payment = PaymentService.confirm_mock(
        session, payment_no, member_id=auth.member_id if auth else None, mock_enabled=enabled
    )
    session.commit()
    return {"payment_no": payment.payment_no, "status": payment.status.lower(), "mode": "mock"}
