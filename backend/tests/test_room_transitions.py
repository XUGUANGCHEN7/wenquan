from datetime import timedelta

import pytest
from sqlalchemy import select

from test_access import prepare, succeed_issue
from test_dining import activate_room
from test_wallet_identity import make_member


def test_cleaning_must_be_started_and_completed_before_room_use_is_closed(db):
    from app.core.errors import ApiError
    from app.modules.rooms.models import CleaningRecord
    from app.modules.rooms.service import RoomService

    make_member(db, "member-clean")
    booking, use = activate_room(db, "member-clean")
    RoomService.finish_use(db, use.id, operator="frontdesk-test", reason="time ended", request_id="finish-1")
    assert use.status == "PENDING_CLEANING"
    assert booking.status == "COMPLETED"
    with pytest.raises(ApiError, match="CLEANING"):
        RoomService.complete_cleaning(db, use.id, operator="frontdesk-test", request_id="clean-early")

    RoomService.start_cleaning(db, use.id, operator="frontdesk-test", request_id="clean-start")
    record = RoomService.complete_cleaning(db, use.id, operator="frontdesk-test", request_id="clean-done")
    assert use.status == "COMPLETED"
    assert record.completed_at is not None
    assert db.scalar(select(CleaningRecord).where(CleaningRecord.room_use_id == use.id)).id == record.id


def test_extension_waits_for_payment_and_device_write_before_extending_use(db):
    from app.modules.access.models import CardBinding
    from app.modules.access.service import AccessService
    from app.modules.devices.models import DeviceTask
    from app.modules.devices.service import DeviceService
    from app.modules.payments.service import PaymentService
    from app.modules.rooms.extension import RoomExtensionService

    _, group, order = prepare(db)
    payment = PaymentService.create_payment(db, order.order_no, "member-access", "WECHAT")
    PaymentService.confirm_mock(db, payment.payment_no, member_id="member-access", mock_enabled=True)
    _, issue_task = AccessService.issue_card(
        db, group.deposits[0].id, card_id="card-01", operator="frontdesk-test", request_id="extend-issue")
    succeed_issue(db, issue_task)
    binding = db.scalar(select(CardBinding).where(CardBinding.deposit_id == group.deposits[0].id))
    _, use = activate_room(db, "member-access")
    binding.room_use_id = use.id
    original_end = use.actual_end_at

    extension, extension_order = RoomExtensionService.create(
        db, room_use_id=use.id, binding_id=binding.id, operator="frontdesk-test")
    assert use.actual_end_at == original_end
    extension_payment = PaymentService.create_payment(db, extension_order.order_no, "member-access", "WECHAT")
    PaymentService.confirm_mock(db, extension_payment.payment_no, member_id="member-access", mock_enabled=True)
    task = db.scalar(select(DeviceTask).where(DeviceTask.task_type == "EXTEND_ROOM"))
    assert extension.status == "PAID"
    assert task.status == "PENDING"
    assert use.actual_end_at == original_end

    DeviceService.claim(db, task.id, worker_id="worker-test", reader_id="reader-test")
    DeviceService.start(db, task.id, worker_id="worker-test")
    DeviceService.report(db, task.id, worker_id="worker-test", result="SUCCEEDED")
    assert extension.status == "APPLIED"
    assert use.actual_end_at == original_end + timedelta(minutes=120)
    assert use.cleaning_end_at == use.actual_end_at + timedelta(minutes=30)
