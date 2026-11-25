from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, Role, require_roles
from app.core.database import get_db
from app.core.errors import ApiError
from app.modules.audit import audit
from app.modules.common import utcnow
from app.modules.payments.models import Order, Refund, RefundApplication

router = APIRouter(prefix="/api/v1", tags=["refund-applications"])
MemberAuth = Annotated[AuthContext, Depends(require_roles(Role.MEMBER))]
FinanceAuth = Annotated[AuthContext, Depends(require_roles(Role.FINANCE, Role.ADMIN))]


class ApplyRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class ReviewRequest(ApplyRequest):
    approve: bool


def application_info(session, order):
    application = session.get(RefundApplication, order.id)
    if application is None:
        return None
    refund = session.scalar(select(Refund).where(Refund.refund_no == application.refund_no)) if application.refund_no else None
    return {"order_no": order.order_no, "order_type": order.order_type, "amount_cents": order.amount_cents,
            "status": application.status, "reason": application.reason, "review_reason": application.review_reason,
            "refund_no": application.refund_no, "refund_status": refund.status if refund else None,
            "created_at": application.created_at, "reviewed_at": application.reviewed_at}


def block_pending_refund(session, order_id):
    application = session.get(RefundApplication, order_id)
    if application and application.status == "PENDING":
        raise ApiError(409, "REFUND_REVIEW_PENDING", "退款审核中，暂不能核销，请先处理申请")


def assert_unused(session, order):
    if order.order_type not in ("TICKET", "PRIVATE") or order.status != "PAID":
        raise ApiError(409, "ORDER_NOT_REFUNDABLE", "仅已支付且未使用的公共票、私汤票可申请退款")
    if order.order_type == "TICKET":
        from app.modules.tickets.models import Ticket
        tickets = session.scalars(select(Ticket).where(Ticket.batch_id == order.business_id).with_for_update()).all()
        if not tickets or any(ticket.status != "UNUSED" for ticket in tickets):
            raise ApiError(409, "TICKET_NOT_REFUNDABLE", "票券已使用或失效，不能申请整单退款")
    else:
        from app.modules.rooms.models import PrivateBooking
        booking = session.get(PrivateBooking, order.business_id, with_for_update=True)
        if booking is None or booking.status != "CONFIRMED":
            raise ApiError(409, "PRIVATE_NOT_REFUNDABLE", "私汤已核销、取消或无法使用，不能申请退款")


def owned_order(session, order_no, member_id):
    order = session.scalar(select(Order).where(Order.order_no == order_no).with_for_update())
    if order is None or order.member_id != member_id:
        raise ApiError(404, "ORDER_NOT_FOUND", "订单不存在")
    return order


@router.get("/orders/{order_no}/refund-application")
def get_application(order_no: str, auth: MemberAuth, session: Session = Depends(get_db)):
    return application_info(session, owned_order(session, order_no, auth.member_id))


@router.post("/orders/{order_no}/refund-application")
def apply(order_no: str, payload: ApplyRequest, request: Request, auth: MemberAuth, session: Session = Depends(get_db)):
    order = owned_order(session, order_no, auth.member_id)
    if not payload.reason.strip():
        raise ApiError(422, "REASON_REQUIRED", "请填写退款原因")
    existing = session.get(RefundApplication, order.id)
    if existing and existing.status in ("PENDING", "APPROVED"):
        return application_info(session, order)
    assert_unused(session, order)
    if existing is None:
        existing = RefundApplication(order_id=order.id, reason=payload.reason.strip())
        session.add(existing)
    else:
        existing.status = "PENDING"
        existing.reason = payload.reason.strip()
        existing.review_reason = ""
        existing.reviewed_by = None
        existing.reviewed_at = None
        existing.created_at = utcnow()
    audit(session, actor=auth.role, action="REFUND_APPLIED", entity_type="order", entity_id=order.id,
          before=order.status, after="REFUND_REVIEW_PENDING", reason=payload.reason, request_id=request.state.request_id)
    session.commit()
    return application_info(session, order)


@router.get("/operations/refund-applications")
def applications(auth: FinanceAuth, session: Session = Depends(get_db)):
    orders = session.scalars(select(Order).join(RefundApplication, Order.id == RefundApplication.order_id)
                             .order_by(RefundApplication.created_at.desc()).limit(200)).all()
    return [application_info(session, order) for order in orders]


@router.post("/operations/refund-applications/{order_no}/review")
def review(order_no: str, payload: ReviewRequest, request: Request, auth: FinanceAuth, session: Session = Depends(get_db)):
    order = session.scalar(select(Order).where(Order.order_no == order_no).with_for_update())
    application = session.get(RefundApplication, order.id, with_for_update=True) if order else None
    if application is None:
        raise ApiError(404, "REFUND_APPLICATION_NOT_FOUND", "退款申请不存在")
    if application.status != "PENDING":
        if application.status == ("APPROVED" if payload.approve else "REJECTED"):
            return application_info(session, order)
        raise ApiError(409, "REFUND_ALREADY_REVIEWED", "该申请已处理，不能更改审核结果")
    if not payload.reason.strip():
        raise ApiError(422, "REASON_REQUIRED", "请填写审核意见")
    if payload.approve:
        from app.modules.payments.refunds import RefundService
        assert_unused(session, order)
        refund = RefundService.request_for_order(session, order_no, reason=payload.reason.strip())
        application.refund_no = refund.refund_no
    application.status = "APPROVED" if payload.approve else "REJECTED"
    application.review_reason = payload.reason.strip()
    application.reviewed_by = auth.role
    application.reviewed_at = utcnow()
    audit(session, actor=auth.role, action="REFUND_REVIEWED", entity_type="order", entity_id=order.id,
          before="PENDING", after=application.status, reason=payload.reason, request_id=request.state.request_id)
    session.commit()
    return application_info(session, order)
