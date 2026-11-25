from datetime import date, timedelta


def pay(client, order_no, member_headers):
    payment = client.post(f"/api/v1/orders/{order_no}/payments", headers=member_headers,
                          json={"method": "wechat"})
    assert payment.status_code == 201, payment.text
    confirmed = client.post(f"/api/v1/payments/{payment.json()['payment_no']}/mock-confirm",
                            headers=member_headers)
    assert confirmed.status_code == 200, confirmed.text


def test_public_ticket_number_frontdesk_first_use_and_repeat(client, member_headers, frontdesk_headers):
    order = client.post("/api/v1/tickets/orders", headers=member_headers, json={
        "visit_date": str(date.today()), "adult_count": 1, "child_count": 0}).json()
    path = f"/api/v1/tickets/orders/{order['order_no']}"
    assert client.get(path, headers=member_headers).json()["tickets"] == []
    pay(client, order["order_no"], member_headers)
    ticket_no = client.get(path, headers=member_headers).json()["tickets"][0]["ticket_no"]
    preview = client.get(f"/api/v1/operations/orders/{order['order_no']}", headers=frontdesk_headers)
    assert preview.status_code == 200
    assert preview.json()["tickets"][0]["ticket_no"] == ticket_no
    assert preview.json()["tickets"][0]["status"] == "UNUSED"
    assert client.get(path, headers=member_headers).json()["tickets"][0]["status"] == "UNUSED"
    assert client.get(f"/api/v1/operations/orders/{ticket_no}", headers=frontdesk_headers).json()["order_no"] == order["order_no"]
    payload = {"code": ticket_no, "request_id": "public-voucher-first"}
    assert client.post("/api/v1/operations/tickets/admit-code", headers=member_headers, json=payload).status_code == 403
    first = client.post("/api/v1/operations/tickets/admit-code", headers=frontdesk_headers, json=payload)
    assert first.status_code == 200, first.text
    assert first.json()["remaining_tickets"] == 0
    assert client.post("/api/v1/operations/tickets/admit-code", headers=frontdesk_headers, json=payload).status_code == 200
    payload["request_id"] = "public-voucher-repeat"
    repeat = client.post("/api/v1/operations/tickets/admit-code", headers=frontdesk_headers, json=payload)
    assert repeat.status_code == 409
    assert repeat.json()["code"] == "TICKET_ALREADY_USED"
    assert client.get(path, headers=member_headers).json()["tickets"][0]["status"] == "USED"


def test_private_voucher_frontdesk_first_use_and_repeat(client, member_headers, frontdesk_headers):
    visit = date.today() + timedelta(days=5)
    created = client.post("/api/v1/rooms/bookings", headers=member_headers, json={
        "visit_date": str(visit), "slot_indices": [0], "expected_arrival_at": f"{visit}T10:00:00"})
    assert created.status_code == 201, created.text
    order = created.json()
    path = f"/api/v1/rooms/bookings/{order['booking_id']}"
    assert order.get("ticket_no") is None
    pay(client, order["order_no"], member_headers)
    paid = client.get(path, headers=member_headers).json()
    assert paid["ticket_no"] and paid["ticket_no"] != order["order_no"]
    assert paid["voucher_status"] == "UNUSED"
    preview = client.get(f"/api/v1/operations/orders/{order['order_no']}", headers=frontdesk_headers)
    assert preview.status_code == 200
    assert preview.json()["private_booking"]["ticket_no"] == paid["ticket_no"]
    assert preview.json()["private_booking"]["voucher_status"] == "UNUSED"
    assert client.get(path, headers=member_headers).json()["voucher_status"] == "UNUSED"
    assert client.get(f"/api/v1/operations/orders/{paid['ticket_no']}", headers=frontdesk_headers).json()["order_no"] == order["order_no"]
    payload = {"code": paid["ticket_no"], "request_id": "private-voucher-first", "actual_start": f"{visit}T10:00:00"}
    assert client.post("/api/v1/operations/rooms/verify-code", headers=member_headers, json=payload).status_code == 403
    first = client.post("/api/v1/operations/rooms/verify-code", headers=frontdesk_headers, json=payload)
    assert first.status_code == 200, first.text
    assert first.json()["room_number"]
    assert client.post("/api/v1/operations/rooms/verify-code", headers=frontdesk_headers, json=payload).status_code == 200
    payload["request_id"] = "private-voucher-repeat"
    repeat = client.post("/api/v1/operations/rooms/verify-code", headers=frontdesk_headers, json=payload)
    assert repeat.status_code == 409, repeat.text
    assert repeat.json()["code"] == "PRIVATE_TICKET_ALREADY_USED"
    assert client.get(path, headers=member_headers).json()["voucher_status"] == "USED"


