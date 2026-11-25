from datetime import date, timedelta
from test_ticket_verification_flow import pay


def test_order_detail_by_real_id_includes_all_ticket_numbers(client, member_headers, frontdesk_headers):
    created = client.post("/api/v1/tickets/orders", headers=member_headers, json={
        "visit_date": str(date.today()), "adult_count": 2, "child_count": 1}).json()
    pay(client, created["order_no"], member_headers)
    listed = client.get("/api/v1/orders", headers=member_headers).json()
    selected = next(order for order in listed if order["order_no"] == created["order_no"])
    assert selected["id"] != created["order_no"]
    detail = client.get(f"/api/v1/orders/{selected['id']}", headers=member_headers)
    assert detail.status_code == 200
    data = detail.json()
    assert data["order_no"] == created["order_no"]
    assert data["quantity"] == 3
    assert len(data["tickets"]) == 3
    assert len({ticket["ticket_no"] for ticket in data["tickets"]}) == 3
    assert data["paid_amount_cents"] == created["amount_cents"]
    assert data["paid_at"] and data["created_at"]
    assert client.get(f"/api/v1/orders/{created['order_no']}", headers=member_headers).json()["id"] == selected["id"]
    from app.core.auth import AuthContext, Role, get_optional_auth
    client.app.dependency_overrides[get_optional_auth] = lambda: AuthContext(role=Role.MEMBER, member_id="other-member")
    assert client.get(f"/api/v1/orders/{selected['id']}", headers=member_headers).status_code == 403


def test_recharge_detail_shows_actual_credit_and_no_vouchers(client, member_headers):
    activity = client.get("/api/v1/catalog/recharge-activities").json()[0]
    created = client.post("/api/v1/wallet/recharges", headers=member_headers, json={"activity_id": activity["id"]}).json()
    path = f"/api/v1/orders/{created['order_no']}"
    pending = client.get(path, headers=member_headers).json()
    assert pending["paid_amount_cents"] == 0
    assert pending["credited_cents"] == 0
    pay(client, created["order_no"], member_headers)
    paid = client.get(path, headers=member_headers).json()
    assert paid["principal_cents"] == activity["principal_cents"]
    assert paid["gift_cents"] == activity["gift_cents"]
    assert paid["credited_cents"] == activity["principal_cents"] + activity["gift_cents"]
    assert "tickets" not in paid and "ticket_no" not in paid


def test_private_detail_by_id_preserves_booking_and_voucher_data(client, member_headers):
    visit = date.today() + timedelta(days=9)
    created = client.post("/api/v1/rooms/bookings", headers=member_headers, json={
        "visit_date": str(visit), "slot_indices": [0], "expected_arrival_at": f"{visit}T10:00:00"}).json()
    pay(client, created["order_no"], member_headers)
    detail = client.get(f"/api/v1/orders/{created['id']}", headers=member_headers).json()
    assert detail["booking_id"] == created["booking_id"]
    assert detail["ticket_no"] == f"PV-{created['booking_id']}"
    assert detail["voucher_status"] == "UNUSED"
    assert detail["slot_count"] == 1 and detail["quantity"] == 1
    assert detail["room_number"] is None
    assert detail["paid_amount_cents"] == created["amount_cents"]
