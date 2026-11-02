from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, Role, require_roles
from app.core.database import get_db
from app.core.errors import ApiError
from app.modules.payments.models import Order
from app.modules.tickets.models import Ticket, TicketBatch
from app.modules.tickets.service import TicketService

router = APIRouter(prefix="/api/v1", tags=["tickets"])
MemberAuth = Annotated[AuthContext, Depends(require_roles(Role.MEMBER))]
DeskAuth = Annotated[AuthContext, Depends(require_roles(Role.FRONTDESK, Role.ADMIN))]


class TicketOrderRequest(BaseModel):
    visit_date: date
    adult_count: int = Field(ge=0, le=20)
    child_count: int = Field(ge=0, le=20)


class AdmitRequest(BaseModel):
    ticket_no: str
    request_id: str = Field(min_length=4, max_length=64)
    reason: str = Field(default="Manual verification", max_length=500)


@router.post("/tickets/orders", status_code=201)
def create_order(payload: TicketOrderRequest, auth: MemberAuth, session: Session = Depends(get_db)):
    batch, order = TicketService.create_order(session, member_id=auth.member_id, **payload.model_dump())
    session.commit()
    return {"order_no": order.order_no, "batch_id": batch.id, "amount_cents": order.amount_cents,
            "status": order.status, "adult_unit_cents": batch.adult_unit_cents,
            "child_unit_cents": batch.child_unit_cents}


@router.get("/tickets/orders/{order_no}")
def order_detail(order_no: str, auth: MemberAuth, session: Session = Depends(get_db)):
    order = session.scalar(select(Order).where(Order.order_no == order_no))
    if order is None or order.member_id != auth.member_id or order.order_type != "TICKET":
        raise ApiError(404, "ORDER_NOT_FOUND", "Ticket order not found")
    batch = session.get(TicketBatch, order.business_id)
    tickets = session.scalars(select(Ticket).where(Ticket.batch_id == batch.id)
                              .order_by(Ticket.visitor_index)).all()
    return {"order_no": order.order_no, "status": order.status, "amount_cents": order.amount_cents,
            "visit_date": batch.visit_date, "tickets": [
                {"ticket_no": item.ticket_no, "category": item.category, "price_cents": item.price_cents,
                 "status": item.status} for item in tickets]}


@router.post("/operations/tickets/admit")
def admit(payload: AdmitRequest, auth: DeskAuth, session: Session = Depends(get_db)):
    from app.modules.audit import audit

    admission = TicketService.admit(session, payload.ticket_no, operator=auth.role,
                                    request_id=payload.request_id)
    audit(session, actor=auth.role, action="TICKET_ADMITTED", entity_type="ticket",
          entity_id=admission.ticket_id, before="UNUSED", after="USED", reason=payload.reason,
          request_id=payload.request_id)
    session.commit()
    return {"admission_id": admission.id, "ticket_id": admission.ticket_id,
            "admitted_at": admission.admitted_at, "operator": admission.operator}
