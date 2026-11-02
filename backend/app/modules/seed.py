from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catalog.models import BusinessConfig, RechargeActivity
from app.modules.identity.models import Member
from app.modules.identity.service import IdentityService
from app.modules.wallet.models import MemberAccount


def seed_development_data(session: Session) -> None:
    member = session.get(Member, "member-demo")
    if member is None:
        member = Member(id="member-demo", nickname="温泉旅人")
        session.add(member)
        session.flush()
    if session.get(MemberAccount, "member-demo") is None:
        session.add(MemberAccount(member_id="member-demo"))
    IdentityService.bind(session, appid="dev-ticket-app", openid="dev-ticket-openid", member_id=member.id, verified=True)
    IdentityService.bind(session, appid="dev-dining-app", openid="dev-dining-openid", member_id=member.id, verified=True)

    if session.scalar(select(RechargeActivity.id).limit(1)) is None:
        session.add_all([
            RechargeActivity(id="recharge-200", name="轻享礼", principal_cents=20_000, gift_cents=2_000),
            RechargeActivity(id="recharge-500", name="舒享礼", principal_cents=50_000, gift_cents=8_000),
            RechargeActivity(id="recharge-1000", name="尊享礼", principal_cents=100_000, gift_cents=20_000),
        ])
    defaults = {
        "private_slot_price_cents": (12_000, "Development private-room price per slot"),
        "deposit_amount_cents": (10_000, "Development-only deposit; business amount is pending confirmation"),
        "extension_price_cents": (12_000, "Development extension price per configured duration"),
        "extension_minutes": (120, "Development extension duration in minutes"),
    }
    for key, (value, description) in defaults.items():
        if session.get(BusinessConfig, key) is None:
            session.add(BusinessConfig(key=key, value=value, description=description))
    from app.modules.access.models import Card, Locker
    from app.modules.common import utcnow
    from app.modules.dining.models import MenuItem, Merchant, RoomQrCode
    from app.modules.payments.models import Order
    from app.modules.rooms.models import PrivateBooking, Room, RoomUse

    if session.scalar(select(Room.id).limit(1)) is None:
        session.add_all([Room(id=f"room-{number:02d}", number=f"{number:02d}") for number in range(1, 18)])
        session.flush()
    for number in range(1, 31):
        if session.get(Locker, f"locker-{number:03d}") is None:
            session.add(Locker(id=f"locker-{number:03d}", number=f"{number:03d}"))
    for number in range(1, 41):
        if session.get(Card, f"card-{number:02d}") is None:
            session.add(Card(id=f"card-{number:02d}", physical_uid=f"DEV-PHYSICAL-{number:02d}",
                             logical_card_id=f"DEV-LOGICAL-{number:02d}"))
    for number in range(1, 18):
        code = f"ROOM-{number:02d}"
        if session.scalar(select(RoomQrCode).where(RoomQrCode.code == code)) is None:
            session.add(RoomQrCode(id=f"qr-{number:02d}", code=code, room_id=f"room-{number:02d}"))
    if session.get(Merchant, "merchant-spring") is None:
        session.add(Merchant(id="merchant-spring", name="山泉食坊"))
        session.add_all([
            MenuItem(id="menu-noodles", merchant_id="merchant-spring", name="暖汤荞麦面",
                     description="山泉高汤 · 时蔬 · 溏心蛋", category="主食套餐", price_cents=3_800, stock=100),
            MenuItem(id="menu-beef-rice", merchant_id="merchant-spring", name="温泉蛋牛肉饭",
                     description="谷饲牛肉 · 温泉蛋 · 米饭", category="主食套餐", price_cents=4_600, stock=100),
            MenuItem(id="menu-tea", merchant_id="merchant-spring", name="桂花乌龙",
                     description="现泡乌龙 · 桂花蜜", category="饮品", price_cents=1_600, stock=100),
        ])

    if session.get(RoomUse, "room-use-demo") is None:
        now = utcnow()
        from datetime import timedelta

        order = Order(id="order-demo-room-use", order_no="DEV-ROOM-USE", member_id=member.id,
                      order_type="PRIVATE", business_id="booking-demo-room-use", amount_cents=12_000,
                      status="PAID", payment_method="WECHAT", paid_at=now)
        booking = PrivateBooking(
            id="booking-demo-room-use", order_id=order.id, member_id=member.id, internal_room_id="room-01",
            visit_date=now.date(), slot_indices=[0], slot_count=1, unit_price_cents=12_000,
            start_at=now - timedelta(minutes=15), end_at=now + timedelta(minutes=105),
            cleaning_end_at=now + timedelta(minutes=135), expected_arrival_at=now - timedelta(minutes=15),
            status="IN_USE", created_at=now - timedelta(minutes=20), expires_at=now, confirmed_at=now,
        )
        use = RoomUse(id="room-use-demo", booking_id=booking.id, room_id="room-01", member_id=member.id,
                      actual_start_at=now - timedelta(minutes=15), actual_end_at=now + timedelta(minutes=105),
                      cleaning_end_at=now + timedelta(minutes=135))
        session.add_all([order, booking, use])
    session.commit()
