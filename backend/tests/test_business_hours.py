from datetime import datetime, timezone
import importlib

import pytest


def test_business_hours_public_defaults(client):
    response = client.get("/api/v1/catalog/business-hours")
    assert response.status_code == 200
    assert response.json()["opens_at"] == "09:00"
    assert response.json()["closes_at"] == "22:00"


@pytest.mark.parametrize("clock,status", [
    ("00:59:59", "NOT_OPEN"), ("01:00:00", "OPEN"),
    ("13:59:59", "OPEN"), ("14:00:00", "CLOSED"),
])
def test_business_status_beijing_boundaries(client, monkeypatch, clock, status):
    hours = importlib.import_module("app.modules.catalog.business_hours")
    monkeypatch.setattr(hours, "now_beijing", lambda: datetime.fromisoformat(
        f"2026-11-13T{clock}+00:00").astimezone(hours.BEIJING))
    data = client.get("/api/v1/catalog/business-hours").json()
    assert data["status"] == status
    assert 1 <= data["refresh_after_seconds"] <= 60


def test_admin_hours_rest_and_next_day_reset(client, admin_headers, monkeypatch):
    hours = importlib.import_module("app.modules.catalog.business_hours")
    monkeypatch.setattr(hours, "now_beijing", lambda: datetime(2026, 11, 13, 12, tzinfo=hours.BEIJING))
    payload = {"opens_at": "10:30", "closes_at": "21:15", "rest_today": True}
    assert client.post("/api/v1/admin/business-hours", json=payload).status_code == 401
    saved = client.post("/api/v1/admin/business-hours", json=payload, headers=admin_headers)
    assert saved.status_code == 200
    public = client.get("/api/v1/catalog/business-hours").json()
    assert public["status"] == "REST"
    assert public["opens_at"] == "10:30"
    assert public["closes_at"] == "21:15"
    monkeypatch.setattr(hours, "now_beijing", lambda: datetime(2026, 11, 14, 12, tzinfo=hours.BEIJING))
    assert client.get("/api/v1/catalog/business-hours").json()["status"] == "OPEN"


@pytest.mark.parametrize("opening,closing", [("22:00", "09:00"), ("09:00", "09:00"), ("25:00", "22:00")])
def test_invalid_hours_not_saved(client, admin_headers, opening, closing):
    response = client.post("/api/v1/admin/business-hours", headers=admin_headers,
                           json={"opens_at": opening, "closes_at": closing, "rest_today": False})
    assert response.status_code == 422