def test_member_refund_requires_review_and_blocks_admission(client, member_headers, frontdesk_headers, finance_headers):
    order = client.post("/api/v1/tickets/orders", headers=member_headers, json={
        "visit_date": str(date.today()), "adult_count": 1, "child_count": 0}).json()
    pay(client, order["order_no"], member_headers)
    detail = client.get(f"/api/v1/tickets/orders/{order['order_no']}", headers=member_headers).json()
    path = f"/api/v1/orders/{order['order_no']}/refund-application"
    application = client.post(path, headers=member_headers, json={"reason": "行程变化"})
    assert application.status_code == 200, application.text
    assert application.json()["status"] == "PENDING"
    manual = client.post(f"/api/v1/operations/orders/{order['order_no']}/refunds", headers=finance_headers,
                         json={"reason": "不可绕过会员申请审核"})
    assert manual.status_code == 409
    assert manual.json()["code"] == "REFUND_REVIEW_PENDING"
    assert client.get(f"/api/v1/orders/{order['order_no']}", headers=member_headers).json()["status"] == "PAID"
    verify = {"code": detail["tickets"][0]["ticket_no"], "request_id": "refund-pending-scan"}
    blocked = client.post("/api/v1/operations/tickets/admit-code", headers=frontdesk_headers, json=verify)
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "REFUND_REVIEW_PENDING"
    review = f"/api/v1/operations/refund-applications/{order['order_no']}/review"
    assert client.post(review, headers=member_headers, json={"approve": True, "reason": "审核"}).status_code == 403
    rejected = client.post(review, headers=finance_headers, json={"approve": False, "reason": "先沟通"})
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "REJECTED"
    assert client.post(path, headers=member_headers, json={"reason": "再次申请"}).json()["status"] == "PENDING"
    approved = client.post(review, headers=finance_headers, json={"approve": True, "reason": "同意全额退回"})
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "APPROVED"
    assert approved.json()["refund_status"] == "ACCEPTED"
    assert client.post(review, headers=finance_headers, json={"approve": True, "reason": "重复请求"}).json()["refund_no"] == approved.json()["refund_no"]
    assert client.get(path, headers=member_headers).json()["status"] == "APPROVED"
    assert client.post("/api/v1/operations/tickets/admit-code", headers=frontdesk_headers, json=verify).status_code == 409


def test_used_ticket_cannot_request_refund(client, member_headers, frontdesk_headers):
    order = client.post("/api/v1/tickets/orders", headers=member_headers, json={
        "visit_date": str(date.today()), "adult_count": 1, "child_count": 0}).json()
    pay(client, order["order_no"], member_headers)
    ticket_no = client.get(f"/api/v1/tickets/orders/{order['order_no']}", headers=member_headers).json()["tickets"][0]["ticket_no"]
    assert client.post("/api/v1/operations/tickets/admit-code", headers=frontdesk_headers,
                       json={"code": ticket_no, "request_id": "used-refund-test"}).status_code == 200
    response = client.post(f"/api/v1/orders/{order['order_no']}/refund-application", headers=member_headers, json={"reason": "已使用不应退款"})
    assert response.status_code == 409


