from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.modules.catalog.models import TicketPriceRule
from app.modules.common import new_business_no, new_id, utcnow
from app.modules.payments.models import Order
from app.modules.tickets.models import Admission, Ticket, TicketBatch


class TicketService:
    @staticmethod
    def prices(session: Session, visit_date: date) -> tuple[int, int]:
        rule = session.get(TicketPriceRule, visit_date)
        if rule:
            return rule.adult_cents, rule.child_cents
        adult = 4_900 if visit_date.weekday() >= 5 else 2_900
        return adult, adult

    @staticmethod
    def create_order(
        session: Session, *, member_id: str, visit_date: date, adult_count: int, child_count: int
    ) -> tuple[TicketBatch, Order]:
        if adult_count < 0 or child_count < 0 or adult_count + child_count <= 0:
            raise ApiError(422, "VISITOR_COUNT_INVALID", "At least one visitor is required")
        if adult_count + child_count > 20:
            raise ApiError(422, "VISITOR_COUNT_INVALID", "At most 20 visitors are allowed per order")
        adult_price, child_price = TicketService.prices(session, visit_date)
        amount = adult_count * adult_price + child_count * child_price
        order = Order(
            id=new_id("ord"), order_no=new_business_no("TK"), member_id=member_id,
            order_type="TICKET", amount_cents=amount,
        )
        batch = TicketBatch(
            id=new_id("tbt"), order_id=order.id, visit_date=visit_date,
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
        ticket = session.scalar(select(Ticket).where(Ticket.ticket_no == ticket_no).with_for_update())
        if ticket is None:
            raise ApiError(404, "TICKET_NOT_FOUND", "Ticket not found")
        existing = session.scalar(select(Admission).where(Admission.ticket_id == ticket.id))
        if existing:
            if existing.request_id == request_id:
                return existing
            raise ApiError(409, "TICKET_ALREADY_USED", "Ticket has already been used for admission")
        if ticket.status != "UNUSED":
            raise ApiError(409, "TICKET_NOT_ADMITTABLE", "Ticket is not valid for admission")
        ticket.status = "USED"
        ticket.used_at = utcnow()
        ticket.used_by = operator
        admission = Admission(id=new_id("adm"), ticket_id=ticket.id, operator=operator, request_id=request_id)
        session.add(admission)
        session.flush()
        return admission
