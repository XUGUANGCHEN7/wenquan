from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.modules.catalog.models import BusinessConfig, TicketPriceRule
from app.modules.common import new_business_no, new_id, utcnow
from app.modules.payments.models import Order
from app.modules.tickets.models import Admission, Ticket, TicketBatch


class TicketService:
    @staticmethod
    def is_holiday(session: Session, day: date) -> bool:
        rule = session.get(TicketPriceRule, day)
        return day.weekday() >= 5 or bool(rule and rule.is_holiday)

    @staticmethod
    def product_prices(session: Session, day_type: str) -> tuple[int, int]:
        holiday = day_type == "HOLIDAY"
        adult = TicketService._config(session, "ticket_weekend_cents" if holiday else "ticket_weekday_cents", 4900 if holiday else 2900)
        child = TicketService._config(session, "ticket_holiday_child_cents" if holiday else "ticket_weekday_child_cents", TicketService._config(session, "ticket_child_cents", adult))
        return adult, child

    @staticmethod
    def eligibility_error(session: Session, batch: TicketBatch):
        if not batch.day_type:  # Preserve existing dated orders.
            return None
        now = utcnow()
        if batch.valid_until is None:
            return ("TICKET_NOT_PAID", "门票尚未付款生效")
        if now >= batch.valid_until:
            return ("TICKET_EXPIRED", "门票已超过付款后30天有效期")
        holiday = TicketService.is_holiday(session, (now + timedelta(hours=8)).date())
        if holiday != (batch.day_type == "HOLIDAY"):
            return ("TICKET_DAY_TYPE_MISMATCH", "今天不符合该门票的工作日或节假日使用规则")
        return None

    @staticmethod
    def metadata(session: Session, batch: TicketBatch) -> dict:
        error = TicketService.eligibility_error(session, batch)
        return {"day_type": batch.day_type, "valid_days": batch.valid_days, "valid_until": batch.valid_until,
                "admission_error": {"code": error[0], "message": error[1]} if error else None}

    @staticmethod
    def _config(session: Session, key: str, default: int) -> int:
        config = session.get(BusinessConfig, key)
        return config.value if config else default

    @staticmethod
    def prices(session: Session, visit_date: date) -> tuple[int, int]:
        rule = session.get(TicketPriceRule, visit_date)
        if rule:
            return rule.adult_cents, rule.child_cents
        adult = TicketService._config(
            session,
            "ticket_weekend_cents" if visit_date.weekday() >= 5 else "ticket_weekday_cents",
            4_900 if visit_date.weekday() >= 5 else 2_900,
        )
        child = TicketService._config(session, "ticket_child_cents", adult)
        return adult, child

    @staticmethod
    def create_order(
        session: Session, *, member_id: str, visit_date: date | None = None, day_type: str | None = None, adult_count: int, child_count: int
    ) -> tuple[TicketBatch, Order]:
        if adult_count < 0 or child_count < 0 or adult_count + child_count <= 0:
            raise ApiError(422, "VISITOR_COUNT_INVALID", "At least one visitor is required")
        if adult_count + child_count > 20:
            raise ApiError(422, "VISITOR_COUNT_INVALID", "At most 20 visitors are allowed per order")
        if (visit_date is None) == (day_type is None) or (day_type is not None and day_type not in ("WEEKDAY", "HOLIDAY")):
            raise ApiError(422, "TICKET_PRODUCT_INVALID", "请选择工作日票或节假日票；旧版日期订单不能同时指定票种")
        adult_price, child_price = TicketService.product_prices(session, day_type) if day_type else TicketService.prices(session, visit_date)
        amount = adult_count * adult_price + child_count * child_price
        order = Order(
            id=new_id("ord"), order_no=new_business_no("TK"), member_id=member_id,
            order_type="TICKET", amount_cents=amount,
        )
        batch = TicketBatch(
            id=new_id("tbt"), order_id=order.id, visit_date=visit_date,
            day_type=day_type, valid_days=30 if day_type else None,
            adult_count=adult_count, child_count=child_count,
            adult_unit_cents=adult_price, child_unit_cents=child_price,
        )
        order.business_id = batch.id
        session.add_all([order, batch])
        session.flush()
        return batch, order

    @staticmethod
    def mark_paid(session: Session, order: Order) -> str:
        batch = session.get(TicketBatch, order.business_id, with_for_update=True)
        if batch is None:
            raise ApiError(409, "ORDER_INVALID", "Ticket batch is missing")
        existing = session.scalar(select(func.count(Ticket.id)).where(Ticket.batch_id == batch.id))
        if existing:
            return "PAID"
        if batch.day_type:
            batch.valid_until = (order.paid_at or utcnow()) + timedelta(days=batch.valid_days)
        total = batch.adult_count + batch.child_count
        for index in range(total):
            category = "ADULT" if index < batch.adult_count else "CHILD"
            price = batch.adult_unit_cents if category == "ADULT" else batch.child_unit_cents
            session.add(Ticket(
                id=new_id("tkt"), batch_id=batch.id, ticket_no=new_business_no("TC"),
                visitor_index=index, category=category, price_cents=price,
            ))
        session.flush()
        return "PAID"

    @staticmethod
    def admit(session: Session, ticket_no: str, *, operator: str, request_id: str) -> Admission:
        ticket = session.scalar(select(Ticket).where(Ticket.ticket_no == ticket_no))
        if ticket is None:
            raise ApiError(404, "TICKET_NOT_FOUND", "Ticket not found")
        batch = session.get(TicketBatch, ticket.batch_id)
        session.get(Order, batch.order_id, with_for_update=True)
        ticket = session.get(Ticket, ticket.id, with_for_update=True, populate_existing=True)
        from app.modules.payments.refund_applications import block_pending_refund
        block_pending_refund(session, batch.order_id)
        existing = session.scalar(select(Admission).where(Admission.ticket_id == ticket.id))
        if existing:
            if existing.request_id == request_id:
                return existing
            raise ApiError(409, "TICKET_ALREADY_USED", "Ticket has already been used for admission")
        if ticket.status != "UNUSED":
            raise ApiError(409, "TICKET_NOT_ADMITTABLE", "Ticket is not valid for admission")
        error = TicketService.eligibility_error(session, batch)
        if error:
            raise ApiError(409, *error)
        ticket.status = "USED"
        ticket.used_at = utcnow()
        ticket.used_by = operator
        admission = Admission(id=new_id("adm"), ticket_id=ticket.id, operator=operator, request_id=request_id)
        session.add(admission)
        session.flush()
        return admission
