from datetime import date, datetime, time, timedelta

from fastapi.testclient import TestClient


def test_ticket_and_private_booking_api_uses_server_prices(client: TestClient, db, member_headers, frontdesk_headers):
    from app.modules.wallet.service import WalletService

    WalletService.credit(db, "member-demo", 100_000, 0, "api-funds")
    db.commit()
    visit_date = date.today() + timedelta(days=7)
    while visit_date.weekday() >= 5:
        visit_date += timedelta(days=1)
    prices = client.get(f"/api/v1/catalog/ticket-prices?visit_date={visit_date}").json()
    assert prices["adult_cents"] == 2_900

    ticket = client.post("/api/v1/tickets/orders", headers=member_headers, json={
        "visit_date": str(visit_date), "adult_count": 2, "child_count": 0})
    assert ticket.status_code == 201
    ticket_order = ticket.json()["order_no"]
    paid = client.post(f"/api/v1/orders/{ticket_order}/payments", headers=member_headers,
                       json={"method": "balance"})
    assert paid.status_code == 201
    assert paid.json()["status"] == "success"
    details = client.get(f"/api/v1/tickets/orders/{ticket_order}", headers=member_headers).json()
    assert len(details["tickets"]) == 2

    assert client.post("/api/v1/operations/tickets/admit", headers=member_headers, json={
        "ticket_no": details["tickets"][0]["ticket_no"], "request_id": "api-admit-denied"}).status_code == 403
    admitted = client.post("/api/v1/operations/tickets/admit", headers=frontdesk_headers, json={
        "ticket_no": details["tickets"][0]["ticket_no"], "request_id": "api-admit-1", "reason": "visual check"})
    assert admitted.status_code == 200

    slots = client.get(f"/api/v1/rooms/slots?visit_date={visit_date}").json()
    assert len(slots["slots"]) == 5
    expected = datetime.combine(visit_date, time(9, 30)).isoformat()
    booking = client.post("/api/v1/rooms/bookings", headers=member_headers, json={
        "visit_date": str(visit_date), "slot_indices": [0, 1], "expected_arrival_at": expected})
    assert booking.status_code == 201
    body = booking.json()
    assert body["amount_cents"] == 24_000
    assert "internal_room_id" not in body
    assert body["room_number"] is None
    private_payment = client.post(f"/api/v1/orders/{body['order_no']}/payments", headers=member_headers,
                                  json={"method": "balance"})
    assert private_payment.json()["status"] == "success"
    orders = client.get("/api/v1/orders", headers=member_headers).json()
    assert {item["order_no"] for item in orders} >= {ticket_order, body["order_no"]}


def test_guest_room_dining_api_and_merchant_queue(client: TestClient, merchant_headers):
    context = client.get("/api/v1/dining/room-context/ROOM-01")
    assert context.status_code == 200
    assert context.json()["room_number"] == "01"
    assert context.json()["can_order"] is True
    menu = client.get("/api/v1/dining/menu").json()
    noodles = next(item for item in menu if item["id"] == "menu-noodles")

    created = client.post("/api/v1/dining/orders", json={
        "room_code": "ROOM-01", "items": [{"menu_item_id": noodles["id"], "quantity": 1}]})
    assert created.status_code == 201
    order_no = created.json()["order_no"]
    assert created.json()["amount_cents"] == noodles["price_cents"]
    payment = client.post(f"/api/v1/orders/{order_no}/payments", json={"method": "wechat"})
    assert payment.status_code == 201
    confirmed = client.post(f"/api/v1/payments/{payment.json()['payment_no']}/mock-confirm")
    assert confirmed.status_code == 200
    detail = client.get(f"/api/v1/dining/orders/{order_no}").json()
    assert detail["fulfillment_status"] == "QUEUED"
    assert detail["items"][0]["name_snapshot"] == "暖汤荞麦面"

    queue = client.get("/api/v1/operations/dining/orders", headers=merchant_headers).json()
    food_id = next(item for item in queue if item["order_no"] == order_no)["id"]
    for status in ("ACCEPTED", "PREPARING", "DELIVERED"):
        response = client.post(f"/api/v1/operations/dining/orders/{food_id}/transition",
                               headers=merchant_headers, json={"status": status, "reason": "workflow test"})
        assert response.status_code == 200
    assert client.get(f"/api/v1/dining/orders/{order_no}").json()["fulfillment_status"] == "DELIVERED"
