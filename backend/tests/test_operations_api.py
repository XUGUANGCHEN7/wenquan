from fastapi.testclient import TestClient


def test_device_api_requires_device_role_and_preserves_task_result(client: TestClient, db, member_headers, device_headers):
    from app.modules.devices.service import DeviceService

    task = DeviceService.create_task(db, task_type="DIAGNOSTIC", idempotency_key="api-diagnostic-1", operator="test")
    db.commit()
    assert client.post("/api/v1/devices/tasks/poll", headers=member_headers,
                       json={"worker_id": "worker-api", "reader_id": "reader-api"}).status_code == 403
    polled = client.post("/api/v1/devices/tasks/poll", headers=device_headers,
                         json={"worker_id": "worker-api", "reader_id": "reader-api"})
    assert polled.status_code == 200
    assert polled.json()["id"] == task.id
    assert client.post(f"/api/v1/devices/tasks/{task.id}/claim", headers=device_headers,
                       json={"worker_id": "worker-api", "reader_id": "reader-api"}).status_code == 200
    assert client.post(f"/api/v1/devices/tasks/{task.id}/start", headers=device_headers,
                       json={"worker_id": "worker-api"}).status_code == 200
    result = client.post(f"/api/v1/devices/tasks/{task.id}/result", headers=device_headers,
                         json={"worker_id": "worker-api", "result": "UNKNOWN", "raw_error": "offline"})
    assert result.status_code == 200
    assert result.json()["status"] == "UNKNOWN"


def test_admin_catalog_room_code_and_price_updates_are_server_owned(client: TestClient, admin_headers, member_headers):
    from datetime import date, timedelta

    visit_date = date.today() + timedelta(days=30)
    denied = client.post(f"/api/v1/admin/ticket-prices/{visit_date}", headers=member_headers,
                         json={"adult_cents": 3900, "child_cents": 1900, "is_holiday": True, "note": "test"})
    assert denied.status_code == 403
    updated = client.post(f"/api/v1/admin/ticket-prices/{visit_date}", headers=admin_headers,
                          json={"adult_cents": 3900, "child_cents": 1900, "is_holiday": True, "note": "test"})
    assert updated.status_code == 200
    assert client.get(f"/api/v1/catalog/ticket-prices?visit_date={visit_date}").json()["adult_cents"] == 3900

    activity = client.post("/api/v1/admin/recharge-activities", headers=admin_headers, json={
        "id": "activity-test", "name": "测试活动", "principal_cents": 30000, "gift_cents": 3000, "active": True})
    assert activity.status_code == 200
    assert any(item["id"] == "activity-test" for item in client.get("/api/v1/catalog/recharge-activities").json())

    menu = client.post("/api/v1/admin/menu-items/menu-noodles", headers=admin_headers,
                       json={"price_cents": 3900, "stock": 88, "available": True, "description": "updated"})
    assert menu.status_code == 200
    assert next(item for item in client.get("/api/v1/dining/menu").json() if item["id"] == "menu-noodles")["price_cents"] == 3900

    disabled = client.post("/api/v1/admin/room-codes/qr-01", headers=admin_headers,
                           json={"active": False, "reprint": False})
    assert disabled.status_code == 200
    assert client.get("/api/v1/dining/room-context/ROOM-01").status_code == 404
    enabled = client.post("/api/v1/admin/room-codes/qr-01", headers=admin_headers,
                          json={"active": True, "reprint": True})
    assert enabled.json()["version"] == 2
    assert client.get("/api/v1/dining/room-context/ROOM-01").json()["can_order"] is True


def test_admin_merchant_and_menu_crud_is_role_scoped(client: TestClient, admin_headers, member_headers):
    payload = {"name": "测试商家", "active": True}
    assert client.post("/api/v1/admin/merchants", headers=member_headers, json=payload).status_code == 403
    merchant = client.post("/api/v1/admin/merchants", headers=admin_headers, json=payload)
    assert merchant.status_code == 201
    merchant_id = merchant.json()["id"]
    assert any(item["id"] == merchant_id for item in client.get("/api/v1/dining/merchants").json())

    item_payload = {
        "merchant_id": merchant_id, "name": "测试套餐", "description": "现做",
        "category": "简餐", "image_url": "", "price_cents": 2680, "stock": 20, "available": True,
    }
    item = client.post("/api/v1/admin/menu-items", headers=admin_headers, json=item_payload)
    assert item.status_code == 201
    item_id = item.json()["id"]
    public_menu = client.get(f"/api/v1/dining/menu?merchant_id={merchant_id}").json()
    assert len(public_menu) == 1
    assert public_menu[0]["price_cents"] == 2680

    renamed = client.patch(f"/api/v1/admin/merchants/{merchant_id}", headers=admin_headers,
                           json={"name": "测试商家（更新）", "active": True})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "测试商家（更新）"
    changed = dict(item_payload, price_cents=2880, available=False)
    updated = client.patch(f"/api/v1/admin/menu-items/{item_id}", headers=admin_headers, json=changed)
    assert updated.status_code == 200
    assert updated.json()["price_cents"] == 2880
    assert updated.json()["available"] is False

    assert client.delete(f"/api/v1/admin/merchants/{merchant_id}", headers=admin_headers).status_code == 409
    assert client.delete(f"/api/v1/admin/menu-items/{item_id}", headers=admin_headers).status_code == 200
    assert client.delete(f"/api/v1/admin/merchants/{merchant_id}", headers=admin_headers).status_code == 200
    assert not any(item["id"] == merchant_id for item in client.get("/api/v1/dining/merchants").json())


