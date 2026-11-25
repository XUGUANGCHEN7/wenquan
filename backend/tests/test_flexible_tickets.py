from datetime import datetime, timedelta
import pytest


@pytest.mark.parametrize("kind", ["WEEKDAY", "HOLIDAY"])
def test_dateless_ticket_prices_validity_and_day_check(client, db, member_headers, frontdesk_headers, monkeypatch, kind):
    from app.modules.tickets import service
    from app.modules.tickets.models import TicketBatch
    products = client.get("/api/v1/catalog/ticket-products").json()
    product = next(item for item in products if item["day_type"] == kind)
    response = client.post("/api/v1/tickets/orders", headers=member_headers,
                           json={"day_type": kind, "adult_count": 1, "child_count": 1})
    assert response.status_code == 201, response.text
    order = response.json()
    assert order["amount_cents"] == product["adult_cents"] + product["child_cents"]
    batch = db.get(TicketBatch, order["batch_id"])
    assert batch.visit_date is None and batch.valid_until is None
    payment = client.post(f"/api/v1/orders/{order['order_no']}/payments", headers=member_headers, json={"method": "wechat"}).json()
    assert client.post(f"/api/v1/payments/{payment['payment_no']}/mock-confirm", headers=member_headers).status_code == 200
    detail = client.get(f"/api/v1/orders/{order['order_no']}", headers=member_headers).json()
    paid_at = datetime.fromisoformat(detail["paid_at"])
    until = datetime.fromisoformat(detail["valid_until"])
    assert until - paid_at == timedelta(days=30)
    assert detail["visit_date"] is None and detail["day_type"] == kind
    # Pick both valid and invalid Beijing admission weekdays inside the validity window.
    for desired_holiday in (False, True):
        now = paid_at + timedelta(days=1)
        while ((now + timedelta(hours=8)).weekday() >= 5) != desired_holiday:
            now += timedelta(days=1)
        monkeypatch.setattr(service, "utcnow", lambda: now)
        preview = client.get(f"/api/v1/operations/orders/{order['order_no']}", headers=frontdesk_headers).json()
        assert preview["tickets"][0]["can_admit"] == (desired_holiday == (kind == "HOLIDAY"))
    from app.modules.catalog.models import TicketPriceRule
    weekday = paid_at + timedelta(days=1)
    while (weekday + timedelta(hours=8)).weekday() >= 5:
        weekday += timedelta(days=1)
    db.add(TicketPriceRule(visit_date=(weekday + timedelta(hours=8)).date(), adult_cents=9900, child_cents=8800, is_holiday=True))
    db.commit()
    monkeypatch.setattr(service, "utcnow", lambda: weekday)
    holiday_preview = client.get(f"/api/v1/operations/orders/{order['order_no']}", headers=frontdesk_headers).json()
    assert holiday_preview["tickets"][0]["can_admit"] == (kind == "HOLIDAY")
    assert holiday_preview["amount_cents"] == order["amount_cents"]
    monkeypatch.setattr(service, "utcnow", lambda: until)
    result = client.post("/api/v1/operations/tickets/admit", headers=frontdesk_headers,
                         json={"ticket_no": detail["tickets"][0]["ticket_no"], "request_id": "expired-ticket"})
    assert result.status_code == 409 and result.json()["code"] == "TICKET_EXPIRED"
    now = paid_at + timedelta(days=1)
    while service.TicketService.is_holiday(db, (now + timedelta(hours=8)).date()) != (kind == "HOLIDAY"):
        now += timedelta(days=1)
    monkeypatch.setattr(service, "utcnow", lambda: now)
    admitted = client.post("/api/v1/operations/tickets/admit-batch", headers=frontdesk_headers,
                          json={"order_no": order["order_no"], "ticket_nos": [item["ticket_no"] for item in detail["tickets"]], "request_id": "correct-day-admit", "reason": "核对票种"})
    assert admitted.status_code == 200, admitted.text
    assert admitted.json()["admitted_count"] == 2


def test_holiday_override_and_ambiguous_order_rejected(client, db, member_headers):
    from datetime import date
    from app.modules.catalog.models import TicketPriceRule
    from app.modules.tickets.service import TicketService
    day = date(2026, 11, 17)
    db.add(TicketPriceRule(visit_date=day, adult_cents=3900, child_cents=1900, is_holiday=True))
    db.commit()
    assert TicketService.is_holiday(db, day)
    assert client.post("/api/v1/tickets/orders", headers=member_headers, json={"adult_count": 1, "child_count": 0}).status_code == 422
    assert client.post("/api/v1/tickets/orders", headers=member_headers, json={"day_type": "WEEKDAY", "visit_date": str(day), "adult_count": 1, "child_count": 0}).status_code == 422
