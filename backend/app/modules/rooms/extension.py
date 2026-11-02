from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.modules.access.models import CardBinding
from app.modules.catalog.models import BusinessConfig
from app.modules.common import new_business_no, new_id, utcnow
from app.modules.devices.models import DeviceTask
from app.modules.devices.service import DeviceService
from app.modules.payments.models import Order
from sqlalchemy import select

from app.modules.rooms.models import Room, RoomBlock, RoomExtension, RoomUse
from app.modules.rooms.service import RoomService


class RoomExtensionService:
    @staticmethod
    def _config(session: Session) -> tuple[int, int]:
        minutes = session.get(BusinessConfig, "extension_minutes")
        price = session.get(BusinessConfig, "extension_price_cents")
        if minutes is None or price is None or minutes.value <= 0 or price.value < 0:
            raise ApiError(409, "EXTENSION_NOT_CONFIGURED", "Extension duration and price must be configured")
        return minutes.value, price.value

    @staticmethod
    def _interval_available(session: Session, use: RoomUse, minutes: int) -> bool:
        new_end = use.actual_end_at + timedelta(minutes=minutes)
        return RoomService._available(
            session, use.room_id, use.actual_end_at, new_end + timedelta(minutes=30),
            now=utcnow(), exclude_booking_id=use.booking_id, exclude_use_id=use.id,
        )

    @staticmethod
    def create(session: Session, *, room_use_id: str, binding_id: str,
               operator: str) -> tuple[RoomExtension, Order]:
        use = session.get(RoomUse, room_use_id, with_for_update=True)
        binding = session.get(CardBinding, binding_id, with_for_update=True)
        if use is None or use.status != "ACTIVE" or binding is None or binding.status != "BOUND":
            raise ApiError(409, "EXTENSION_NOT_ALLOWED", "An active use and bound wristband are required")
        if binding.room_use_id != use.id:
            raise ApiError(409, "WRISTBAND_ROOM_MISMATCH", "The wristband is not bound to this room use")
        session.scalar(select(Room).where(Room.id == use.room_id).with_for_update())
        minutes, price = RoomExtensionService._config(session)
        if not RoomExtensionService._interval_available(session, use, minutes):
            raise ApiError(409, "EXTENSION_CONFLICT", "The extended use and cleaning interval is unavailable")
        order = Order(id=new_id("ord"), order_no=new_business_no("EX"), member_id=use.member_id,
                      order_type="EXTENSION", amount_cents=price)
        extension = RoomExtension(id=new_id("ext"), room_use_id=use.id, order_id=order.id,
                                  binding_id=binding.id, minutes=minutes, amount_cents=price)
        order.business_id = extension.id
        session.add_all([order, extension])
        session.flush()
        return extension, order

    @staticmethod
    def confirm_paid(session: Session, order: Order) -> str:
        extension = session.get(RoomExtension, order.business_id, with_for_update=True)
        if extension is None:
            raise ApiError(409, "ORDER_INVALID", "Room extension is missing")
        if extension.status in ("PAID", "APPLIED"):
            return "PAID"
        if extension.status != "PENDING":
            return "EXCEPTION"
        use = session.get(RoomUse, extension.room_use_id, with_for_update=True)
        session.scalar(select(Room).where(Room.id == use.room_id).with_for_update())
        if use.status != "ACTIVE" or not RoomExtensionService._interval_available(session, use, extension.minutes):
            extension.status = "EXCEPTION"
            session.flush()
            return "EXCEPTION"
        extension.status = "PAID"
        new_end = use.actual_end_at + timedelta(minutes=extension.minutes)
        session.add(RoomBlock(id=f"extension-hold-{extension.id}", room_id=use.room_id,
                              start_at=use.actual_end_at, end_at=new_end + timedelta(minutes=30),
                              reason="Paid extension authorization hold", kind="EXTENSION_HOLD"))
        binding = session.get(CardBinding, extension.binding_id)
        DeviceService.create_task(
            session, task_type="EXTEND_ROOM", idempotency_key=f"extend-{extension.id}", operator="frontdesk",
            binding_id=binding.id, card_id=binding.card_id, locker_id=binding.locker_id, room_id=use.room_id,
            payload={"extension_id": extension.id, "minutes": extension.minutes})
        session.flush()
        return "PAID"

    @staticmethod
    def apply_device_result(session: Session, task: DeviceTask, result: str) -> None:
        extension = session.get(RoomExtension, task.payload.get("extension_id"), with_for_update=True)
        if extension is None or extension.status != "PAID" or result != "SUCCEEDED":
            return
        use = session.get(RoomUse, extension.room_use_id, with_for_update=True)
        use.actual_end_at += timedelta(minutes=extension.minutes)
        use.cleaning_end_at += timedelta(minutes=extension.minutes)
        extension.status = "APPLIED"
        extension.applied_at = utcnow()
        session.flush()
