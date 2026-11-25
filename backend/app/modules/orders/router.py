from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, OptionalAuth, Role, require_roles
from app.core.database import get_db
from app.core.errors import ApiError
from app.modules.payments.models import Order, Payment
from app.modules.payments.service import PaymentService

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])
MemberAuth = Annotated[AuthContext, Depends(require_roles(Role.MEMBER))]


class PaymentRequest(BaseModel):
    method: Literal["wechat", "balance"]


def order_dict(order: Order) -> dict:
    from sqlalchemy.orm import object_session
    from app.modules.payments.refund_applications import application_info
    session = object_session(order)
    return {
        "id": order.id,
        "refund_application": application_info(session, order) if session else None,
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
    order = session.get(Order, order_no) or session.scalar(select(Order).where(Order.order_no == order_no))
    if order is None:
        raise ApiError(404, "ORDER_NOT_FOUND", "Order not found")
    assert_order_access(order, auth)
    result = order_dict(order)
    payment = session.scalar(select(Payment).where(Payment.order_id == order.id))
    result["paid_amount_cents"] = payment.amount_cents if payment and payment.status == "SUCCESS" else (0 if order.status == "PENDING" else None)
    if order.order_type == "TICKET":
        from app.modules.tickets.models import Ticket, TicketBatch
        batch = session.get(TicketBatch, order.business_id)
        from app.modules.tickets.service import TicketService
        if batch:
            result.update(TicketService.metadata(session, batch))
        tickets = session.scalars(select(Ticket).where(Ticket.batch_id == order.business_id).order_by(Ticket.visitor_index)).all()
        result.update(visit_date=batch.visit_date if batch else None,
                      adult_count=batch.adult_count if batch else None, child_count=batch.child_count if batch else None,
                      quantity=batch.adult_count + batch.child_count if batch else None,
                      tickets=[{"ticket_no": ticket.ticket_no, "category": ticket.category,
                                "price_cents": ticket.price_cents, "status": ticket.status} for ticket in tickets])
    elif order.order_type == "PRIVATE":
        from app.modules.rooms.models import PrivateBooking, RoomUse
        from app.modules.rooms.router import booking_dict
        booking = session.get(PrivateBooking, order.business_id)
        if booking:
            use = session.scalar(select(RoomUse).where(RoomUse.booking_id == booking.id))
            result.update(booking_dict(booking, order, use))
            result.update(quantity=1, slot_count=booking.slot_count)
    elif order.order_type == "RECHARGE":
        from app.modules.wallet.models import LedgerEntry
        try:
            principal, gift = (int(value) for value in order.business_id.split(":"))
        except (AttributeError, ValueError):
            principal, gift = None, None
        credit = session.scalar(select(LedgerEntry).where(LedgerEntry.member_id == order.member_id,
            LedgerEntry.reference == order.order_no, LedgerEntry.entry_type == "RECHARGE"))
        result.update(quantity=1, principal_cents=principal, gift_cents=gift,
                      credited_cents=credit.principal_delta + credit.gift_delta if credit else (0 if order.status == "PENDING" else None))
    return result


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
