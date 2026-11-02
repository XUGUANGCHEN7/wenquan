from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, Role, require_roles
from app.core.database import get_db
from app.core.errors import ApiError
from app.modules.access.models import Card, CardBinding, Deposit, Locker, LockerReservation
from app.modules.access.service import AccessService
from app.modules.audit import audit
from app.modules.devices.models import DeviceTask
from app.modules.devices.router import task_dict
from app.modules.payments.models import Order

router = APIRouter(prefix="/api/v1/operations", tags=["operations-access"])
DeskAuth = Annotated[AuthContext, Depends(require_roles(Role.FRONTDESK, Role.ADMIN))]


class IssueRequest(BaseModel):
    deposit_id: str
    card_id: str


class ReturnRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class DepositOrderRequest(BaseModel):
    payer_member_id: str
    ticket_nos: list[str] = Field(min_length=1)


@router.get("/access/overview")
def overview(auth: DeskAuth, session: Session = Depends(get_db)):
    cards = session.scalars(select(Card).order_by(Card.id)).all()
    lockers = session.scalars(select(Locker).order_by(Locker.number)).all()
    deposits = session.scalars(select(Deposit).order_by(Deposit.created_at.desc()).limit(100)).all()
    bindings = session.scalars(select(CardBinding).order_by(CardBinding.created_at.desc()).limit(100)).all()
    tasks = session.scalars(select(DeviceTask).order_by(DeviceTask.created_at.desc()).limit(100)).all()
    return {"cards": [{"id": item.id, "physical_uid": item.physical_uid, "status": item.status} for item in cards],
            "lockers": [{"id": item.id, "number": item.number, "status": item.status} for item in lockers],
            "deposits": [{"id": item.id, "ticket_id": item.ticket_id, "amount_cents": item.amount_cents,
                          "status": item.status, "refund_id": item.refund_id} for item in deposits],
            "bindings": [{"id": item.id, "card_id": item.card_id, "locker_id": item.locker_id,
                          "deposit_id": item.deposit_id, "room_use_id": item.room_use_id,
                          "status": item.status} for item in bindings],
            "device_tasks": [task_dict(item) for item in tasks]}


@router.post("/deposits/orders", status_code=201)
def deposit_order(payload: DepositOrderRequest, auth: DeskAuth, session: Session = Depends(get_db)):
    group, order = AccessService.create_deposit_order(session, **payload.model_dump())
    session.commit()
    return {"group_id": group.id, "order_no": order.order_no, "amount_cents": order.amount_cents,
            "deposit_ids": [item.id for item in group.deposits]}


@router.post("/deposits/{deposit_id}/refund")
def refund_deposit(deposit_id: str, payload: ReturnRequest, request: Request,
                   auth: DeskAuth, session: Session = Depends(get_db)):
    refund = AccessService.refund_unissued_deposit(session, deposit_id, reason=payload.reason)
    audit(session, actor=auth.role, action="UNISSUED_DEPOSIT_REFUNDED", entity_type="deposit",
          entity_id=deposit_id, before="PAID", after=refund.status, reason=payload.reason,
          request_id=request.state.request_id)
    session.commit()
    return {"deposit_id": deposit_id, "refund_no": refund.refund_no, "status": refund.status}


@router.post("/cards/issue", status_code=201)
def issue(payload: IssueRequest, request: Request, auth: DeskAuth, session: Session = Depends(get_db)):
    binding, task = AccessService.issue_card(session, payload.deposit_id, card_id=payload.card_id,
                                             operator=auth.role, request_id=request.state.request_id)
    audit(session, actor=auth.role, action="CARD_ISSUE_REQUESTED", entity_type="card_binding",
          entity_id=binding.id, before=None, after=binding.status, reason="Front desk issue",
          request_id=request.state.request_id)
    session.commit()
    return {"binding_id": binding.id, "locker_id": binding.locker_id,
            "status": binding.status, "task": task_dict(task)}


@router.post("/cards/{binding_id}/return")
def return_card(binding_id: str, payload: ReturnRequest, request: Request,
                auth: DeskAuth, session: Session = Depends(get_db)):
    binding, refund, task = AccessService.return_card(
        session, binding_id, operator=auth.role, reason=payload.reason, request_id=request.state.request_id)
    audit(session, actor=auth.role, action="CARD_RETURNED", entity_type="card_binding",
          entity_id=binding.id, before="BOUND", after=binding.status, reason=payload.reason,
          request_id=request.state.request_id)
    session.commit()
    return {"binding_id": binding.id, "status": binding.status, "refund_no": refund.refund_no,
            "refund_status": refund.status, "clear_task": task_dict(task)}


@router.post("/lockers/{locker_id}/cleaned")
def locker_cleaned(locker_id: str, payload: ReturnRequest, request: Request,
                   auth: DeskAuth, session: Session = Depends(get_db)):
    locker = session.get(Locker, locker_id, with_for_update=True)
    binding = session.scalar(select(CardBinding).where(CardBinding.locker_id == locker_id)
                             .order_by(CardBinding.created_at.desc()).limit(1))
    if locker is None or locker.status != "CLEANING" or binding is None or binding.status not in ("CLEARED", "CLEAR_FAILED"):
        raise ApiError(409, "LOCKER_NOT_RELEASABLE", "Card recovery and locker cleaning must be recorded first")
    locker.status = "FREE"
    reservation = session.scalar(select(LockerReservation).where(LockerReservation.binding_id == binding.id))
    reservation.status = "RELEASED"
    audit(session, actor=auth.role, action="LOCKER_RELEASED", entity_type="locker", entity_id=locker.id,
          before="CLEANING", after="FREE", reason=payload.reason, request_id=request.state.request_id)
    session.commit()
    return {"id": locker.id, "status": locker.status}
