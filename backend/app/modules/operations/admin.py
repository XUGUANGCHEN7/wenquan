from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, Role, require_roles
from app.core.database import get_db
from app.core.errors import ApiError
from app.modules.audit import audit
from app.modules.catalog.models import BusinessConfig, RechargeActivity, TicketPriceRule
from app.modules.common import new_id, utcnow
from app.modules.dining.models import FoodOrder, FoodOrderItem, MenuItem, Merchant, RoomQrCode

router = APIRouter(prefix="/api/v1/admin", tags=["administration"])
AdminAuth = Annotated[AuthContext, Depends(require_roles(Role.ADMIN))]


class PriceRequest(BaseModel):
    adult_cents: int = Field(ge=0)
    child_cents: int = Field(ge=0)
    is_holiday: bool = False
    note: str = Field(default="", max_length=200)


class ActivityRequest(BaseModel):
    id: str | None = Field(default=None, max_length=64)
    name: str = Field(min_length=1, max_length=80)
    principal_cents: int = Field(gt=0)
    gift_cents: int = Field(ge=0)
    active: bool = True


class MenuItemRequest(BaseModel):
    price_cents: int = Field(ge=0)
    stock: int | None = Field(default=None, ge=0)
    available: bool = True
    description: str = Field(default="", max_length=300)


class MerchantPayload(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    active: bool = True


class MenuItemPayload(BaseModel):
    merchant_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=300)
    category: str = Field(default="热销推荐", min_length=1, max_length=50)
    image_url: str = Field(default="", max_length=500)
    price_cents: int = Field(ge=0)
    stock: int | None = Field(default=None, ge=0)
    available: bool = True


class RoomCodeRequest(BaseModel):
    active: bool
    reprint: bool = False


@router.get("/config")
def configs(auth: AdminAuth, session: Session = Depends(get_db)):
    records = session.scalars(select(BusinessConfig).order_by(BusinessConfig.key)).all()
    return [{"key": item.key, "value": item.value, "description": item.description} for item in records]


@router.get("/merchants")
def merchants(auth: AdminAuth, session: Session = Depends(get_db)):
    records = session.scalars(select(Merchant).order_by(Merchant.name, Merchant.id)).all()
    return [{"id": item.id, "name": item.name, "active": item.active,
             "item_count": len(session.scalars(select(MenuItem.id).where(MenuItem.merchant_id == item.id)).all())}
            for item in records]


