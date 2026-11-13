from datetime import date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, Role, require_roles
from app.core.database import get_db
from app.core.errors import ApiError
from app.modules.audit import audit
from app.modules.common import utcnow
from app.modules.identity.models import Member
from app.modules.identity.sessions import profile
from app.modules.payments.models import Order
from app.modules.rooms.models import PrivateBooking, RoomUse
from app.modules.rooms.service import RoomService
from app.modules.tickets.models import Admission, Ticket, TicketBatch
from app.modules.tickets.service import TicketService

router = APIRouter(prefix="/api/v1/operations", tags=["operations-verification"])
DeskAuth = Annotated[AuthContext, Depends(require_roles(Role.FRONTDESK, Role.ADMIN))]
DeskFinanceAuth = Annotated[AuthContext, Depends(require_roles(Role.FRONTDESK, Role.FINANCE, Role.ADMIN))]


class VerificationRequest(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    request_id: str = Field(min_length=4, max_length=64)
    reason: str = Field(default="前台人工核验", max_length=500)
    actual_start: datetime | None = None


def _ticket_order(session: Session, code: str) -> tuple[Ticket | None, Order | None]:
    ticket = session.scalar(select(Ticket).where(Ticket.ticket_no == code))
    if ticket:
        batch = session.get(TicketBatch, ticket.batch_id)
        return ticket, session.get(Order, batch.order_id) if batch else None
    order = session.scalar(select(Order).where(Order.order_no == code, Order.order_type == "TICKET"))
    if order is None:
        return None, None
    batch = session.get(TicketBatch, order.business_id)
    if batch is None:
        return None, order
    ticket = session.scalar(
        select(Ticket).where(Ticket.batch_id == batch.id, Ticket.status == "UNUSED")
        .order_by(Ticket.visitor_index).limit(1)
    )
    return ticket, order


@router.get("/verification-summary")
def verification_summary(auth: DeskFinanceAuth, report_date: date | None = None,
                         session: Session = Depends(get_db)):
    day = report_date or utcnow().date()
    start = datetime.combine(day, time.min)
    end = start + timedelta(days=1)
    ticket_count = session.scalar(select(func.count(Admission.id)).where(
        Admission.admitted_at >= start, Admission.admitted_at < end)) or 0
    private_count = session.scalar(select(func.count(RoomUse.id)).where(
        RoomUse.actual_start_at >= start, RoomUse.actual_start_at < end)) or 0
    return {"report_date": day, "ticket_verifications": ticket_count,
            "private_verifications": private_count}


@router.get("/orders/{order_no}")
def order_lookup(order_no: str, auth: DeskFinanceAuth, session: Session = Depends(get_db)):
    order = session.scalar(select(Order).where(Order.order_no == order_no))
    if order is None:
        raise ApiError(404, "ORDER_NOT_FOUND", "订单不存在")
    member = session.get(Member, order.member_id) if order.member_id else None
    result = {
        "order_no": order.order_no, "order_type": order.order_type, "status": order.status,
        "amount_cents": order.amount_cents, "payment_method": order.payment_method,
        "created_at": order.created_at, "paid_at": order.paid_at,
        "member_id": order.member_id, "member": profile(member) if member else None,
    }
    if order.order_type == "TICKET":
        batch = session.get(TicketBatch, order.business_id)
        tickets = session.scalars(select(Ticket).where(Ticket.batch_id == batch.id)
                                  .order_by(Ticket.visitor_index)).all() if batch else []
        result["tickets"] = [{"ticket_no": item.ticket_no, "category": item.category,
                              "price_cents": item.price_cents, "status": item.status} for item in tickets]
    if order.order_type == "PRIVATE":
        booking = session.get(PrivateBooking, order.business_id)
        if booking:
            room_use = session.scalar(select(RoomUse).where(RoomUse.booking_id == booking.id))
            result["private_booking"] = {
                "booking_id": booking.id, "status": booking.status, "visit_date": booking.visit_date,
                "slot_indices": booking.slot_indices, "start_at": booking.start_at,
                "end_at": booking.end_at, "room_use_id": room_use.id if room_use else None,
            }
    return result


@router.post("/tickets/admit-code")
def admit_code(payload: VerificationRequest, request: Request, auth: DeskAuth,
               session: Session = Depends(get_db)):
    existing = session.scalar(select(Admission).where(Admission.request_id == payload.request_id))
    if existing:
        ticket = session.get(Ticket, existing.ticket_id)
        batch = session.get(TicketBatch, ticket.batch_id) if ticket else None
        order = session.get(Order, batch.order_id) if batch else None
        remaining = session.scalar(select(func.count(Ticket.id)).where(
            Ticket.batch_id == ticket.batch_id, Ticket.status == "UNUSED")) if ticket and batch else 0
        return {"admission_id": existing.id, "ticket_no": ticket.ticket_no if ticket else None,
                "order_no": order.order_no if order else None, "remaining_tickets": remaining or 0,
                "admitted_at": existing.admitted_at}

    code = payload.code.strip()
    ticket, order = _ticket_order(session, code)
    if ticket is None:
        if order is not None:
            raise ApiError(409, "NO_UNUSED_TICKET", "该订单没有可核验的未使用票券")
        raise ApiError(404, "TICKET_OR_ORDER_NOT_FOUND", "票券编号或订单编号不存在")
    admission = TicketService.admit(session, ticket.ticket_no, operator=auth.role,
                                    request_id=payload.request_id)
    audit(session, actor=auth.role, action="TICKET_ADMITTED", entity_type="ticket",
          entity_id=admission.ticket_id, before="UNUSED", after="USED", reason=payload.reason,
          request_id=payload.request_id)
    batch = session.get(TicketBatch, ticket.batch_id)
    order = session.get(Order, batch.order_id) if batch else None
    remaining = session.scalar(select(func.count(Ticket.id)).where(
        Ticket.batch_id == ticket.batch_id, Ticket.status == "UNUSED")) or 0
    session.commit()
    return {"admission_id": admission.id, "ticket_no": ticket.ticket_no,
            "order_no": order.order_no if order else None, "remaining_tickets": remaining,
            "admitted_at": admission.admitted_at}


@router.post("/rooms/verify-code")
def verify_private(payload: VerificationRequest, request: Request, auth: DeskAuth,
                   session: Session = Depends(get_db)):
    code = payload.code.strip()
    order = session.scalar(select(Order).where(Order.order_no == code, Order.order_type == "PRIVATE"))
    booking = session.get(PrivateBooking, order.business_id) if order else session.get(PrivateBooking, code)
    if booking is None:
        raise ApiError(404, "PRIVATE_ORDER_NOT_FOUND", "私汤订单或预约不存在")
    existing = session.scalar(select(RoomUse).where(RoomUse.booking_id == booking.id))
    if existing:
        return {"booking_id": booking.id, "room_use_id": existing.id,
                "room_number": existing.room.number, "status": existing.status,
                "actual_end_at": existing.actual_end_at, "already_verified": True}
    if booking.status != "CONFIRMED":
        raise ApiError(409, "PRIVATE_ORDER_NOT_CONFIRMED", "订单尚未支付确认，不能核验分房")
    actual_start = payload.actual_start or utcnow()
    use = RoomService.assign_booking(session, booking.id, actual_start=actual_start, operator=auth.role,
                                     reason=payload.reason, request_id=request.state.request_id)
    if use is None:
        session.commit()
        raise ApiError(409, "ASSIGNMENT_CONFLICT", "没有可覆盖完整使用与清洁区间的房间，请前台按规则处理")
    audit(session, actor=auth.role, action="PRIVATE_BOOKING_VERIFIED", entity_type="room_use",
          entity_id=use.id, before="CONFIRMED", after=use.status, reason=payload.reason,
          request_id=request.state.request_id)
    session.commit()
    return {"booking_id": booking.id, "room_use_id": use.id, "room_number": use.room.number,
            "status": use.status, "actual_end_at": use.actual_end_at,
            "cleaning_end_at": use.cleaning_end_at, "already_verified": False}
