from datetime import date

from test_ticket_verification_flow import pay


def make_order(client, member_headers, count=3):
    response = client.post("/api/v1/tickets/orders", headers=member_headers, json={
        "visit_date": str(date.today()), "adult_count": count, "child_count": 0})
    assert response.status_code == 201, response.text
    order = response.json()
    pay(client, order["order_no"], member_headers)
    detail = client.get(f"/api/v1/tickets/orders/{order['order_no']}", headers=member_headers).json()
    return order["order_no"], [ticket["ticket_no"] for ticket in detail["tickets"]]


def test_lookup_by_ticket_then_admit_selected_tickets(client, member_headers, frontdesk_headers):
    order_no, tickets = make_order(client, member_headers)
    lookup = client.get(f"/api/v1/operations/orders/{tickets[0]}", headers=frontdesk_headers)
    assert lookup.status_code == 200
    assert lookup.json()["order_no"] == order_no
    assert all(ticket["can_admit"] for ticket in lookup.json()["tickets"])
    payload = {"order_no": order_no, "ticket_nos": tickets[:2], "request_id": "batch-selected-1", "reason": "游客确认两人入园"}
    path = "/api/v1/operations/tickets/admit-batch"
    assert client.post(path, headers=member_headers, json=payload).status_code == 403
    first = client.post(path, headers=frontdesk_headers, json=payload)
    assert first.status_code == 200, first.text
    assert first.json()["admitted_count"] == 2
    assert first.json()["remaining_tickets"] == 1
    repeated = client.post(path, headers=frontdesk_headers, json={**payload, "ticket_nos": list(reversed(tickets[:2]))})
    assert repeated.status_code == 200
    assert repeated.json() == first.json()
    assert client.post(path, headers=frontdesk_headers, json={**payload, "ticket_nos": tickets}).status_code == 409
    refreshed = client.get(f"/api/v1/operations/orders/{order_no}", headers=frontdesk_headers).json()
    assert [ticket["status"] for ticket in refreshed["tickets"]] == ["USED", "USED", "UNUSED"]
    assert [ticket["can_admit"] for ticket in refreshed["tickets"]] == [False, False, True]
    other_order, other_tickets = make_order(client, member_headers, 1)
    conflict = client.post(path, headers=frontdesk_headers, json={**payload, "order_no": other_order, "ticket_nos": other_tickets})
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "BATCH_REQUEST_CONFLICT"


def test_batch_is_atomic_when_any_ticket_was_already_used(client, member_headers, frontdesk_headers):
    order_no, tickets = make_order(client, member_headers)
    assert client.post("/api/v1/operations/tickets/admit-code", headers=frontdesk_headers,
                       json={"code": tickets[1], "request_id": "single-before-bulk"}).status_code == 200
    payload = {"order_no": order_no, "ticket_nos": tickets, "request_id": "batch-stale-selection"}
    result = client.post("/api/v1/operations/tickets/admit-batch", headers=frontdesk_headers, json=payload)
    assert result.status_code == 409, result.text
    detail = client.get(f"/api/v1/tickets/orders/{order_no}", headers=member_headers).json()
    assert [ticket["status"] for ticket in detail["tickets"]] == ["UNUSED", "USED", "UNUSED"]


def test_batch_rejects_other_orders_duplicates_and_empty_selection(client, member_headers, frontdesk_headers):
    order_no, tickets = make_order(client, member_headers)
    _, other_tickets = make_order(client, member_headers, 1)
    path = "/api/v1/operations/tickets/admit-batch"
    for selected in [[], [tickets[0], tickets[0]], [tickets[0], other_tickets[0]]]:
        response = client.post(path, headers=frontdesk_headers, json={
            "order_no": order_no, "ticket_nos": selected, "request_id": "invalid-bulk-selection"})
        assert response.status_code in (409, 422), response.text
    detail = client.get(f"/api/v1/tickets/orders/{order_no}", headers=member_headers).json()
    assert all(ticket["status"] == "UNUSED" for ticket in detail["tickets"])


def test_pending_refund_disables_selection_and_batch_admission(client, member_headers, frontdesk_headers):
    order_no, tickets = make_order(client, member_headers)
    assert client.post(f"/api/v1/orders/{order_no}/refund-application", headers=member_headers,
                       json={"reason": "行程有变"}).status_code == 200
    lookup = client.get(f"/api/v1/operations/orders/{tickets[0]}", headers=frontdesk_headers).json()
    assert not any(ticket["can_admit"] for ticket in lookup["tickets"])
    result = client.post("/api/v1/operations/tickets/admit-batch", headers=frontdesk_headers, json={
        "order_no": order_no, "ticket_nos": tickets, "request_id": "batch-pending-refund"})
    assert result.status_code == 409
    assert result.json()["code"] == "REFUND_REVIEW_PENDING"


def test_failure_during_batch_rolls_back_already_written_admission(client, member_headers, frontdesk_headers, monkeypatch):
    order_no, tickets = make_order(client, member_headers)
    from app.modules.tickets.service import TicketService
    from app.core.errors import ApiError
    original = TicketService.admit
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ApiError(409, "TEST_BATCH_FAILURE", "second admission failed")
        return original(*args, **kwargs)

    monkeypatch.setattr(TicketService, "admit", fail_second)
    result = client.post("/api/v1/operations/tickets/admit-batch", headers=frontdesk_headers, json={
        "order_no": order_no, "ticket_nos": tickets, "request_id": "batch-rollback-test"})
    assert result.status_code == 409
    detail = client.get(f"/api/v1/tickets/orders/{order_no}", headers=member_headers).json()
    assert all(ticket["status"] == "UNUSED" for ticket in detail["tickets"])
