from datetime import timedelta

import pytest
from sqlalchemy import func, select


class FakeWechat:
    appid = 'test-ticket-app'

    def exchange_login(self, code):
        from app.core.errors import ApiError
        if code == 'invalid':
            raise ApiError(401, 'WECHAT_LOGIN_FAILED', '微信登录失败')
        return 'openid-' + code

    def exchange_phone(self, code):
        from app.core.errors import ApiError
        if code == 'denied':
            raise ApiError(400, 'PHONE_AUTH_FAILED', '手机号授权失败')
        return '+8613800000001' if code == 'phone-one' else '+8613800000002'


@pytest.fixture
def wechat(client):
    from app.modules.identity.wechat import get_wechat_client
    client.app.dependency_overrides[get_wechat_client] = lambda: FakeWechat()


def login(client, code='alice'):
    result = client.post('/api/v1/auth/wechat/login', json={'code': code})
    assert result.status_code == 200, result.text
    return result.json()


def register(client, code='alice', phone='phone-one', nickname=''):
    challenge = login(client, code)
    assert challenge['status'] == 'REGISTER_REQUIRED'
    return client.post('/api/v1/auth/wechat/register', json={
        'registration_token': challenge['registration_token'], 'phone_code': phone,
        'nickname': nickname, 'consent': True,
    })


def headers(result):
    return {'Authorization': 'Bearer ' + result['access_token']}


def test_unconfigured_wechat_does_not_create_demo_login(client, monkeypatch):
    from app.core.config import get_settings
    get_settings().wechat_ticket_appid = ''
    result = client.post('/api/v1/auth/wechat/login', json={'code': 'new-user'})
    assert result.status_code == 503
    assert result.json()['code'] == 'WECHAT_NOT_CONFIGURED'


def test_phone_registration_and_repeat_login_reuse_one_wallet(client, db, wechat):
    from app.modules.identity.models import Identity, Member
    from app.modules.wallet.models import MemberAccount
    result = register(client)
    assert result.status_code == 200, result.text
    body = result.json()
    assert body['status'] == 'AUTHENTICATED'
    me = client.get('/api/v1/members/me', headers=headers(body))
    assert me.status_code == 200
    assert me.json()['nickname'] == '会员0001'
    assert me.json()['phone_masked'] == '138****0001'
    assert '+8613800000001' not in me.text
    member_id = me.json()['member_id']
    again = login(client)
    assert again['member_id'] == member_id
    assert again['access_token'] != body['access_token']
    assert db.scalar(select(func.count(Member.id)).where(Member.id == member_id)) == 1
    assert db.scalar(select(func.count(Identity.id)).where(Identity.member_id == member_id)) == 1
    assert db.scalar(select(func.count(MemberAccount.member_id)).where(MemberAccount.member_id == member_id)) == 1
    assert client.get('/api/v1/wallet/balance', headers=headers(body)).json()['available_cents'] == 0
    other = register(client, 'bob', 'phone-two', '小泉').json()
    assert client.get(f'/api/v1/members/{other["member_id"]}/profile', headers=headers(body)).status_code == 403
    assert client.get(f'/api/v1/members/{member_id}/profile', headers=headers(body)).json()['nickname'] == '会员0001'


def test_registration_credential_cannot_read_wallet_and_is_single_use(client, wechat):
    challenge = login(client)
    token = challenge['registration_token']
    assert client.get('/api/v1/wallet/balance', headers={'Authorization': 'Bearer ' + token}).status_code == 401
    payload = {'registration_token': token, 'phone_code': 'phone-one', 'consent': True}
    first = client.post('/api/v1/auth/wechat/register', json=payload)
    assert first.status_code == 200
    assert client.post('/api/v1/auth/wechat/register', json=payload).status_code == 401


def test_phone_conflict_does_not_merge_accounts(client, db, wechat):
    from app.modules.identity.models import Identity, Member
    first = register(client).json()
    second = register(client, code='bob')
    assert second.status_code == 409
    assert second.json()['code'] == 'PHONE_ALREADY_REGISTERED'
    assert db.scalar(select(func.count(Member.id))) == 2  # seed + alice
    assert db.scalar(select(Identity).where(Identity.openid == 'openid-bob')) is None
    assert client.get('/api/v1/members/me', headers=headers(first)).status_code == 200


def test_failed_phone_and_missing_consent_create_no_member(client, db, wechat):
    from app.modules.identity.models import Member
    failed = register(client, phone='denied')
    assert failed.status_code == 400
    challenge = login(client)
    rejected = client.post('/api/v1/auth/wechat/register', json={
        'registration_token': challenge['registration_token'], 'phone_code': 'phone-one', 'consent': False})
    assert rejected.status_code == 422
    assert db.scalar(select(func.count(Member.id))) == 1
    assert client.post('/api/v1/auth/wechat/login', json={'code': 'invalid'}).status_code == 401


def test_logout_expiry_and_disabled_member_reject_session(client, db, wechat):
    from app.modules.common import utcnow
    from app.modules.identity.models import Member, MemberSession
    result = register(client).json()
    auth = headers(result)
    assert client.post('/api/v1/auth/logout', headers=auth).status_code == 200
    assert client.get('/api/v1/members/me', headers=auth).status_code == 401
    result = login(client)
    for session in db.scalars(select(MemberSession).where(MemberSession.member_id == result['member_id'])):
        session.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    assert client.get('/api/v1/members/me', headers=headers(result)).status_code == 401
    result = login(client)
    member = db.get(Member, result['member_id'])
    member.status = 'DISABLED'
    db.commit()
    assert client.get('/api/v1/wallet/balance', headers=headers(result)).status_code == 403
    assert client.post('/api/v1/auth/wechat/login', json={'code': 'alice'}).status_code == 403


def test_legacy_member_completes_phone_without_resetting_wallet(client, db, wechat):
    from app.modules.identity.models import Identity
    from app.modules.wallet.models import MemberAccount
    db.add(Identity(id='legacy-identity', appid='test-ticket-app', openid='openid-legacy', member_id='member-demo'))
    db.get(MemberAccount, 'member-demo').principal_cents = 2300
    db.commit()
    body = register(client, code='legacy', nickname='老会员').json()
    assert body['member_id'] == 'member-demo'
    assert client.get('/api/v1/wallet/balance', headers=headers(body)).json()['available_cents'] == 2300
    assert client.get('/api/v1/members/me', headers=headers(body)).json()['nickname'] == '老会员'


def test_expired_registration_does_not_consume_phone(client, db, wechat):
    from app.modules.common import utcnow
    from app.modules.identity.models import MemberSession
    challenge = login(client)
    for session in db.scalars(select(MemberSession)):
        session.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    result = client.post('/api/v1/auth/wechat/register', json={
        'registration_token': challenge['registration_token'], 'phone_code': 'phone-one', 'consent': True})
    assert result.status_code == 401


def test_real_member_can_create_ticket_without_client_member_id(client, wechat):
    from datetime import date, timedelta
    body = register(client).json()
    result = client.post('/api/v1/tickets/orders', headers=headers(body), json={
        'visit_date': str(date.today() + timedelta(days=1)), 'adult_count': 1, 'child_count': 0})
    assert result.status_code == 201
    assert client.get('/api/v1/orders', headers=headers(body)).json()[0]['order_no'] == result.json()['order_no']
