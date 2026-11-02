from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, Role, require_roles
from app.core.database import get_db
from app.core.errors import ApiError
from app.modules.catalog.models import RechargeActivity
from app.modules.common import new_business_no, new_id
from app.modules.payments.models import Order, Payment
from app.modules.wallet.models import LedgerEntry
from app.modules.wallet.service import WalletService

router = APIRouter(prefix="/api/v1/wallet", tags=["wallet"])
MemberAuth = Annotated[AuthContext, Depends(require_roles(Role.MEMBER))]


class RechargeRequest(BaseModel):
    activity_id: str = Field(min_length=1, max_length=64)


@router.get("/balance")
def balance(auth: MemberAuth, session: Session = Depends(get_db)):
    return {"available_cents": WalletService.available_cents(session, auth.member_id)}


@router.get("/entries")
def entries(auth: MemberAuth, session: Session = Depends(get_db)):
    records = session.scalars(
        select(LedgerEntry).where(LedgerEntry.member_id == auth.member_id)
        .order_by(LedgerEntry.created_at.desc()).limit(100)
    ).all()
    return [
        {
            "reference": item.reference, "entry_type": item.entry_type,
            "delta_cents": item.principal_delta + item.gift_delta,
            "balance_after_cents": item.principal_after + item.gift_after,
            "created_at": item.created_at,
        }
        for item in records
    ]


@router.post("/recharges", status_code=201)
def recharge(payload: RechargeRequest, auth: MemberAuth, session: Session = Depends(get_db)):
    activity = session.get(RechargeActivity, payload.activity_id)
    if activity is None or not activity.active:
        raise ApiError(404, "RECHARGE_ACTIVITY_NOT_FOUND", "Recharge activity not found or inactive")
    order = Order(
        id=new_id("ord"), order_no=new_business_no("RC"), member_id=auth.member_id,
        order_type="RECHARGE", business_id=f"{activity.principal_cents}:{activity.gift_cents}",
        amount_cents=activity.principal_cents, payment_method="WECHAT",
    )
    payment = Payment(
        id=new_id("pay"), payment_no=new_business_no("PY"), order_id=order.id,
        method="WECHAT", amount_cents=order.amount_cents,
    )
    session.add_all([order, payment])
    session.commit()
    return {
        "order_no": order.order_no, "payment_no": payment.payment_no,
        "amount_cents": payment.amount_cents, "payment_method": "wechat",
        "status": payment.status.lower(), "mode": "mock",
    }
