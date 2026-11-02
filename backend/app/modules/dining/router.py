from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import OptionalAuth, Role
from app.core.database import get_db
from app.core.errors import ApiError
from app.modules.common import utcnow
from app.modules.dining.models import FoodOrder, MenuItem, Merchant, RoomQrCode
from app.modules.dining.service import DiningService
from app.modules.orders.router import assert_order_access, order_dict
from app.modules.payments.models import Order
from app.modules.rooms.models import Room, RoomUse

router = APIRouter(prefix="/api/v1/dining", tags=["dining"])


class CartLine(BaseModel):
    menu_item_id: str
    quantity: int = Field(ge=1, le=50)


class DiningOrderRequest(BaseModel):
    room_code: str = Field(min_length=2, max_length=80)
    items: list[CartLine] = Field(min_length=1)


def food_dict(food: FoodOrder, order: Order) -> dict:
    return {**order_dict(order), "food_order_id": food.id, "fulfillment_status": food.fulfillment_status,
            "delivered_at": food.delivered_at,
            "exception_reason": food.exception_reason, "room_id": food.room_id, "room_number": food.room.number,
            "items": [{"name_snapshot": item.name_snapshot, "unit_price_cents": item.unit_price_cents,
                       "quantity": item.quantity} for item in food.items]}


@router.get("/rooms")
def selectable_rooms(session: Session = Depends(get_db)):
    rows = session.execute(select(RoomQrCode, Room).join(
        Room, RoomQrCode.room_id == Room.id).where(RoomQrCode.active.is_(True)).order_by(Room.number)).all()
    now = utcnow()
    occupied = set(session.scalars(select(RoomUse.room_id).where(
        RoomUse.status == "ACTIVE", RoomUse.actual_start_at <= now, RoomUse.actual_end_at > now)).all())
    return [{"room_code": qr.code, "room_number": room.number, "can_order": room.id in occupied}
            for qr, room in rows]


@router.get("/merchants")
def merchants(session: Session = Depends(get_db)):
    records = session.scalars(select(Merchant).where(Merchant.active.is_(True)).order_by(Merchant.name, Merchant.id)).all()
    return [{"id": item.id, "name": item.name,
             "item_count": len(session.scalars(select(MenuItem.id).where(
                 MenuItem.merchant_id == item.id, MenuItem.available.is_(True))).all())}
            for item in records]


@router.get("/room-context/{room_code}")
def room_context(room_code: str, session: Session = Depends(get_db)):
    qr = session.scalar(select(RoomQrCode).where(RoomQrCode.code == room_code.upper()))
    if qr is None or not qr.active:
        raise ApiError(404, "ROOM_CODE_INVALID", "Room code is invalid or disabled")
    room = session.get(Room, qr.room_id)
    now = utcnow()
    use = session.scalar(select(RoomUse).where(RoomUse.room_id == room.id, RoomUse.status == "ACTIVE",
                                               RoomUse.actual_start_at <= now, RoomUse.actual_end_at > now))
    return {"room_code": qr.code, "room_number": room.number, "can_order": use is not None,
            "message": None if use else "当前房间暂不可接收新订单"}


@router.get("/menu")
def menu(merchant_id: str | None = None, session: Session = Depends(get_db)):
    query = select(MenuItem).join(Merchant, MenuItem.merchant_id == Merchant.id).where(Merchant.active.is_(True))
    if merchant_id:
        query = query.where(MenuItem.merchant_id == merchant_id)
    items = session.scalars(query.order_by(MenuItem.category, MenuItem.name, MenuItem.id)).all()
    return [{"id": item.id, "merchant_id": item.merchant_id, "name": item.name,
             "description": item.description, "category": item.category, "image_url": item.image_url,
             "price_cents": item.price_cents, "stock": item.stock, "available": item.available} for item in items]


@router.post("/orders", status_code=201)
def create_order(payload: DiningOrderRequest, auth: OptionalAuth, session: Session = Depends(get_db)):
    member_id = auth.member_id if auth and auth.role == Role.MEMBER else None
    food, order = DiningService.create_order(
        session, member_id=member_id, room_code=payload.room_code,
        items=[(line.menu_item_id, line.quantity) for line in payload.items])
    session.commit()
    return food_dict(food, order)


@router.get("/orders/{order_no}")
def order_detail(order_no: str, auth: OptionalAuth, session: Session = Depends(get_db)):
    order = session.scalar(select(Order).where(Order.order_no == order_no))
    if order is None or order.order_type != "FOOD":
        raise ApiError(404, "ORDER_NOT_FOUND", "Food order not found")
    assert_order_access(order, auth)
    food = session.get(FoodOrder, order.business_id)
    return food_dict(food, order)
