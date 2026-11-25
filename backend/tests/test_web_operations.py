def test_verification_summary_and_period_reports(client, frontdesk_headers, finance_headers):
    summary = client.get("/api/v1/operations/verification-summary", headers=frontdesk_headers)
    assert summary.status_code == 200, summary.text
    assert {"ticket_verifications", "private_verifications"} <= set(summary.json())

    report = client.get("/api/v1/operations/reports/summary?period=week", headers=finance_headers)
    assert report.status_code == 200, report.text
    body = report.json()
    assert body["period"] == "week"
    assert "ticket_revenue_cents" in body and "recharge_principal_cents" in body


def test_wallet_lookup_by_phone(client, db, finance_headers):
    from app.modules.common import utcnow
    from app.modules.identity.models import Member
    from app.modules.wallet.models import MemberAccount

    db.add(Member(id="member-phone-test", nickname="手机号会员", phone="+8613800000009",
                  phone_verified_at=utcnow()))
    db.add(MemberAccount(member_id="member-phone-test", principal_cents=0, gift_cents=0))
    db.commit()

    result = client.get("/api/v1/operations/wallet-by-phone?phone=13800000009", headers=finance_headers)
    assert result.status_code == 200, result.text
    assert result.json()["member_id"] == "member-phone-test"
    assert result.json()["phone_masked"] == "138****0009"


def test_order_lookup_and_ticket_price_config_keys(client, frontdesk_headers, admin_headers):
    order = client.get("/api/v1/operations/orders/DEV-ROOM-USE", headers=frontdesk_headers)
    assert order.status_code == 200, order.text
    assert order.json()["private_booking"]["booking_id"] == "booking-demo-room-use"

    configs = client.get("/api/v1/admin/config", headers=admin_headers)
    keys = {item["key"] for item in configs.json()}
    assert {"ticket_weekday_cents", "ticket_weekend_cents", "ticket_child_cents"} <= keys
