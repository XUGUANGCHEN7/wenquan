import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select


def make_member(db, member_id: str):
    from app.modules.identity.models import Member
    from app.modules.wallet.models import MemberAccount

    member = Member(id=member_id, nickname="测试会员")
    db.add(member)
    db.add(MemberAccount(member_id=member_id, principal_cents=0, gift_cents=0))
    db.commit()
    return member


def test_cross_app_identity_requires_explicit_verified_binding(db):
    from app.core.errors import ApiError
    from app.modules.identity.service import IdentityService

    make_member(db, "member-bind")
    first = IdentityService.bind(db, appid="app-ticket", openid="openid-a", member_id="member-bind", verified=True)
    second = IdentityService.bind(db, appid="app-dining", openid="openid-b", member_id="member-bind", verified=True)
    assert first.member_id == second.member_id == "member-bind"
    assert first.openid != second.openid

    with pytest.raises(ApiError, match="verified"):
        IdentityService.bind(db, appid="app-other", openid="openid-c", member_id="member-bind", verified=False)


def test_wallet_spends_principal_first_and_reverses_original_source(db):
    from app.modules.wallet.models import LedgerEntry
    from app.modules.wallet.service import WalletService

    make_member(db, "member-wallet")
    WalletService.credit(db, "member-wallet", 10_000, 2_000, "recharge-1")
    debit = WalletService.debit(db, "member-wallet", 11_000, "order-1")
    assert (debit.principal_delta, debit.gift_delta) == (-10_000, -1_000)
    assert WalletService.available_cents(db, "member-wallet") == 1_000

    reversal = WalletService.refund(db, "member-wallet", "order-1", "refund-1")
    assert (reversal.principal_delta, reversal.gift_delta) == (10_000, 1_000)
    assert WalletService.available_cents(db, "member-wallet") == 12_000
    assert reversal.original_entry_id == debit.id

    repeated = WalletService.refund(db, "member-wallet", "order-1", "refund-1")
    assert repeated.id == reversal.id
    assert db.scalar(select(func.count(LedgerEntry.id))) == 3


def test_wallet_rejects_overdraft_without_changing_balance(db):
    from app.core.errors import ApiError
    from app.modules.wallet.service import WalletService

    make_member(db, "member-overdraft")
    with pytest.raises(ApiError, match="Insufficient"):
        WalletService.debit(db, "member-overdraft", 1, "order-too-large")
    assert WalletService.available_cents(db, "member-overdraft") == 0


def test_duplicate_recharge_confirmation_credits_once(client: TestClient, db, member_headers):
    activities = client.get("/api/v1/catalog/recharge-activities").json()
    recharge = client.post(
        "/api/v1/wallet/recharges",
        headers=member_headers,
        json={"activity_id": activities[0]["id"]},
    )
    assert recharge.status_code == 201
    payment_no = recharge.json()["payment_no"]
    assert recharge.json()["payment_method"] == "wechat"

    first = client.post(f"/api/v1/payments/{payment_no}/mock-confirm", headers=member_headers)
    second = client.post(f"/api/v1/payments/{payment_no}/mock-confirm", headers=member_headers)
    assert first.status_code == second.status_code == 200
    assert first.json()["status"] == second.json()["status"] == "success"
    assert first.json()["mode"] == "mock"

    balance = client.get("/api/v1/wallet/balance", headers=member_headers).json()
    assert balance["available_cents"] == activities[0]["principal_cents"] + activities[0]["gift_cents"]
    assert "principal_cents" not in balance
    entries = client.get("/api/v1/wallet/entries", headers=member_headers).json()
    assert len(entries) == 1
    assert entries[0]["delta_cents"] == balance["available_cents"]
