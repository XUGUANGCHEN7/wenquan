from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from test_access import prepare, succeed_issue


def test_frontdesk_room_assignment_and_cleaning_api(client: TestClient, db, frontdesk_headers):
    from app.modules.rooms.service import RoomService

    visit_date = date.today() + timedelta(days=2)
    booking, _ = RoomService.create_booking(
        db, member_id="member-demo", visit_date=visit_date, slot_indices=[0],
        expected_arrival_at=datetime.combine(visit_date, datetime.min.time()))
    booking.status = "CONFIRMED"
    db.commit()
    board = client.get("/api/v1/operations/rooms/board", headers=frontdesk_headers)
    assert board.status_code == 200
    assert len(board.json()) == 17

    assigned = client.post(f"/api/v1/operations/rooms/bookings/{booking.id}/assign",
                           headers=frontdesk_headers,
                           json={"actual_start": datetime.now().isoformat(), "reason": "arrival test"})
    assert assigned.status_code == 200
    assert assigned.json()["room_number"]
    use_id = assigned.json()["room_use_id"]
    assert client.post(f"/api/v1/operations/rooms/uses/{use_id}/finish", headers=frontdesk_headers,
                       json={"reason": "test finished"}).status_code == 200
    assert client.post(f"/api/v1/operations/rooms/uses/{use_id}/cleaning/start",
                       headers=frontdesk_headers).status_code == 200
    completed = client.post(f"/api/v1/operations/rooms/uses/{use_id}/cleaning/complete",
                            headers=frontdesk_headers)
    assert completed.status_code == 200
    assert completed.json()["status"] == "COMPLETED"


def test_unissued_paid_deposit_can_be_refunded_without_card_binding(client: TestClient, db, frontdesk_headers):
    from app.modules.payments.service import PaymentService

    _, group, order = prepare(db)
    payment = PaymentService.create_payment(db, order.order_no, "member-access", "WECHAT")
    PaymentService.confirm_mock(db, payment.payment_no, member_id="member-access", mock_enabled=True)
    db.commit()
    first = client.post(f"/api/v1/operations/deposits/{group.deposits[0].id}/refund",
                        headers=frontdesk_headers, json={"reason": "card issuance abandoned"})
    second = client.post(f"/api/v1/operations/deposits/{group.deposits[0].id}/refund",
                         headers=frontdesk_headers, json={"reason": "repeated click"})
    assert first.status_code == second.status_code == 200
    assert second.json()["refund_no"] == first.json()["refund_no"]


def test_frontdesk_access_issue_return_and_overview_api(client: TestClient, db, frontdesk_headers):
    from app.modules.access.models import CardBinding
    from app.modules.access.service import AccessService
    from app.modules.devices.service import DeviceService
    from app.modules.payments.service import PaymentService

    _, group, order = prepare(db)
    payment = PaymentService.create_payment(db, order.order_no, "member-access", "WECHAT")
    PaymentService.confirm_mock(db, payment.payment_no, member_id="member-access", mock_enabled=True)
    db.commit()
    overview = client.get("/api/v1/operations/access/overview", headers=frontdesk_headers)
    assert overview.status_code == 200
    assert len(overview.json()["cards"]) >= 40

    issued = client.post("/api/v1/operations/cards/issue", headers=frontdesk_headers,
                         json={"deposit_id": group.deposits[0].id, "card_id": "card-01"})
    assert issued.status_code == 201
    binding_id = issued.json()["binding_id"]
    task_id = issued.json()["task"]["id"]
    DeviceService.claim(db, task_id, worker_id="worker-api", reader_id="reader-api")
    DeviceService.start(db, task_id, worker_id="worker-api")
    DeviceService.report(db, task_id, worker_id="worker-api", result="SUCCEEDED")
    db.commit()

    returned = client.post(f"/api/v1/operations/cards/{binding_id}/return", headers=frontdesk_headers,
                           json={"reason": "physical return verified"})
    assert returned.status_code == 200
    assert returned.json()["refund_no"].startswith("DR-")
    clear_task_id = returned.json()["clear_task"]["id"]
    DeviceService.claim(db, clear_task_id, worker_id="worker-api", reader_id="reader-api")
    DeviceService.start(db, clear_task_id, worker_id="worker-api")
    DeviceService.report(db, clear_task_id, worker_id="worker-api", result="SUCCEEDED")
    db.commit()
    binding = db.get(CardBinding, binding_id)
    cleaned = client.post(f"/api/v1/operations/lockers/{binding.locker_id}/cleaned",
                          headers=frontdesk_headers, json={"reason": "locker cleaned"})
    assert cleaned.status_code == 200
    assert cleaned.json()["status"] == "FREE"
