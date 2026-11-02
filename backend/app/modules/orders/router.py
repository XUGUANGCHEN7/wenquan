from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, OptionalAuth, Role, require_roles
from app.core.database import get_db
from app.core.errors import ApiError
from app.modules.payments.models import Order
from app.modules.payments.service import PaymentService

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])
MemberAuth = Annotated[AuthContext, Depends(require_roles(Role.MEMBER))]


class PaymentRequest(BaseModel):
    method: Literal["wechat", "balance"]


def order_dict(order: Order) -> dict:
    return {
        "order_no": order.order_no, "order_type": order.order_type, "status": order.status,
        "business_id": order.business_id,
        "amount_cents": order.amount_cents, "payment_method": order.payment_method,
        "created_at": order.created_at, "paid_at": order.paid_at,
    }


def assert_order_access(order: Order, auth: AuthContext | None) -> None:
    if order.member_id is None:
        return
    operations = {Role.FRONTDESK, Role.FINANCE, Role.ADMIN, Role.MERCHANT}
    if auth is None or (auth.role == Role.MEMBER and auth.member_id != order.member_id) or auth.role not in operations | {Role.MEMBER}:
        raise ApiError(403, "RESOURCE_FORBIDDEN", "You cannot access this order")


@router.get("")
def my_orders(auth: MemberAuth, session: Session = Depends(get_db)):
    orders = session.scalars(select(Order).where(Order.member_id == auth.member_id)
                             .order_by(Order.created_at.desc()).limit(100)).all()
    return [order_dict(order) for order in orders]


@router.get("/{order_no}")
def order_detail(order_no: str, auth: OptionalAuth, session: Session = Depends(get_db)):
    order = session.scalar(select(Order).where(Order.order_no == order_no))
    if order is None:
        raise ApiError(404, "ORDER_NOT_FOUND", "Order not found")
    assert_order_access(order, auth)
    return order_dict(order)


@router.post("/{order_no}/payments", status_code=201)
def create_payment(order_no: str, payload: PaymentRequest, auth: OptionalAuth,
                   session: Session = Depends(get_db)):
    order = session.scalar(select(Order).where(Order.order_no == order_no))
    if order is None:
        raise ApiError(404, "ORDER_NOT_FOUND", "Order not found")
    assert_order_access(order, auth)
    member_id = auth.member_id if auth and auth.role == Role.MEMBER else None
    payment = PaymentService.create_payment(session, order_no, member_id, payload.method.upper())
    session.commit()
    return {"payment_no": payment.payment_no, "order_no": order.order_no,
            "status": payment.status.lower(), "amount_cents": payment.amount_cents,
            "payment_method": payment.method.lower(), "mode": "mock" if payment.method == "WECHAT" else "server"}
