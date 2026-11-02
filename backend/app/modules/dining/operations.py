from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, Role, require_roles
from app.core.database import get_db
from app.modules.dining.models import FoodOrder
from app.modules.dining.router import food_dict
from app.modules.dining.service import DiningService
from app.modules.payments.models import Order

router = APIRouter(prefix="/api/v1/operations/dining", tags=["operations-dining"])
MerchantAuth = Annotated[AuthContext, Depends(require_roles(Role.MERCHANT, Role.FRONTDESK, Role.ADMIN))]


class TransitionRequest(BaseModel):
    status: Literal["ACCEPTED", "PREPARING", "DELIVERED"]
    reason: str = Field(min_length=1, max_length=500)


@router.get("/orders")
def orders(auth: MerchantAuth, session: Session = Depends(get_db)):
    records = session.scalars(select(FoodOrder).where(
        FoodOrder.fulfillment_status.in_(["QUEUED", "ACCEPTED", "PREPARING", "DELIVERED"])
    ).order_by(FoodOrder.created_at)).all()
    return [{**food_dict(food, session.get(Order, food.order_id)), "id": food.id} for food in records]


@router.post("/orders/{food_order_id}/transition")
def transition(food_order_id: str, payload: TransitionRequest, request: Request,
               auth: MerchantAuth, session: Session = Depends(get_db)):
    food = DiningService.advance(session, food_order_id, payload.status, actor=auth.role,
                                 reason=payload.reason, request_id=request.state.request_id)
    session.commit()
    return {"id": food.id, "fulfillment_status": food.fulfillment_status, "delivered_at": food.delivered_at}