def test_dining_room_choices_are_server_owned(client: TestClient):
    rooms = client.get("/api/v1/dining/rooms")
    assert rooms.status_code == 200
    assert len(rooms.json()) == 17
    assert next(item for item in rooms.json() if item["room_code"] == "ROOM-01")["can_order"] is True


def test_finance_manual_refund_reverses_balance_once_and_is_role_scoped(client: TestClient, db, member_headers, finance_headers):
    from datetime import date, timedelta

    from app.modules.wallet.service import WalletService

    visit_date = date.today() + timedelta(days=9)
    while visit_date.weekday() >= 5:
        visit_date += timedelta(days=1)
    WalletService.credit(db, "member-demo", 50_000, 0, "refund-api-funds")
    db.commit()
    order = client.post("/api/v1/tickets/orders", headers=member_headers,
                        json={"visit_date": str(visit_date), "adult_count": 1, "child_count": 0}).json()
    payment = client.post(f"/api/v1/orders/{order['order_no']}/payments", headers=member_headers,
                          json={"method": "balance"})
    assert payment.json()["status"] == "success"
    before = client.get("/api/v1/wallet/balance", headers=member_headers).json()["available_cents"]

    assert client.post(f"/api/v1/operations/orders/{order['order_no']}/refunds", headers=member_headers,
                       json={"reason": "denied"}).status_code == 403
    refund = client.post(f"/api/v1/operations/orders/{order['order_no']}/refunds",
                         headers=finance_headers, json={"reason": "业务方签认退款"})
    assert refund.status_code == 200
    assert refund.json()["status"] == "SUCCESS"
    repeated = client.post(f"/api/v1/operations/orders/{order['order_no']}/refunds",
                           headers=finance_headers, json={"reason": "重复点击"})
    assert repeated.json()["refund_no"] == refund.json()["refund_no"]
    after = client.get("/api/v1/wallet/balance", headers=member_headers).json()["available_cents"]
    assert after == before + order["amount_cents"]


def test_finance_report_and_admin_config_are_role_scoped(client: TestClient, db, finance_headers, member_headers, admin_headers):
    from app.modules.wallet.service import WalletService

    WalletService.credit(db, "member-demo", 10_000, 2_000, "report-funds")
    WalletService.debit(db, "member-demo", 11_000, "report-consume")
    db.commit()
    assert client.get("/api/v1/operations/wallet/member-demo", headers=member_headers).status_code == 403
    wallet = client.get("/api/v1/operations/wallet/member-demo", headers=finance_headers)
    assert wallet.status_code == 200
    assert wallet.json()["principal_cents"] == 0
    assert wallet.json()["gift_cents"] == 1_000
    assert len(wallet.json()["entries"]) == 2

    report = client.get("/api/v1/operations/reports/daily", headers=finance_headers)
    assert report.status_code == 200
    assert "unrefunded_deposit_cents" in report.json()
    assert "ticket_revenue_cents" in report.json()
    exceptions = client.get("/api/v1/operations/exceptions", headers=finance_headers)
    assert exceptions.status_code == 200
    assert {"refunds", "device_unknown", "room_conflicts", "food_delivery"} <= set(exceptions.json())

    assert client.post("/api/v1/admin/config/private_slot_price_cents", headers=member_headers,
                       json={"value": 12_000, "description": "denied"}).status_code == 403
    updated = client.post("/api/v1/admin/config/private_slot_price_cents", headers=admin_headers,
                          json={"value": 12_100, "description": "admin test"})
    assert updated.status_code == 200
    assert updated.json()["value"] == 12_100