def test_private_review_freezes_verification_and_rejection_restores_it(client, member_headers, frontdesk_headers, finance_headers):
    visit = date.today() + timedelta(days=7)
    created = client.post("/api/v1/rooms/bookings", headers=member_headers, json={
        "visit_date": str(visit), "slot_indices": [0], "expected_arrival_at": f"{visit}T10:00:00"}).json()
    pay(client, created["order_no"], member_headers)
    paid = client.get(f"/api/v1/rooms/bookings/{created['booking_id']}", headers=member_headers).json()
    application = f"/api/v1/orders/{created['order_no']}/refund-application"
    assert client.post(application, headers=member_headers, json={"reason": "退订"}).status_code == 200
    payload = {"code": paid["ticket_no"], "request_id": "private-refund-freeze", "actual_start": f"{visit}T10:00:00"}
    response = client.post("/api/v1/operations/rooms/verify-code", headers=frontdesk_headers, json=payload)
    assert response.status_code == 409
    assert response.json()["code"] == "REFUND_REVIEW_PENDING"
    assert client.get("/api/v1/operations/refund-applications", headers=member_headers).status_code == 403
    queue = client.get("/api/v1/operations/refund-applications", headers=finance_headers).json()
    assert queue[0]["order_no"] == created["order_no"]
    assert client.post(f"/api/v1/operations/refund-applications/{created['order_no']}/review", headers=finance_headers,
                       json={"approve": False, "reason": "旅客确认继续使用"}).status_code == 200
    assert client.post("/api/v1/operations/rooms/verify-code", headers=frontdesk_headers, json=payload).status_code == 200
    assert client.post(application, headers=member_headers, json={"reason": "已核销后申请"}).status_code == 409


def test_recharge_has_no_refund_and_members_cannot_apply_for_another_order(client, db, member_headers):
    activities = client.get("/api/v1/catalog/recharge-activities").json()
    recharge = client.post("/api/v1/wallet/recharges", headers=member_headers, json={"activity_id": activities[0]["id"]}).json()
    pay(client, recharge["order_no"], member_headers)
    path = f"/api/v1/orders/{recharge['order_no']}/refund-application"
    assert client.post(path, headers=member_headers, json={"reason": "不允许储值退款"}).status_code == 409
    from app.core.auth import AuthContext, Role, get_current_auth
    client.app.dependency_overrides[get_current_auth] = lambda: AuthContext(role=Role.MEMBER, member_id="other-member")
    assert client.get(path, headers=member_headers).status_code == 404
    assert client.post(path, headers=member_headers, json={"reason": "越权申请"}).status_code == 404


def test_balance_refund_only_moves_funds_after_approval(client, db, member_headers, finance_headers):
    from app.modules.wallet.service import WalletService
    WalletService.credit(db, "member-demo", 10000, 0, "review-test-credit")
    db.commit()
    original = client.get("/api/v1/wallet/balance", headers=member_headers).json()["available_cents"]
    order = client.post("/api/v1/tickets/orders", headers=member_headers, json={
        "visit_date": str(date.today()), "adult_count": 1, "child_count": 0}).json()
    assert client.post(f"/api/v1/orders/{order['order_no']}/payments", headers=member_headers, json={"method": "balance"}).status_code == 201
    after_payment = original - order["amount_cents"]
    path = f"/api/v1/orders/{order['order_no']}/refund-application"
    assert client.post(path, headers=member_headers, json={"reason": "余额原路退回"}).status_code == 200
    assert client.get("/api/v1/wallet/balance", headers=member_headers).json()["available_cents"] == after_payment
    review = f"/api/v1/operations/refund-applications/{order['order_no']}/review"
    result = client.post(review, headers=finance_headers, json={"approve": True, "reason": "同意"})
    assert result.status_code == 200, result.text
    assert result.json()["refund_status"] == "SUCCESS"
    assert client.get("/api/v1/wallet/balance", headers=member_headers).json()["available_cents"] == original
    assert client.post(review, headers=finance_headers, json={"approve": True, "reason": "重复"}).status_code == 200
    assert client.get("/api/v1/wallet/balance", headers=member_headers).json()["available_cents"] == original
