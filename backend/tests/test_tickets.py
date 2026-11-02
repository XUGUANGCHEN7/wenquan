from datetime import date

import pytest
from sqlalchemy import select

from test_wallet_identity import make_member


def test_ticket_order_uses_server_price_snapshots_and_admits_each_ticket_once(db):
    from app.modules.payments.service import PaymentService
    from app.modules.tickets.models import Ticket
    from app.modules.tickets.service import TicketService
    from app.modules.wallet.service import WalletService

    make_member(db, "member-tickets")
    WalletService.credit(db, "member-tickets", 100_000, 0, "ticket-funds")
    batch, order = TicketService.create_order(
        db, member_id="member-tickets", visit_date=date(2026, 11, 2), adult_count=2, child_count=1
    )
    assert order.amount_cents == 3 * 2_900
    assert (batch.adult_unit_cents, batch.child_unit_cents) == (2_900, 2_900)

    payment = PaymentService.create_payment(db, order.order_no, "member-tickets", "BALANCE")
    db.commit()
    assert payment.status == "SUCCESS"
    tickets = db.scalars(select(Ticket).where(Ticket.batch_id == batch.id)).all()
    assert len(tickets) == 3
    assert {ticket.price_cents for ticket in tickets} == {2_900}

    admission = TicketService.admit(
        db, tickets[0].ticket_no, operator="frontdesk-test", request_id="admit-request-1"
    )
    repeated = TicketService.admit(
        db, tickets[0].ticket_no, operator="frontdesk-test", request_id="admit-request-1"
    )
    assert repeated.id == admission.id
    with pytest.raises(Exception, match="already"):
        TicketService.admit(db, tickets[0].ticket_no, operator="frontdesk-test", request_id="admit-request-2")


def test_weekend_ticket_price_is_4900_cents(db):
    from app.modules.tickets.service import TicketService

    make_member(db, "member-weekend")
    batch, order = TicketService.create_order(
        db, member_id="member-weekend", visit_date=date(2026, 11, 8), adult_count=1, child_count=0
    )
    assert order.amount_cents == batch.adult_unit_cents == 4_900


def test_ticket_order_requires_at_least_one_visitor(db):
    from app.core.errors import ApiError
    from app.modules.tickets.service import TicketService

    make_member(db, "member-empty-tickets")
    with pytest.raises(ApiError, match="visitor"):
        TicketService.create_order(
            db, member_id="member-empty-tickets", visit_date=date(2026, 11, 2), adult_count=0, child_count=0
        )
