from sqlalchemy import select

from test_access import prepare


def test_unknown_device_result_is_not_released_or_polled_as_new(db):
    from app.modules.access.models import CardBinding, Locker
    from app.modules.access.service import AccessService
    from app.modules.devices.models import DeviceTask
    from app.modules.devices.service import DeviceService
    from app.modules.payments.service import PaymentService

    _, group, order = prepare(db)
    payment = PaymentService.create_payment(db, order.order_no, "member-access", "WECHAT")
    PaymentService.confirm_mock(db, payment.payment_no, member_id="member-access", mock_enabled=True)
    binding, task = AccessService.issue_card(
        db, group.deposits[0].id, card_id="card-01", operator="frontdesk-test", request_id="issue-unknown")

    DeviceService.claim(db, task.id, worker_id="worker-offline", reader_id="reader-test")
    DeviceService.start(db, task.id, worker_id="worker-offline")
    DeviceService.report(db, task.id, worker_id="worker-offline", result="UNKNOWN", raw_error="connection lost")
    assert task.status == "UNKNOWN"
    assert binding.status == "ISSUING"
    assert db.get(Locker, binding.locker_id).status == "RESERVED"
    assert DeviceService.poll(db, worker_id="worker-offline", reader_id="reader-test") is None

    duplicate = DeviceService.report(db, task.id, worker_id="worker-offline", result="UNKNOWN", raw_error="connection lost")
    assert duplicate.id == task.id
    assert len(db.scalars(select(DeviceTask)).all()) == 1
