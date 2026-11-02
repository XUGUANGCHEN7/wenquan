import pytest
from sqlalchemy import func, select

from test_wallet_identity import make_member


def prepare(db, count=1):
    from app.modules.access.service import AccessService
    from app.modules.payments.service import PaymentService
    from app.modules.tickets.models import Ticket, TicketBatch
    from app.modules.tickets.service import TicketService
    from app.modules.wallet.service import WalletService

    make_member(db, "member-access")
    WalletService.credit(db, "member-access", 100_000, 0, "access-funds")
    _, ticket_order = TicketService.create_order(
        db, member_id="member-access", visit_date=__import__("datetime").date(2026, 11, 2),
        adult_count=count, child_count=0,
    )
    PaymentService.create_payment(db, ticket_order.order_no, "member-access", "BALANCE")
    batch = db.get(TicketBatch, ticket_order.business_id)
    tickets = db.scalars(select(Ticket).where(Ticket.batch_id == batch.id).order_by(Ticket.visitor_index)).all()
    group, order = AccessService.create_deposit_order(
        db, payer_member_id="member-access", ticket_nos=[ticket.ticket_no for ticket in tickets]
    )
    return tickets, group, order


def succeed_issue(db, task):
    from app.modules.devices.service import DeviceService

    DeviceService.claim(db, task.id, worker_id="worker-test", reader_id="reader-test")
    DeviceService.start(db, task.id, worker_id="worker-test")
    return DeviceService.report(db, task.id, worker_id="worker-test", result="SUCCEEDED")


def test_issue_requires_paid_deposit_and_reuses_locker_reservation(db):
    from app.core.errors import ApiError
    from app.modules.access.models import CardBinding, Locker
    from app.modules.access.service import AccessService
    from app.modules.payments.service import PaymentService

    _, group, order = prepare(db)
    with pytest.raises(ApiError, match="WeChat"):
        PaymentService.create_payment(db, order.order_no, "member-access", "BALANCE")
    with pytest.raises(ApiError, match="paid"):
        AccessService.issue_card(db, group.deposits[0].id, card_id="card-01",
                                 operator="frontdesk-test", request_id="issue-unpaid")

    payment = PaymentService.create_payment(db, order.order_no, "member-access", "WECHAT")
    PaymentService.confirm_mock(db, payment.payment_no, member_id="member-access", mock_enabled=True)
    binding, task = AccessService.issue_card(db, group.deposits[0].id, card_id="card-01",
                                             operator="frontdesk-test", request_id="issue-paid")
    repeated_binding, repeated_task = AccessService.issue_card(
        db, group.deposits[0].id, card_id="card-02", operator="frontdesk-test", request_id="issue-repeat")
    assert repeated_binding.id == binding.id
    assert repeated_task.id == task.id
    assert binding.status == "ISSUING"
    assert db.get(Locker, binding.locker_id).status == "RESERVED"
    assert db.scalar(select(func.count(CardBinding.id))) == 1

    succeed_issue(db, task)
    assert binding.status == "BOUND"
    assert db.get(Locker, binding.locker_id).status == "BOUND"
    from app.modules.tickets.models import Ticket

    assert db.get(Ticket, group.deposits[0].ticket_id).status == "UNUSED"


def test_return_uses_stable_independent_refund_and_clear_failure_does_not_block(db):
    from app.modules.access.models import Card
    from app.modules.access.service import AccessService
    from app.modules.devices.service import DeviceService
    from app.modules.payments.models import Refund
    from app.modules.payments.service import PaymentService

    _, group, order = prepare(db, count=2)
    payment = PaymentService.create_payment(db, order.order_no, "member-access", "WECHAT")
    PaymentService.confirm_mock(db, payment.payment_no, member_id="member-access", mock_enabled=True)
    tasks = []
    for index, deposit in enumerate(group.deposits, start=1):
        _, task = AccessService.issue_card(db, deposit.id, card_id=f"card-{index:02d}",
                                           operator="frontdesk-test", request_id=f"issue-{index}")
        succeed_issue(db, task)
        tasks.append(task)

    from app.modules.access.models import CardBinding

    first_binding = db.scalar(select(CardBinding).where(CardBinding.deposit_id == group.deposits[0].id))
    _, refund, clear_task = AccessService.return_card(
        db, first_binding.id, operator="frontdesk-test", reason="physical card returned", request_id="return-1")
    _, repeated, _ = AccessService.return_card(
        db, first_binding.id, operator="frontdesk-test", reason="physical card returned", request_id="return-1")
    assert repeated.id == refund.id
    assert refund.amount_cents == group.deposits[0].amount_cents
    assert db.scalar(select(func.count(Refund.id))) == 1
    assert group.deposits[1].status == "PAID"

    DeviceService.claim(db, clear_task.id, worker_id="worker-test", reader_id="reader-test")
    DeviceService.start(db, clear_task.id, worker_id="worker-test")
    DeviceService.report(db, clear_task.id, worker_id="worker-test", result="FAILED", raw_error="mock clear failure")
    assert db.get(Card, first_binding.card_id).status == "QUARANTINED"
    assert refund.status == "ACCEPTED"
    assert group.deposits[0].status == "REFUND_PENDING"
