from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.catalog.models import RechargeActivity
from app.modules.tickets.service import TicketService

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


@router.get("/ticket-prices")
def ticket_prices(visit_date: date, session: Session = Depends(get_db)):
    adult, child = TicketService.prices(session, visit_date)
    return {"visit_date": visit_date, "adult_cents": adult, "child_cents": child, "currency": "CNY"}


@router.get("/recharge-activities")
def recharge_activities(session: Session = Depends(get_db)):
    activities = session.scalars(
        select(RechargeActivity).where(RechargeActivity.active.is_(True)).order_by(RechargeActivity.principal_cents)
    ).all()
    return [
        {
            "id": item.id, "name": item.name,
            "principal_cents": item.principal_cents, "gift_cents": item.gift_cents,
        }
        for item in activities
    ]
