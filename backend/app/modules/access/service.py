from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.modules.access.models import (
    Card, CardBinding, Deposit, DepositGroup, Locker, LockerReservation, Visit,
)
from app.modules.catalog.models import BusinessConfig
from app.modules.common import new_business_no, new_id, utcnow
from app.modules.devices.service import DeviceService
from app.modules.payments.models import Order, Refund
from app.modules.payments.refunds import RefundService
from app.modules.tickets.models import Ticket, TicketBatch


class AccessService:
    @staticmethod
    def create_deposit_order(session: Session, *, payer_member_id: str,
                             ticket_nos: list[str]) -> tuple[DepositGroup, Order]:
        if not ticket_nos or len(ticket_nos) != len(set(ticket_nos)):
            raise ApiError(422, "DEPOSIT_TICKETS_INVALID", "Each visitor ticket must be listed once")
        config = session.get(BusinessConfig, "deposit_amount_cents")
        if config is None or config.value <= 0:
            raise ApiError(409, "DEPOSIT_NOT_CONFIGURED", "Deposit amount is not configured")
        tickets = session.scalars(select(Ticket).where(Ticket.ticket_no.in_(ticket_nos))).all()
        if len(tickets) != len(ticket_nos) or any(ticket.status != "UNUSED" for ticket in tickets):
            raise ApiError(409, "TICKET_NOT_VALID", "Every visitor needs an independent unused ticket")
        for ticket in tickets:
            if session.scalar(select(Deposit.id).where(Deposit.ticket_id == ticket.id)):
                raise ApiError(409, "DEPOSIT_ALREADY_EXISTS", "A deposit already exists for this ticket")
        order = Order(id=new_id("ord"), order_no=new_business_no("DP"), member_id=payer_member_id,
                      order_type="DEPOSIT", amount_cents=config.value * len(tickets), payment_method="WECHAT")
        group = DepositGroup(id=new_id("dpg"), order_id=order.id, payer_member_id=payer_member_id,
                             unit_amount_cents=config.value)
        order.business_id = group.id
        session.add_all([order, group])
        session.flush()
        for ticket in tickets:
            session.add(Deposit(id=new_id("dep"), group_id=group.id, ticket_id=ticket.id,
                                amount_cents=config.value))
        session.flush()
        return group, order

    @staticmethod
    def mark_deposit_paid(session: Session, order: Order) -> str:
        group = session.get(DepositGroup, order.business_id, with_for_update=True)
        if group is None:
            raise ApiError(409, "ORDER_INVALID", "Deposit group is missing")
        for deposit in group.deposits:
            if deposit.status == "PENDING":
                deposit.status = "PAID"
        session.flush()
        return "PAID"

    @staticmethod
    def issue_card(session: Session, deposit_id: str, *, card_id: str,
                   operator: str, request_id: str):
        existing = session.scalar(select(CardBinding).where(CardBinding.deposit_id == deposit_id))
        if existing:
            task = DeviceService.create_task(
                session, task_type="ISSUE_CARD", idempotency_key=f"issue-{existing.id}", operator=operator,
                binding_id=existing.id, card_id=existing.card_id, locker_id=existing.locker_id)
            return existing, task
        deposit = session.get(Deposit, deposit_id, with_for_update=True)
        if deposit is None or deposit.status != "PAID":
            raise ApiError(409, "DEPOSIT_NOT_PAID", "The deposit for this band must be paid")
        ticket = session.get(Ticket, deposit.ticket_id, with_for_update=True)
        if ticket is None or ticket.status != "UNUSED":
            raise ApiError(409, "TICKET_NOT_VALID", "An independent valid ticket is required before issue")
        card = session.get(Card, card_id, with_for_update=True)
        if card is None or card.status != "AVAILABLE":
            raise ApiError(409, "CARD_NOT_AVAILABLE", "Physical card is not available")
        locker = session.scalar(select(Locker).where(Locker.status == "FREE")
                                .order_by(Locker.number).limit(1).with_for_update())
        if locker is None:
            raise ApiError(409, "NO_LOCKER_AVAILABLE", "No free locker is available")
        batch = session.get(TicketBatch, ticket.batch_id)
        order = session.get(Order, batch.order_id)
        visit = Visit(id=new_id("vis"), ticket_id=ticket.id, member_id=order.member_id)
        binding = CardBinding(id=new_id("bnd"), visit_id=visit.id, card_id=card.id,
                              locker_id=locker.id, deposit_id=deposit.id)
        session.add_all([visit, binding])
        session.flush()
        session.add(LockerReservation(id=new_id("lkr"), locker_id=locker.id, binding_id=binding.id))
        card.status = "RESERVED"
        locker.status = "RESERVED"
        task = DeviceService.create_task(
            session, task_type="ISSUE_CARD", idempotency_key=f"issue-{binding.id}", operator=operator,
            binding_id=binding.id, card_id=card.id, locker_id=locker.id,
            payload={"verification": "write_then_readback", "mode": "adapter_neutral"})
        session.flush()
        return binding, task

    @staticmethod
    def refund_unissued_deposit(session: Session, deposit_id: str, *, reason: str):
        deposit = session.get(Deposit, deposit_id, with_for_update=True)
        if deposit is None:
            raise ApiError(404, "DEPOSIT_NOT_FOUND", "Deposit not found")
        existing = session.scalar(select(Refund).where(Refund.refund_no == f"DR-{deposit.id}"))
        if existing:
            return existing
        if deposit.status != "PAID":
            raise ApiError(409, "DEPOSIT_NOT_REFUNDABLE", "Only a paid, unissued deposit can be refunded")
        binding = session.scalar(select(CardBinding).where(CardBinding.deposit_id == deposit.id))
        if binding and binding.status == "BOUND":
            raise ApiError(409, "CARD_ALREADY_BOUND", "A bound wristband must use the physical return flow")
        return RefundService.request_for_deposit(session, deposit, reason=reason)

    @staticmethod
    def return_card(session: Session, binding_id: str, *, operator: str,
                    reason: str, request_id: str):
        binding = session.get(CardBinding, binding_id, with_for_update=True)
        if binding is None:
            raise ApiError(404, "CARD_BINDING_NOT_FOUND", "Card binding not found")
        deposit = session.get(Deposit, binding.deposit_id, with_for_update=True)
        existing_refund = session.scalar(select(Refund).where(Refund.refund_no == f"DR-{deposit.id}"))
        if existing_refund:
            clear_task = DeviceService.create_task(
                session, task_type="CLEAR_CARD", idempotency_key=f"clear-{binding.id}", operator=operator,
                binding_id=binding.id, card_id=binding.card_id, locker_id=binding.locker_id)
            return binding, existing_refund, clear_task
        if binding.status != "BOUND":
            raise ApiError(409, "CARD_NOT_RETURNABLE", "Only a bound card can be returned")
        binding.status = "RETURNED"
        binding.returned_at = utcnow()
        deposit.returned_at = binding.returned_at
        visit = session.get(Visit, binding.visit_id)
        visit.status = "RETURNED"
        card = session.get(Card, binding.card_id, with_for_update=True)
        locker = session.get(Locker, binding.locker_id, with_for_update=True)
        card.status = "CLEARING"
        locker.status = "CLEANING"
        refund = RefundService.request_for_deposit(session, deposit, reason=reason)
        clear_task = DeviceService.create_task(
            session, task_type="CLEAR_CARD", idempotency_key=f"clear-{binding.id}", operator=operator,
            binding_id=binding.id, card_id=card.id, locker_id=locker.id)
        session.flush()
        return binding, refund, clear_task
