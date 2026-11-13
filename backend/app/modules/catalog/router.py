from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.catalog.models import RechargeActivity, RechargeActivityWindow
from app.modules.tickets.service import TicketService

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


@router.get("/business-hours")
def venue_business_hours(session: Session = Depends(get_db)):
    from app.modules.catalog.business_hours import business_hours

    return business_hours(session)


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
            "starts_on": (window.starts_on if (window := session.get(RechargeActivityWindow, item.id)) else None),
            "ends_on": (window.ends_on if window else None),
        }
        for item in activities
    ]
