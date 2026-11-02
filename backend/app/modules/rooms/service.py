from datetime import date, datetime, time, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.modules.audit import audit
from app.modules.catalog.models import BusinessConfig
from app.modules.common import new_business_no, new_id, utcnow
from app.modules.payments.models import Order
from app.modules.rooms.models import CleaningRecord, PrivateBooking, Room, RoomBlock, RoomUse

SLOT_TIMES = (
    (time(10, 0), time(12, 0)), (time(12, 30), time(14, 30)),
    (time(15, 0), time(17, 0)), (time(17, 30), time(19, 30)),
    (time(20, 0), time(22, 0)),
)
ACTIVE_BOOKING_STATES = ("CONFIRMED", "IN_USE")


class RoomService:
    @staticmethod
    def interval(visit_date: date, slot_indices: list[int]) -> tuple[datetime, datetime, datetime]:
        if not slot_indices or any(not isinstance(index, int) or index < 0 or index >= len(SLOT_TIMES) for index in slot_indices):
            raise ApiError(422, "SLOT_INVALID", "At least one valid slot is required")
        if slot_indices != sorted(set(slot_indices)) or any(
            later != earlier + 1 for earlier, later in zip(slot_indices, slot_indices[1:])
        ):
            raise ApiError(422, "SLOTS_NOT_CONSECUTIVE", "Private-room slots must be consecutive")
        start = datetime.combine(visit_date, SLOT_TIMES[slot_indices[0]][0])
        end = datetime.combine(visit_date, SLOT_TIMES[slot_indices[-1]][1])
        return start, end, end + timedelta(minutes=30)

    @staticmethod
    def _available(session: Session, room_id: str, start: datetime, cleaning_end: datetime,
                   *, now: datetime, exclude_booking_id: str | None = None,
                   exclude_use_id: str | None = None) -> bool:
        block = select(RoomBlock.id).where(
            RoomBlock.room_id == room_id, RoomBlock.start_at < cleaning_end, RoomBlock.end_at > start)
        if session.scalar(block.limit(1)):
            return False
        booking = select(PrivateBooking.id).where(
            PrivateBooking.internal_room_id == room_id,
            PrivateBooking.start_at < cleaning_end, PrivateBooking.cleaning_end_at > start,
            or_(and_(PrivateBooking.status == "HELD", PrivateBooking.expires_at > now),
                PrivateBooking.status.in_(ACTIVE_BOOKING_STATES)))
        if exclude_booking_id:
            booking = booking.where(PrivateBooking.id != exclude_booking_id)
        if session.scalar(booking.limit(1)):
            return False
        live_use = select(RoomUse.id).where(
            RoomUse.room_id == room_id,
            RoomUse.status.in_(["ACTIVE", "PENDING_CLEANING", "CLEANING"]),
            RoomUse.cleaning_end_at + timedelta(hours=6) > start,
        )
        if exclude_use_id:
            live_use = live_use.where(RoomUse.id != exclude_use_id)
        if session.scalar(live_use.limit(1)):
            return False
        use = select(RoomUse.id).where(
            RoomUse.room_id == room_id, RoomUse.actual_start_at < cleaning_end,
            RoomUse.cleaning_end_at > start, RoomUse.status != "COMPLETED")
        if exclude_use_id:
            use = use.where(RoomUse.id != exclude_use_id)
        return session.scalar(use.limit(1)) is None

    @staticmethod
    def _candidates(session: Session, start: datetime, cleaning_end: datetime, *, lock: bool,
                    exclude_booking_id: str | None = None) -> list[Room]:
        statement = select(Room).where(Room.active.is_(True)).order_by(Room.number)
        if lock:
            statement = statement.with_for_update()
        rooms = session.scalars(statement).all()
        now = utcnow()
        return [room for room in rooms if RoomService._available(
            session, room.id, start, cleaning_end, now=now, exclude_booking_id=exclude_booking_id)]

    @staticmethod
    def availability(session: Session, visit_date: date, slot_indices: list[int]) -> int:
        start, _, cleaning_end = RoomService.interval(visit_date, slot_indices)
        return len(RoomService._candidates(session, start, cleaning_end, lock=False))

    @staticmethod
    def create_booking(session: Session, *, member_id: str, visit_date: date,
                       slot_indices: list[int], expected_arrival_at: datetime) -> tuple[PrivateBooking, Order]:
        start, end, cleaning_end = RoomService.interval(visit_date, slot_indices)
        candidates = RoomService._candidates(session, start, cleaning_end, lock=True)
        if not candidates:
            raise ApiError(409, "NO_ROOM_AVAILABLE", "No room can cover the complete usage and cleaning interval")
        config = session.get(BusinessConfig, "private_slot_price_cents")
        if config is None:
            raise ApiError(409, "PRICE_NOT_CONFIGURED", "Private-room price is not configured")
        now = utcnow()
        order = Order(id=new_id("ord"), order_no=new_business_no("PR"), member_id=member_id,
                      order_type="PRIVATE", amount_cents=config.value * len(slot_indices))
        booking = PrivateBooking(
            id=new_id("bkg"), order_id=order.id, member_id=member_id,
            internal_room_id=candidates[0].id, visit_date=visit_date,
            slot_indices=slot_indices, slot_count=len(slot_indices), unit_price_cents=config.value,
            start_at=start, end_at=end, cleaning_end_at=cleaning_end,
            expected_arrival_at=expected_arrival_at, created_at=now, expires_at=now + timedelta(minutes=15))
        order.business_id = booking.id
        session.add_all([order, booking])
        session.flush()
        return booking, order

    @staticmethod
    def confirm_paid(session: Session, order: Order) -> str:
        booking = session.get(PrivateBooking, order.business_id, with_for_update=True)
        if booking is None:
            raise ApiError(409, "ORDER_INVALID", "Private booking is missing")
        if booking.status in (*ACTIVE_BOOKING_STATES, "COMPLETED"):
            return "PAID"
        if booking.status != "HELD" or booking.expires_at <= utcnow():
            booking.status = "EXPIRED"
            session.flush()
            return "EXCEPTION"
        booking.status = "CONFIRMED"
        booking.confirmed_at = utcnow()
        session.flush()
        return "PAID"

    @staticmethod
    def assign_booking(session: Session, booking_id: str, *, actual_start: datetime,
                       operator: str, reason: str, request_id: str) -> RoomUse | None:
        booking = session.get(PrivateBooking, booking_id, with_for_update=True)
        if booking is None or booking.status != "CONFIRMED":
            raise ApiError(409, "BOOKING_NOT_ASSIGNABLE", "Only a confirmed booking can be assigned")
        actual_end = actual_start + timedelta(minutes=120 * booking.slot_count)
        cleaning_end = actual_end + timedelta(minutes=30)
        candidates = RoomService._candidates(
            session, actual_start, cleaning_end, lock=True, exclude_booking_id=booking.id)
        if not candidates:
            booking.status = "CONFLICT"
            audit(session, actor=operator, action="ASSIGNMENT_CONFLICT", entity_type="private_booking",
                  entity_id=booking.id, before="CONFIRMED", after="CONFLICT", reason=reason, request_id=request_id)
            session.flush()
            return None
        room = candidates[0]
        before = booking.status
        booking.internal_room_id = room.id
        booking.status = "IN_USE"
        room_use = RoomUse(id=new_id("use"), booking_id=booking.id, room_id=room.id, member_id=booking.member_id,
                           actual_start_at=actual_start, actual_end_at=actual_end, cleaning_end_at=cleaning_end)
        session.add(room_use)
        audit(session, actor=operator, action="ROOM_ASSIGNED", entity_type="private_booking",
              entity_id=booking.id, before=before, after="IN_USE", reason=reason, request_id=request_id)
        session.flush()
        return room_use

    @staticmethod
    def finish_use(session: Session, room_use_id: str, *, operator: str,
                   reason: str, request_id: str) -> RoomUse:
        use = session.get(RoomUse, room_use_id, with_for_update=True)
        if use is None or use.status != "ACTIVE":
            raise ApiError(409, "ROOM_USE_NOT_FINISHABLE", "Only an active room use can be finished")
        use.status = "PENDING_CLEANING"
        booking = session.get(PrivateBooking, use.booking_id)
        booking.status = "COMPLETED"
        audit(session, actor=operator, action="ROOM_USE_FINISHED", entity_type="room_use",
              entity_id=use.id, before="ACTIVE", after=use.status, reason=reason, request_id=request_id)
        session.flush()
        return use

    @staticmethod
    def start_cleaning(session: Session, room_use_id: str, *, operator: str,
                       request_id: str) -> CleaningRecord:
        use = session.get(RoomUse, room_use_id, with_for_update=True)
        if use is None or use.status != "PENDING_CLEANING":
            raise ApiError(409, "CLEANING_NOT_STARTABLE", "Room use must be pending cleaning")
        record = session.scalar(select(CleaningRecord).where(CleaningRecord.room_use_id == use.id))
        if record is None:
            record = CleaningRecord(id=new_id("cln"), room_use_id=use.id, room_id=use.room_id, operator=operator)
            session.add(record)
        record.started_at = utcnow()
        record.operator = operator
        use.status = "CLEANING"
        audit(session, actor=operator, action="ROOM_CLEANING_STARTED", entity_type="room_use",
              entity_id=use.id, before="PENDING_CLEANING", after="CLEANING", reason="Cleaning started",
              request_id=request_id)
        session.flush()
        return record

    @staticmethod
    def complete_cleaning(session: Session, room_use_id: str, *, operator: str,
                          request_id: str) -> CleaningRecord:
        use = session.get(RoomUse, room_use_id, with_for_update=True)
        if use is None or use.status != "CLEANING":
            raise ApiError(409, "CLEANING_NOT_COMPLETABLE", "CLEANING must be started before completion")
        record = session.scalar(select(CleaningRecord).where(CleaningRecord.room_use_id == use.id))
        record.completed_at = utcnow()
        record.operator = operator
        use.status = "COMPLETED"
        audit(session, actor=operator, action="ROOM_CLEANING_COMPLETED", entity_type="room_use",
              entity_id=use.id, before="CLEANING", after="COMPLETED", reason="Cleaning completed",
              request_id=request_id)
        session.flush()
        return record
