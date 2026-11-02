from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import select

from test_dining import activate_room
from test_wallet_identity import make_member

VISIT_DATE = date(2026, 11, 3)


def create_booking(db, member_id="member-rooms", slots=(0,), expected_hour=9):
    from app.modules.rooms.service import RoomService

    return RoomService.create_booking(
        db, member_id=member_id, visit_date=VISIT_DATE, slot_indices=list(slots),
        expected_arrival_at=datetime(2026, 11, 3, expected_hour, 0),
    )


def test_continuous_slots_use_same_room_interval_and_only_final_cleaning(db):
    make_member(db, "member-rooms")
    booking, order = create_booking(db, slots=(0, 1))
    assert order.amount_cents == 24_000
    assert booking.start_at == datetime(2026, 11, 3, 10, 0)
    assert booking.end_at == datetime(2026, 11, 3, 14, 30)
    assert booking.cleaning_end_at == datetime(2026, 11, 3, 15, 0)
    assert booking.expires_at - booking.created_at == timedelta(minutes=15)


def test_nonconsecutive_slots_are_rejected(db):
    from app.core.errors import ApiError

    make_member(db, "member-rooms")
    with pytest.raises(ApiError, match="consecutive"):
        create_booking(db, slots=(0, 2))


def test_individual_slot_availability_does_not_imply_continuous_availability(db):
    from app.modules.rooms.models import Room, RoomBlock
    from app.modules.rooms.service import RoomService

    make_member(db, "member-rooms")
    rooms = db.scalars(select(Room).order_by(Room.number)).all()
    day_start = datetime(2026, 11, 3, 0, 0)
    for room in rooms[:15]:
        db.add(RoomBlock(id=f"block-{room.id}", room_id=room.id, start_at=day_start,
                         end_at=day_start + timedelta(days=1), reason="test", kind="MANUAL"))
    db.add(RoomBlock(id="block-first", room_id=rooms[15].id, start_at=datetime(2026, 11, 3, 10),
                     end_at=datetime(2026, 11, 3, 12), reason="test", kind="MAINTENANCE"))
    db.add(RoomBlock(id="block-second", room_id=rooms[16].id, start_at=datetime(2026, 11, 3, 12, 30),
                     end_at=datetime(2026, 11, 3, 14, 30), reason="test", kind="MAINTENANCE"))
    db.flush()
    assert RoomService.availability(db, VISIT_DATE, [0]) == 1
    assert RoomService.availability(db, VISIT_DATE, [1]) == 1
    assert RoomService.availability(db, VISIT_DATE, [0, 1]) == 0


def test_expired_hold_cannot_be_confirmed_by_late_payment(db):
    from app.modules.payments.models import Order
    from app.modules.payments.service import PaymentService

    make_member(db, "member-rooms")
    booking, order = create_booking(db)
    payment = PaymentService.create_payment(db, order.order_no, "member-rooms", "WECHAT")
    from app.modules.common import utcnow

    booking.expires_at = utcnow() - timedelta(minutes=1)
    db.commit()

    confirmed = PaymentService.confirm_mock(
        db, payment.payment_no, member_id="member-rooms", mock_enabled=True
    )
    db.commit()
    assert confirmed.status == "SUCCESS"
    assert db.get(Order, order.id).status == "EXCEPTION"
    assert booking.status == "EXPIRED"


def test_paid_exception_can_refund_balance_and_overrun_room_is_not_resold(db):
    from app.core.errors import ApiError
    from app.modules.common import utcnow
    from app.modules.payments.models import Order
    from app.modules.payments.refunds import RefundService
    from app.modules.payments.service import PaymentService
    from app.modules.rooms.models import Room, RoomBlock, RoomUse
    from app.modules.rooms.service import RoomService
    from app.modules.wallet.service import WalletService

    make_member(db, "member-refund-room")
    WalletService.credit(db, "member-refund-room", 24_000, 0, "room-refund-fund")
    booking, order = create_booking(db, member_id="member-refund-room", slots=(0,))
    booking.expires_at = utcnow() - timedelta(minutes=1)
    db.flush()
    payment = PaymentService.create_payment(db, order.order_no, "member-refund-room", "BALANCE")
    assert payment.status == "SUCCESS"
    assert db.get(Order, order.id).status == "EXCEPTION"
    refund = RefundService.request_for_order(db, order.order_no, reason="Paid hold expired")
    assert refund.status == "SUCCESS"
    assert WalletService.available_cents(db, "member-refund-room") == 24_000
    assert booking.status == "CANCELLED"

    _, active = activate_room(db, "member-refund-room")
    rooms = db.scalars(select(Room).where(Room.id != active.room_id)).all()
    for room in rooms:
        db.add(RoomBlock(id=f"overrun-block-{room.id}", room_id=room.id,
                         start_at=datetime.combine(utcnow().date(), datetime.min.time()),
                         end_at=datetime.combine(utcnow().date(), datetime.max.time()),
                         reason="test only active room", kind="MANUAL"))
    db.flush()
    assert RoomService.availability(db, utcnow().date(), [0]) == 0


def test_delayed_assignment_refuses_to_overlap_next_sold_booking(db):
    from app.modules.rooms.models import Room, RoomBlock, RoomUse
    from app.modules.rooms.service import RoomService

    make_member(db, "member-rooms")
    rooms = db.scalars(select(Room).order_by(Room.number)).all()
    for room in rooms[1:]:
        db.add(RoomBlock(id=f"full-{room.id}", room_id=room.id,
                         start_at=datetime(2026, 11, 3), end_at=datetime(2026, 11, 4),
                         reason="test", kind="MANUAL"))
    db.flush()
    first, first_order = create_booking(db, slots=(0,))
    second, second_order = create_booking(db, slots=(1,))
    first.status = second.status = "CONFIRMED"
    assert first.internal_room_id == second.internal_room_id

    result = RoomService.assign_booking(
        db, first.id, actual_start=datetime(2026, 11, 3, 11, 30),
        operator="frontdesk-test", reason="late arrival", request_id="assign-late-1",
    )
    assert result is None
    assert first.status == "CONFLICT"
    assert db.scalars(select(RoomUse).where(RoomUse.booking_id == first.id)).all() == []
