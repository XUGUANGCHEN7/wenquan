from datetime import date, datetime, time, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, Role, require_roles
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import ApiError
from app.modules.access.models import Deposit
from app.modules.audit import audit
from app.modules.catalog.models import BusinessConfig
from app.modules.common import utcnow
from app.modules.dining.models import FoodOrder
from app.modules.devices.models import DeviceTask
from app.modules.payments.models import AuditEvent, Order, Refund
from app.modules.rooms.models import PrivateBooking
from app.modules.wallet.models import LedgerEntry, MemberAccount

router = APIRouter(prefix="/api/v1", tags=["operations"])
FinanceAuth = Annotated[AuthContext, Depends(require_roles(Role.FINANCE, Role.ADMIN))]
DeskFinanceAuth = Annotated[AuthContext, Depends(require_roles(Role.FRONTDESK, Role.FINANCE, Role.ADMIN))]
AdminAuth = Annotated[AuthContext, Depends(require_roles(Role.ADMIN))]


class ConfigRequest(BaseModel):
    value: int = Field(ge=0)
    description: str = Field(min_length=1, max_length=500)


class RefundRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class MockRefundRequest(BaseModel):
    status: Literal["SUCCESS", "FAILED", "UNKNOWN"]


@router.post("/operations/orders/{order_no}/refunds")
def request_order_refund(order_no: str, payload: RefundRequest, request: Request,
                         auth: FinanceAuth, session: Session = Depends(get_db)):
    from app.modules.payments.refunds import RefundService

    refund = RefundService.request_for_order(session, order_no, reason=payload.reason)
    audit(session, actor=auth.role, action="ORDER_REFUND_REQUESTED", entity_type="refund",
          entity_id=refund.id, before=None, after=refund.status, reason=payload.reason,
          request_id=request.state.request_id)
    session.commit()
    return {"refund_no": refund.refund_no, "status": refund.status,
            "amount_cents": refund.amount_cents}


@router.post("/operations/refunds/{refund_no}/mock-result")
def mock_refund_result(refund_no: str, payload: MockRefundRequest, request: Request,
                       auth: FinanceAuth, session: Session = Depends(get_db),
                       settings: Settings = Depends(get_settings)):
    from app.modules.payments.refunds import RefundService

    if not settings.dev_auth_enabled or settings.is_production or settings.payment_provider != "mock":
        raise ApiError(403, "MOCK_REFUND_DISABLED", "Mock refund result is disabled")
    refund = RefundService.set_mock_result(session, refund_no, status=payload.status)
    audit(session, actor=auth.role, action="MOCK_REFUND_RESULT", entity_type="refund",
          entity_id=refund.id, before=None, after=refund.status, reason="Development-only channel simulation",
          request_id=request.state.request_id)
    session.commit()
    return {"refund_no": refund.refund_no, "status": refund.status}


@router.get("/operations/wallet/{member_id}")
def wallet_detail(member_id: str, auth: FinanceAuth, session: Session = Depends(get_db)):
    account = session.get(MemberAccount, member_id)
    if account is None:
        raise ApiError(404, "WALLET_NOT_FOUND", "Member wallet not found")
    entries = session.scalars(select(LedgerEntry).where(LedgerEntry.member_id == member_id)
                              .order_by(LedgerEntry.created_at.desc()).limit(200)).all()
    return {"member_id": member_id, "principal_cents": account.principal_cents,
            "gift_cents": account.gift_cents, "available_cents": account.principal_cents + account.gift_cents,
            "entries": [{"id": item.id, "entry_type": item.entry_type, "reference": item.reference,
                         "principal_delta": item.principal_delta, "gift_delta": item.gift_delta,
                         "principal_after": item.principal_after, "gift_after": item.gift_after,
                         "original_entry_id": item.original_entry_id, "created_at": item.created_at}
                        for item in entries]}


