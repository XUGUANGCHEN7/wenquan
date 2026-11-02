from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.modules.common import utcnow
from app.modules.payments.models import Order, Payment
from app.modules.wallet.service import WalletService


class PaymentService:
    @staticmethod
    def _dispatch(session: Session, order: Order) -> str:
        if order.order_type == "RECHARGE":
            principal, gift = (int(value) for value in order.business_id.split(":", maxsplit=1))
            WalletService.credit(session, order.member_id, principal, gift, order.order_no)
            return "PAID"
        if order.order_type == "TICKET":
            from app.modules.tickets.service import TicketService

            return TicketService.mark_paid(session, order)
        if order.order_type == "PRIVATE":
            from app.modules.rooms.service import RoomService

            return RoomService.confirm_paid(session, order)
        if order.order_type == "FOOD":
            from app.modules.dining.service import DiningService

            return DiningService.mark_paid(session, order)
        if order.order_type == "DEPOSIT":
            from app.modules.access.service import AccessService

            return AccessService.mark_deposit_paid(session, order)
        if order.order_type == "EXTENSION":
            from app.modules.rooms.extension import RoomExtensionService

            return RoomExtensionService.confirm_paid(session, order)
        raise ApiError(422, "UNSUPPORTED_ORDER_TYPE", "This order type is not enabled yet")

    @staticmethod
    def create_payment(session: Session, order_no: str, member_id: str | None, method: str) -> Payment:
        from app.modules.common import new_business_no, new_id

        order = session.scalar(select(Order).where(Order.order_no == order_no).with_for_update())
        if order is None or order.member_id != member_id:
            raise ApiError(404, "ORDER_NOT_FOUND", "Order not found")
        if order.status != "PENDING":
            raise ApiError(409, "ORDER_NOT_PAYABLE", "Order is not pending payment")
        if method not in ("WECHAT", "BALANCE"):
            raise ApiError(422, "PAYMENT_METHOD_INVALID", "Unsupported payment method")
        if method == "BALANCE" and member_id is None:
            raise ApiError(403, "MEMBER_REQUIRED", "Balance payment requires an authenticated member")
        if method == "BALANCE" and order.order_type in ("RECHARGE", "DEPOSIT"):
            raise ApiError(409, "WECHAT_ONLY", "Recharge and deposits require WeChat payment")
        payment = session.scalar(select(Payment).where(Payment.order_id == order.id).with_for_update())
        if payment and payment.method != method:
            raise ApiError(409, "PAYMENT_METHOD_CONFLICT", "Order already has a different payment method")
        if payment is None:
            payment = Payment(id=new_id("pay"), payment_no=new_business_no("PY"), order_id=order.id,
                              method=method, amount_cents=order.amount_cents)
            session.add(payment)
            session.flush()
        order.payment_method = method
        if method == "BALANCE" and payment.status != "SUCCESS":
            WalletService.debit(session, member_id, order.amount_cents, order.order_no)
            payment.status = "SUCCESS"
            payment.channel_transaction_id = f"wallet-{order.order_no}"
            payment.confirmed_at = utcnow()
            order.status = PaymentService._dispatch(session, order)
            order.paid_at = payment.confirmed_at
        session.flush()
        return payment

    @staticmethod
    def confirm_mock(session: Session, payment_no: str, *, member_id: str | None, mock_enabled: bool) -> Payment:
        if not mock_enabled:
            raise ApiError(403, "MOCK_PAYMENT_DISABLED", "Mock payment confirmation is disabled")
        payment = session.scalar(select(Payment).where(Payment.payment_no == payment_no).with_for_update())
        if payment is None:
            raise ApiError(404, "PAYMENT_NOT_FOUND", "Payment not found")
        order = session.get(Order, payment.order_id, with_for_update=True)
        if order is None or order.member_id != member_id:
            raise ApiError(403, "RESOURCE_FORBIDDEN", "You can only confirm your own development payment")
        if payment.status == "SUCCESS":
            return payment
        if payment.method != "WECHAT":
            raise ApiError(409, "PAYMENT_METHOD_CONFLICT", "Only WeChat development payments use this confirmation")

        payment.status = "SUCCESS"
        payment.channel_transaction_id = f"mock-{payment.payment_no}"
        payment.confirmed_at = utcnow()
        order.status = PaymentService._dispatch(session, order)
        order.paid_at = payment.confirmed_at
        session.flush()
        return payment
