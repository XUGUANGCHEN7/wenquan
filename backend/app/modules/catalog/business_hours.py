"""Venue hours use the existing business config store and Beijing server time."""
from datetime import datetime, timedelta, timezone
from math import ceil

from app.modules.catalog.models import BusinessConfig

BEIJING = timezone(timedelta(hours=8))
DEFAULTS = {"business_open_minutes": 540, "business_close_minutes": 1320, "business_rest_date": 0}


def now_beijing():
    return datetime.now(BEIJING)


def business_hours(session):
    values = {key: record.value if (record := session.get(BusinessConfig, key)) else default
              for key, default in DEFAULTS.items()}
    now = now_beijing()
    opening = values["business_open_minutes"]
    closing = values["business_close_minutes"]
    rest = values["business_rest_date"] == int(now.strftime("%Y%m%d"))
    start = now.replace(hour=opening // 60, minute=opening % 60, second=0, microsecond=0)
    end = now.replace(hour=closing // 60, minute=closing % 60, second=0, microsecond=0)
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    status = "REST" if rest else "NOT_OPEN" if now < start else "OPEN" if now < end else "CLOSED"
    next_change = midnight if rest or now >= end else start if now < start else end
    return {"opens_at": f"{opening // 60:02}:{opening % 60:02}",
            "closes_at": f"{closing // 60:02}:{closing % 60:02}",
            "rest_today": rest, "business_date": now.date().isoformat(), "status": status,
            "refresh_after_seconds": max(1, min(60, ceil((next_change - now).total_seconds())))}
