from datetime import datetime, timedelta

from sqlalchemy import select


def test_booking_dates_use_beijing_day_and_real_inventory(client, db, monkeypatch):
    from app.modules.catalog.business_hours import BEIJING
    from app.modules.rooms import router
    from app.modules.rooms.models import Room, RoomBlock

    today = datetime(2026, 11, 18, 1, tzinfo=BEIJING)
    monkeypatch.setattr(router, "now_beijing", lambda: today)
    for room in db.scalars(select(Room)).all():
        db.add(RoomBlock(id=f"calendar-{room.id}", room_id=room.id,
                         start_at=datetime(2026, 11, 18), end_at=datetime(2026, 11, 19),
                         reason="calendar test", kind="MANUAL"))
    db.commit()
    response = client.get("/api/v1/rooms/dates")
    assert response.status_code == 200
    days = response.json()["dates"]
    assert len(days) == 7
    assert days[0] == {"value": "2026-11-18", "available": False, "weekday": "周三", "label": "今天"}
    assert days[1]["value"] == "2026-11-19"
    assert days[1]["available"] is True
    assert days[-1]["value"] == (today + timedelta(days=6)).date().isoformat()
