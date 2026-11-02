from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.modules.common import new_business_no, new_id, utcnow
from app.modules.dining.models import FoodOrder, FoodOrderItem, MenuItem, Merchant, RoomQrCode
from app.modules.payments.models import Order
from app.modules.rooms.models import RoomUse


class DiningService:
    @staticmethod
    def _deliverable_use(session: Session, room_use_id: str) -> RoomUse | None:
        use = session.get(RoomUse, room_use_id)
        now = utcnow()
        if use and use.status == "ACTIVE" and use.actual_start_at <= now < use.actual_end_at:
            return use
        return None

    @staticmethod
    def create_order(session: Session, *, member_id: str | None, room_code: str,
                     items: list[tuple[str, int]]) -> tuple[FoodOrder, Order]:
        qr = session.scalar(select(RoomQrCode).where(RoomQrCode.code == room_code.upper()))
        if qr is None or not qr.active:
            raise ApiError(404, "ROOM_CODE_INVALID", "Room code is invalid or disabled")
        now = utcnow()
        use = session.scalar(select(RoomUse).where(
            RoomUse.room_id == qr.room_id, RoomUse.status == "ACTIVE",
            RoomUse.actual_start_at <= now, RoomUse.actual_end_at > now,
        ).order_by(RoomUse.actual_start_at.desc()).limit(1))
        if use is None:
            raise ApiError(409, "ROOM_NOT_AVAILABLE", "Room is not available for new dining orders")
        if not items or any(quantity <= 0 or quantity > 50 for _, quantity in items):
            raise ApiError(422, "CART_INVALID", "Cart must contain positive item quantities")
        item_ids = [item_id for item_id, _ in items]
        records = {item.id: item for item in session.scalars(
            select(MenuItem).where(MenuItem.id.in_(item_ids)))}
        if len(records) != len(set(item_ids)):
            raise ApiError(404, "MENU_ITEM_NOT_FOUND", "A menu item was not found")
        if any(not records[item_id].available for item_id, _ in items):
            raise ApiError(409, "MENU_ITEM_UNAVAILABLE", "A menu item is unavailable")
        if len({records[item_id].merchant_id for item_id, _ in items}) != 1:
            raise ApiError(422, "SINGLE_MERCHANT_REQUIRED", "Each order must belong to one merchant")
        merchant_ids = {records[item_id].merchant_id for item_id, _ in items}
        active_merchants = set(session.scalars(select(Merchant.id).where(
            Merchant.id.in_(merchant_ids), Merchant.active.is_(True))).all())
        if active_merchants != merchant_ids:
            raise ApiError(409, "MERCHANT_UNAVAILABLE", "Merchant is not accepting orders")
        amount = sum(records[item_id].price_cents * quantity for item_id, quantity in items)
        order = Order(id=new_id("ord"), order_no=new_business_no("FD"), member_id=member_id,
                      order_type="FOOD", amount_cents=amount)
        food = FoodOrder(id=new_id("foo"), order_id=order.id, room_use_id=use.id,
                         room_id=use.room_id, merchant_id=records[items[0][0]].merchant_id)
        order.business_id = food.id
        session.add_all([order, food])
        session.flush()
        for item_id, quantity in items:
            item = records[item_id]
            if item.stock is not None and item.stock < quantity:
                raise ApiError(409, "MENU_ITEM_UNAVAILABLE", f"Insufficient stock for {item.name}")
            session.add(FoodOrderItem(id=new_id("foi"), food_order_id=food.id, menu_item_id=item.id,
                                      name_snapshot=item.name, unit_price_cents=item.price_cents, quantity=quantity))
        session.flush()
        return food, order

    @staticmethod
    def mark_paid(session: Session, order: Order) -> str:
        food = session.get(FoodOrder, order.business_id, with_for_update=True)
        if food is None:
            raise ApiError(409, "ORDER_INVALID", "Food order is missing")
        if food.fulfillment_status in ("QUEUED", "ACCEPTED", "PREPARING", "DELIVERED"):
            return "PAID"
        if food.fulfillment_status == "EXCEPTION":
            return "EXCEPTION"
        use = DiningService._deliverable_use(session, food.room_use_id)
        if use is None:
            food.fulfillment_status = "EXCEPTION"
            food.exception_reason = "Original room use is no longer deliverable"
            session.flush()
            return "EXCEPTION"
        for line in food.items:
            item = session.get(MenuItem, line.menu_item_id, with_for_update=True)
            if item is None or not item.available or (item.stock is not None and item.stock < line.quantity):
                food.fulfillment_status = "EXCEPTION"
                food.exception_reason = f"Menu item unavailable: {line.name_snapshot}"
                session.flush()
                return "EXCEPTION"
        for line in food.items:
            item = session.get(MenuItem, line.menu_item_id)
            if item.stock is not None:
                item.stock -= line.quantity
        food.fulfillment_status = "QUEUED"
        food.queued_at = utcnow()
        session.flush()
        return "PAID"

    @staticmethod
    def advance(session: Session, food_order_id: str, target: str, *, actor: str,
                reason: str, request_id: str) -> FoodOrder:
        from app.modules.audit import audit

        food = session.get(FoodOrder, food_order_id, with_for_update=True)
        allowed = {"QUEUED": "ACCEPTED", "ACCEPTED": "PREPARING", "PREPARING": "DELIVERED"}
        if food is None or allowed.get(food.fulfillment_status) != target:
            raise ApiError(409, "FULFILLMENT_TRANSITION_INVALID", "Unsupported fulfillment transition")
        before = food.fulfillment_status
        food.fulfillment_status = target
        if target == "DELIVERED":
            food.delivered_at = utcnow()
        audit(session, actor=actor, action="FOOD_FULFILLMENT", entity_type="food_order",
              entity_id=food.id, before=before, after=target, reason=reason, request_id=request_id)
        session.flush()
        return food
