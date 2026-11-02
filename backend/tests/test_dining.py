from datetime import timedelta

import pytest
from sqlalchemy import select

from test_wallet_identity import make_member as make_member_base


def make_member(db):
    return make_member_base(db, "member-dining")


def activate_room(db, member_id="member-dining", slot=0):
    from app.modules.common import utcnow
    from app.modules.rooms.service import RoomService

    now = utcnow()
    booking, _ = RoomService.create_booking(
        db, member_id=member_id, visit_date=now.date(), slot_indices=[slot], expected_arrival_at=now
    )
    booking.status = "CONFIRMED"
    use = RoomService.assign_booking(
        db, booking.id, actual_start=now - timedelta(minutes=10), operator="test",
        reason="test active room", request_id=f"activate-{booking.id}",
    )
    return booking, use


def test_visitor_payment_queues_once_with_server_price_snapshot(db):
    from app.modules.dining.models import FoodOrder, MenuItem
    from app.modules.dining.service import DiningService
    from app.modules.payments.service import PaymentService

    make_member(db)
    _, use = activate_room(db)
    food, order = DiningService.create_order(
        db, member_id=None, room_code=f"ROOM-{use.room.number}", items=[("menu-noodles", 2)]
    )
    assert order.member_id is None
    assert order.amount_cents == 7_600
    assert food.room_use_id == use.id
    payment = PaymentService.create_payment(db, order.order_no, None, "WECHAT")
    first = PaymentService.confirm_mock(db, payment.payment_no, member_id=None, mock_enabled=True)
    db.commit()
    assert first.status == "SUCCESS"
    assert food.fulfillment_status == "QUEUED"
    assert db.get(MenuItem, "menu-noodles").stock == 98

    PaymentService.confirm_mock(db, payment.payment_no, member_id=None, mock_enabled=True)
    assert db.get(MenuItem, "menu-noodles").stock == 98
    assert db.get(FoodOrder, food.id).queued_at == food.queued_at

    from app.core.errors import ApiError
    from app.modules.payments.refunds import RefundService

    with pytest.raises(ApiError, match="manual policy"):
        RefundService.request_for_order(db, order.order_no, reason="food policy pending")


def test_old_room_use_becomes_paid_exception_after_guest_change(db):
    from app.modules.dining.service import DiningService
    from app.modules.payments.models import Order
    from app.modules.payments.service import PaymentService
    from app.modules.rooms.models import Room, RoomBlock
    from app.modules.rooms.service import RoomService

    make_member(db)
    first_booking, old_use = activate_room(db)
    food, order = DiningService.create_order(
        db, member_id=None, room_code=f"ROOM-{old_use.room.number}", items=[("menu-noodles", 1)]
    )
    payment = PaymentService.create_payment(db, order.order_no, None, "WECHAT")
    old_use.status = "COMPLETED"
    first_booking.status = "COMPLETED"

    rooms = db.scalars(select(Room).where(Room.id != old_use.room_id)).all()
    for room in rooms:
        db.add(RoomBlock(id=f"dining-block-{room.id}", room_id=room.id,
                         start_at=old_use.actual_start_at - timedelta(days=1),
                         end_at=old_use.cleaning_end_at + timedelta(days=1), reason="test", kind="MANUAL"))
    db.flush()
    second_booking, new_use = activate_room(db, slot=1)
    assert new_use.room_id == old_use.room_id
    assert new_use.id != food.room_use_id

    PaymentService.confirm_mock(db, payment.payment_no, member_id=None, mock_enabled=True)
    db.commit()
    assert food.fulfillment_status == "EXCEPTION"
    assert db.get(Order, order.id).status == "EXCEPTION"
    assert food.queued_at is None


def test_inactive_merchant_cannot_receive_new_food_order(db):
    from app.core.errors import ApiError
    from app.modules.dining.models import Merchant
    from app.modules.dining.service import DiningService

    make_member(db)
    _, use = activate_room(db)
    db.get(Merchant, "merchant-spring").active = False
    db.flush()
    with pytest.raises(ApiError, match="Merchant is not accepting orders"):
        DiningService.create_order(
            db, member_id=None, room_code=f"ROOM-{use.room.number}", items=[("menu-noodles", 1)]
        )


def test_empty_or_inactive_room_cannot_create_food_order(db):
    from app.core.errors import ApiError
    from app.modules.dining.service import DiningService

    make_member(db)
    _, use = activate_room(db)
    use.status = "CLEANING"
    with pytest.raises(ApiError, match="not available"):
        DiningService.create_order(
            db, member_id=None, room_code=f"ROOM-{use.room.number}", items=[("menu-noodles", 1)]
        )
