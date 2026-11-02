from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.modules.access.models import Deposit, DepositGroup
from app.modules.common import new_id
from app.modules.payments.models import Order, Payment, Refund
from app.modules.wallet.service import WalletService


class RefundService:
    @staticmethod
    def request_for_order(session: Session, order_no: str, *, reason: str) -> Refund:
        order = session.scalar(select(Order).where(Order.order_no == order_no).with_for_update())
        if order is None:
            raise ApiError(404, "ORDER_NOT_FOUND", "Order not found")
        if order.order_type in ("DEPOSIT", "RECHARGE", "FOOD", "EXTENSION"):
            raise ApiError(409, "REFUND_FLOW_NOT_SUPPORTED",
                           "Use the domain-specific return flow; food/extension refunds need manual policy confirmation")
        refund_no = f"RO-{order.order_no}"
        existing = session.scalar(select(Refund).where(Refund.refund_no == refund_no))
        if existing:
            return existing
        if order.status not in ("PAID", "EXCEPTION"):
            raise ApiError(409, "ORDER_NOT_REFUNDABLE", "Only a paid or paid-exception order can enter refund processing")
        payment = session.scalar(select(Payment).where(Payment.order_id == order.id).with_for_update())
        if payment is None or payment.status != "SUCCESS":
            raise ApiError(409, "ORIGINAL_PAYMENT_INVALID", "Original payment is not confirmed")
        if order.order_type == "TICKET":
            from app.modules.tickets.models import Ticket, TicketBatch

            batch = session.get(TicketBatch, order.business_id)
            for ticket in session.scalars(select(Ticket).where(Ticket.batch_id == batch.id).with_for_update()):
                if ticket.status == "USED":
                    raise ApiError(409, "TICKET_ALREADY_USED", "A used ticket cannot use this manual refund flow")
                ticket.status = "VOID"
        if order.order_type == "PRIVATE":
            from app.modules.rooms.models import PrivateBooking

            booking = session.get(PrivateBooking, order.business_id, with_for_update=True)
            if booking.status in ("IN_USE", "COMPLETED"):
                raise ApiError(409, "ROOM_USE_STARTED", "An in-use or completed booking needs operator review")
            booking.status = "CANCELLED"
        if payment.method == "BALANCE":
            reversal = WalletService.refund(session, order.member_id, order.order_no, f"RF-W-{order.order_no}")
            refund = Refund(id=new_id("ref"), refund_no=refund_no, payment_id=payment.id,
                            amount_cents=order.amount_cents, status="SUCCESS", reason=reason,
                            channel_reference=reversal.id)
            order.status = "REFUNDED"
        else:
            refund = Refund(id=new_id("ref"), refund_no=refund_no, payment_id=payment.id,
                            amount_cents=order.amount_cents, status="ACCEPTED", reason=reason)
        session.add(refund)
        session.flush()
        return refund

    @staticmethod
    def set_mock_result(session: Session, refund_no: str, *, status: str) -> Refund:
        if status not in ("SUCCESS", "FAILED", "UNKNOWN"):
            raise ApiError(422, "REFUND_RESULT_INVALID", "Unsupported refund result")
        refund = session.scalar(select(Refund).where(Refund.refund_no == refund_no).with_for_update())
        if refund is None:
            raise ApiError(404, "REFUND_NOT_FOUND", "Refund not found")
        if refund.status == "SUCCESS":
            return refund
        refund.status = status
        refund.channel_reference = f"mock-{refund_no}"
        deposit = session.scalar(select(Deposit).where(Deposit.refund_id == refund.id).with_for_update())
        if deposit:
            deposit.status = "REFUNDED" if status == "SUCCESS" else "EXCEPTION"
        payment = session.get(Payment, refund.payment_id)
        order = session.get(Order, payment.order_id)
        if status == "SUCCESS":
            if deposit:
                group = session.get(DepositGroup, deposit.group_id)
                remaining = session.scalar(select(func.count(Deposit.id)).where(
                    Deposit.group_id == group.id, Deposit.status != "REFUNDED"))
                if remaining == 0:
                    order.status = "REFUNDED"
            else:
                order.status = "REFUNDED"
        elif status == "FAILED" and not deposit:
            order.status = "EXCEPTION"
        session.flush()
        return refund
    @staticmethod
    def request_for_deposit(session: Session, deposit: Deposit, *, reason: str) -> Refund:
        refund_no = f"DR-{deposit.id}"
        existing = session.scalar(select(Refund).where(Refund.refund_no == refund_no))
        if existing:
            return existing
        group = session.get(DepositGroup, deposit.group_id, with_for_update=True)
        order = session.get(Order, group.order_id)
        payment = session.scalar(select(Payment).where(Payment.order_id == order.id).with_for_update())
        if payment is None or payment.status != "SUCCESS" or payment.method != "WECHAT":
            raise ApiError(409, "ORIGINAL_PAYMENT_INVALID", "Original WeChat deposit payment is not confirmed")
        refunded = session.scalar(select(func.coalesce(func.sum(Refund.amount_cents), 0)).where(
            Refund.payment_id == payment.id, Refund.status.notin_(["FAILED", "CLOSED"])))
        if refunded + deposit.amount_cents > payment.amount_cents:
            raise ApiError(409, "REFUND_EXCEEDS_PAYMENT", "Cumulative refunds cannot exceed the original payment")
        refund = Refund(id=new_id("ref"), refund_no=refund_no, payment_id=payment.id,
                        amount_cents=deposit.amount_cents, reason=reason)
        deposit.status = "REFUND_PENDING"
        deposit.refund_id = refund.id
        session.add(refund)
        session.flush()
        return refund
