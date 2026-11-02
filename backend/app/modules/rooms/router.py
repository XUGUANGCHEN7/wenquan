from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, Role, require_roles
from app.core.database import get_db
from app.core.errors import ApiError
from app.modules.catalog.models import BusinessConfig
from app.modules.orders.router import order_dict
from app.modules.payments.models import Order
from app.modules.rooms.models import PrivateBooking, RoomUse
from app.modules.rooms.service import SLOT_TIMES, RoomService

router = APIRouter(prefix="/api/v1/rooms", tags=["rooms"])
MemberAuth = Annotated[AuthContext, Depends(require_roles(Role.MEMBER))]


class BookingRequest(BaseModel):
    visit_date: date
    slot_indices: list[int] = Field(min_length=1, max_length=5)
    expected_arrival_at: datetime


def booking_dict(booking: PrivateBooking, order: Order, room_use: RoomUse | None = None) -> dict:
    return {**order_dict(order), "booking_id": booking.id, "visit_date": booking.visit_date,
            "slot_indices": booking.slot_indices, "expected_arrival_at": booking.expected_arrival_at,
            "start_at": booking.start_at, "end_at": booking.end_at, "cleaning_end_at": booking.cleaning_end_at,
            "expires_at": booking.expires_at, "booking_status": booking.status,
            "room_number": room_use.room.number if room_use else None}


@router.get("/slots")
def slots(visit_date: date, session: Session = Depends(get_db)):
    config = session.get(BusinessConfig, "private_slot_price_cents")
    return {"visit_date": visit_date, "unit_price_cents": config.value,
            "slots": [{"slot_index": index, "start": values[0].strftime("%H:%M"),
                       "end": values[1].strftime("%H:%M"),
                       "available": RoomService.availability(session, visit_date, [index])}
                      for index, values in enumerate(SLOT_TIMES)]}


@router.get("/availability")
def availability(visit_date: date, slots: str = Query(...), session: Session = Depends(get_db)):
    try:
        indices = [int(value) for value in slots.split(",")]
    except ValueError as exc:
        raise ApiError(422, "SLOT_INVALID", "Slots must be comma-separated integers") from exc
    count = RoomService.availability(session, visit_date, indices)
    config = session.get(BusinessConfig, "private_slot_price_cents")
    return {"available": count, "amount_cents": count > 0 and config.value * len(indices) or 0,
            "slot_indices": indices}


@router.post("/bookings", status_code=201)
def create_booking(payload: BookingRequest, auth: MemberAuth, session: Session = Depends(get_db)):
    booking, order = RoomService.create_booking(session, member_id=auth.member_id, **payload.model_dump())
    session.commit()
    return booking_dict(booking, order)


@router.get("/bookings/{booking_id}")
def booking_detail(booking_id: str, auth: MemberAuth, session: Session = Depends(get_db)):
    booking = session.get(PrivateBooking, booking_id)
    if booking is None or booking.member_id != auth.member_id:
        raise ApiError(404, "BOOKING_NOT_FOUND", "Booking not found")
    order = session.get(Order, booking.order_id)
    use = session.scalar(select(RoomUse).where(RoomUse.booking_id == booking.id))
    return booking_dict(booking, order, use)