@router.post("/merchants", status_code=201)
def create_merchant(payload: MerchantPayload, request: Request, auth: AdminAuth,
                    session: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise ApiError(422, "MERCHANT_NAME_REQUIRED", "商家名称不能为空")
    merchant = Merchant(id=new_id("merchant"), name=name, active=payload.active)
    session.add(merchant)
    audit(session, actor=auth.role, action="MERCHANT_CREATED", entity_type="merchant",
          entity_id=merchant.id, before=None, after=f"{merchant.name}:{merchant.active}",
          reason="管理员新增商家", request_id=request.state.request_id)
    session.commit()
    return {"id": merchant.id, "name": merchant.name, "active": merchant.active, "item_count": 0}


@router.patch("/merchants/{merchant_id}")
def update_merchant(merchant_id: str, payload: MerchantPayload, request: Request, auth: AdminAuth,
                    session: Session = Depends(get_db)):
    merchant = session.get(Merchant, merchant_id, with_for_update=True)
    if merchant is None:
        raise ApiError(404, "MERCHANT_NOT_FOUND", "商家不存在")
    name = payload.name.strip()
    if not name:
        raise ApiError(422, "MERCHANT_NAME_REQUIRED", "商家名称不能为空")
    before = f"{merchant.name}:{merchant.active}"
    merchant.name = name
    merchant.active = payload.active
    audit(session, actor=auth.role, action="MERCHANT_UPDATED", entity_type="merchant",
          entity_id=merchant.id, before=before, after=f"{merchant.name}:{merchant.active}",
          reason="管理员修改商家", request_id=request.state.request_id)
    session.commit()
    return {"id": merchant.id, "name": merchant.name, "active": merchant.active}


@router.delete("/merchants/{merchant_id}")
def delete_merchant(merchant_id: str, request: Request, auth: AdminAuth,
                    session: Session = Depends(get_db)):
    merchant = session.get(Merchant, merchant_id, with_for_update=True)
    if merchant is None:
        raise ApiError(404, "MERCHANT_NOT_FOUND", "商家不存在")
    has_items = session.scalar(select(MenuItem.id).where(MenuItem.merchant_id == merchant.id).limit(1))
    has_orders = session.scalar(select(FoodOrder.id).where(FoodOrder.merchant_id == merchant.id).limit(1))
    if has_items or has_orders:
        raise ApiError(409, "MERCHANT_IN_USE", "商家仍有商品或历史订单，请先下架并停用商家")
    before = f"{merchant.name}:{merchant.active}"
    audit(session, actor=auth.role, action="MERCHANT_DELETED", entity_type="merchant",
          entity_id=merchant.id, before=before, after="DELETED",
          reason="管理员删除商家", request_id=request.state.request_id)
    session.delete(merchant)
    session.commit()
    return {"deleted": True, "id": merchant_id}


@router.get("/menu-items")
def menu_items(auth: AdminAuth, session: Session = Depends(get_db)):
    records = session.execute(select(MenuItem, Merchant).join(
        Merchant, MenuItem.merchant_id == Merchant.id).order_by(Merchant.name, MenuItem.category, MenuItem.name)).all()
    return [{"id": item.id, "merchant_id": item.merchant_id, "merchant_name": merchant.name,
             "merchant_active": merchant.active, "name": item.name, "description": item.description,
             "category": item.category, "image_url": item.image_url, "price_cents": item.price_cents,
             "stock": item.stock, "available": item.available} for item, merchant in records]


@router.post("/menu-items", status_code=201)
def create_menu_item(payload: MenuItemPayload, request: Request, auth: AdminAuth,
                     session: Session = Depends(get_db)):
    merchant = session.get(Merchant, payload.merchant_id)
    if merchant is None:
        raise ApiError(404, "MERCHANT_NOT_FOUND", "商家不存在")
    name, category = payload.name.strip(), payload.category.strip()
    if not name or not category:
        raise ApiError(422, "MENU_ITEM_FIELDS_REQUIRED", "商品名称和分类不能为空")
    item = MenuItem(id=new_id("menu"), merchant_id=merchant.id, name=name,
                    description=payload.description, category=category,
                    image_url=payload.image_url, price_cents=payload.price_cents,
                    stock=payload.stock, available=payload.available)
    session.add(item)
    audit(session, actor=auth.role, action="MENU_ITEM_CREATED", entity_type="menu_item",
          entity_id=item.id, before=None, after=f"{item.name}:{item.price_cents}",
          reason="管理员新增商品", request_id=request.state.request_id)
    session.commit()
    return {"id": item.id, "merchant_id": item.merchant_id, "name": item.name,
            "price_cents": item.price_cents, "stock": item.stock, "available": item.available,
            "category": item.category, "image_url": item.image_url, "description": item.description}


@router.patch("/menu-items/{item_id}")
def update_menu_item_full(item_id: str, payload: MenuItemPayload, request: Request, auth: AdminAuth,
                          session: Session = Depends(get_db)):
    item = session.get(MenuItem, item_id, with_for_update=True)
    if item is None:
        raise ApiError(404, "MENU_ITEM_NOT_FOUND", "商品不存在")
    merchant = session.get(Merchant, payload.merchant_id)
    if merchant is None:
        raise ApiError(404, "MERCHANT_NOT_FOUND", "商家不存在")
    name, category = payload.name.strip(), payload.category.strip()
    if not name or not category:
        raise ApiError(422, "MENU_ITEM_FIELDS_REQUIRED", "商品名称和分类不能为空")
    before = f"{item.name}:{item.price_cents}:{item.available}"
    item.merchant_id = merchant.id
    item.name = name
    item.description = payload.description
    item.category = category
    item.image_url = payload.image_url
    item.price_cents = payload.price_cents
    item.stock = payload.stock
    item.available = payload.available
    audit(session, actor=auth.role, action="MENU_ITEM_UPDATED", entity_type="menu_item",
          entity_id=item.id, before=before, after=f"{item.name}:{item.price_cents}:{item.available}",
          reason="管理员修改商品", request_id=request.state.request_id)
    session.commit()
    return {"id": item.id, "merchant_id": item.merchant_id, "name": item.name,
            "price_cents": item.price_cents, "stock": item.stock, "available": item.available,
            "category": item.category, "image_url": item.image_url, "description": item.description}


@router.delete("/menu-items/{item_id}")
def delete_menu_item(item_id: str, request: Request, auth: AdminAuth,
                     session: Session = Depends(get_db)):
    item = session.get(MenuItem, item_id, with_for_update=True)
    if item is None:
        raise ApiError(404, "MENU_ITEM_NOT_FOUND", "商品不存在")
    has_orders = session.scalar(select(FoodOrderItem.id).where(FoodOrderItem.menu_item_id == item.id).limit(1))
    if has_orders:
        raise ApiError(409, "MENU_ITEM_IN_USE", "商品已有历史订单，不能删除，请改为下架")
    before = f"{item.name}:{item.price_cents}:{item.available}"
    audit(session, actor=auth.role, action="MENU_ITEM_DELETED", entity_type="menu_item",
          entity_id=item.id, before=before, after="DELETED",
          reason="管理员删除商品", request_id=request.state.request_id)
    session.delete(item)
    session.commit()
    return {"deleted": True, "id": item_id}


@router.post("/ticket-prices/{visit_date}")
def update_ticket_price(visit_date: date, payload: PriceRequest, request: Request,
                        auth: AdminAuth, session: Session = Depends(get_db)):
    rule = session.get(TicketPriceRule, visit_date, with_for_update=True)
    before = str(rule.adult_cents) if rule else None
    if rule is None:
        rule = TicketPriceRule(visit_date=visit_date, **payload.model_dump())
        session.add(rule)
    else:
        for key, value in payload.model_dump().items():
            setattr(rule, key, value)
    audit(session, actor=auth.role, action="TICKET_PRICE_UPDATED", entity_type="ticket_price_rule",
          entity_id=str(visit_date), before=before, after=str(rule.adult_cents), reason=payload.note,
          request_id=request.state.request_id)
    session.commit()
    return {"visit_date": rule.visit_date, "adult_cents": rule.adult_cents,
            "child_cents": rule.child_cents, "is_holiday": rule.is_holiday}


@router.post("/recharge-activities")
def update_activity(payload: ActivityRequest, request: Request, auth: AdminAuth,
                    session: Session = Depends(get_db)):
    activity_id = payload.id or new_id("act")
    activity = session.get(RechargeActivity, activity_id, with_for_update=True)
    before = f"{activity.principal_cents}:{activity.gift_cents}:{activity.active}" if activity else None
    if activity is None:
        activity = RechargeActivity(id=activity_id, **payload.model_dump(exclude={"id"}))
        session.add(activity)
    else:
        for key, value in payload.model_dump(exclude={"id"}).items():
            setattr(activity, key, value)
    audit(session, actor=auth.role, action="RECHARGE_ACTIVITY_UPDATED", entity_type="recharge_activity",
          entity_id=activity.id, before=before,
          after=f"{activity.principal_cents}:{activity.gift_cents}:{activity.active}",
          reason="Administrator configuration", request_id=request.state.request_id)
    session.commit()
    return {"id": activity.id, "name": activity.name, "principal_cents": activity.principal_cents,
            "gift_cents": activity.gift_cents, "active": activity.active}


@router.post("/menu-items/{item_id}")
def update_menu_item(item_id: str, payload: MenuItemRequest, request: Request,
                     auth: AdminAuth, session: Session = Depends(get_db)):
    item = session.get(MenuItem, item_id, with_for_update=True)
    if item is None:
        raise ApiError(404, "MENU_ITEM_NOT_FOUND", "Menu item not found")
    before = str(item.price_cents)
    item.price_cents = payload.price_cents
    item.stock = payload.stock
    item.available = payload.available
    item.description = payload.description
    audit(session, actor=auth.role, action="MENU_ITEM_UPDATED", entity_type="menu_item", entity_id=item.id,
          before=before, after=str(item.price_cents), reason=payload.description,
          request_id=request.state.request_id)
    session.commit()
    return {"id": item.id, "price_cents": item.price_cents, "stock": item.stock, "available": item.available}


@router.post("/room-codes/{qr_id}")
def update_room_code(qr_id: str, payload: RoomCodeRequest, request: Request,
                     auth: AdminAuth, session: Session = Depends(get_db)):
    qr = session.get(RoomQrCode, qr_id, with_for_update=True)
    if qr is None:
        raise ApiError(404, "ROOM_CODE_NOT_FOUND", "Room code not found")
    before = f"{qr.active}:{qr.version}"
    qr.active = payload.active
    if payload.reprint:
        qr.version += 1
        qr.printed_at = utcnow()
    audit(session, actor=auth.role, action="ROOM_CODE_UPDATED", entity_type="room_qr_code", entity_id=qr.id,
          before=before, after=f"{qr.active}:{qr.version}", reason="Administrator room-code update",
          request_id=request.state.request_id)
    session.commit()
    return {"id": qr.id, "code": qr.code, "active": qr.active, "version": qr.version,
            "printed_at": qr.printed_at}