@router.get("/operations/reports/daily")
def daily_report(auth: DeskFinanceAuth, report_date: date | None = None, session: Session = Depends(get_db)):
    day = report_date or utcnow().date()
    start = datetime.combine(day, time.min)
    orders = session.scalars(select(Order).where(Order.status == "PAID", Order.paid_at >= start,
                                                 Order.paid_at < start + timedelta(days=1))).all()
    totals = {kind: sum(order.amount_cents for order in orders if order.order_type == kind)
              for kind in ("TICKET", "PRIVATE", "FOOD", "EXTENSION")}
    deposits = session.scalar(select(func.coalesce(func.sum(Deposit.amount_cents), 0)).where(
        Deposit.status.in_(["PAID", "REFUND_PENDING"])))
    ledger = session.scalars(select(LedgerEntry).where(LedgerEntry.entry_type == "RECHARGE",
                                                       LedgerEntry.created_at >= start,
                                                       LedgerEntry.created_at < start + timedelta(days=1))).all()
    return {"report_date": day, "ticket_revenue_cents": totals["TICKET"],
            "private_revenue_cents": totals["PRIVATE"], "dining_revenue_cents": totals["FOOD"],
            "extension_revenue_cents": totals["EXTENSION"],
            "recharge_principal_cents": sum(item.principal_delta for item in ledger),
            "recharge_gift_cents": sum(item.gift_delta for item in ledger),
            "unrefunded_deposit_cents": deposits, "deposit_is_revenue": False}


@router.get("/operations/exceptions")
def exceptions(auth: DeskFinanceAuth, session: Session = Depends(get_db)):
    refunds = session.scalars(select(Refund).where(Refund.status.in_(["ACCEPTED", "PROCESSING", "UNKNOWN", "FAILED"]))).all()
    paid_exceptions = session.scalars(select(Order).where(Order.status == "EXCEPTION")).all()
    unknown = session.scalars(select(DeviceTask).where(DeviceTask.status == "UNKNOWN")).all()
    conflicts = session.scalars(select(PrivateBooking).where(PrivateBooking.status == "CONFLICT")).all()
    food = session.scalars(select(FoodOrder).where(FoodOrder.fulfillment_status == "EXCEPTION")).all()
    return {"refunds": [{"refund_no": item.refund_no, "status": item.status, "amount_cents": item.amount_cents} for item in refunds],
            "paid_exceptions": [{"order_no": item.order_no, "order_type": item.order_type,
                                 "amount_cents": item.amount_cents, "status": item.status} for item in paid_exceptions],
            "device_unknown": [{"id": item.id, "task_no": item.task_no, "raw_error": item.raw_error} for item in unknown],
            "room_conflicts": [{"id": item.id, "order_id": item.order_id, "status": item.status} for item in conflicts],
            "food_delivery": [{"id": item.id, "reason": item.exception_reason} for item in food]}


@router.get("/operations/audit")
def audit_events(auth: AdminAuth, session: Session = Depends(get_db)):
    events = session.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(200)).all()
    return [{"id": item.id, "actor": item.actor, "action": item.action, "entity_type": item.entity_type,
             "entity_id": item.entity_id, "before_status": item.before_status,
             "after_status": item.after_status, "reason": item.reason,
             "request_id": item.request_id, "created_at": item.created_at} for item in events]


@router.post("/admin/config/{key}")
def update_config(key: str, payload: ConfigRequest, request: Request,
                  auth: AdminAuth, session: Session = Depends(get_db)):
    allowed = {"private_slot_price_cents", "deposit_amount_cents", "extension_price_cents", "extension_minutes"}
    if key not in allowed or (key == "extension_minutes" and payload.value == 0):
        raise ApiError(422, "CONFIG_INVALID", "Configuration key or value is not supported")
    config = session.get(BusinessConfig, key, with_for_update=True)
    before = str(config.value) if config else None
    if config is None:
        config = BusinessConfig(key=key, value=payload.value, description=payload.description)
        session.add(config)
    else:
        config.value = payload.value
        config.description = payload.description
    audit(session, actor=auth.role, action="CONFIG_UPDATED", entity_type="business_config", entity_id=key,
          before=before, after=str(payload.value), reason=payload.description, request_id=request.state.request_id)
    session.commit()
    return {"key": key, "value": config.value, "description": config.description}
