import json
from urllib.error import URLError

import pytest


def transport(monkeypatch, responses):
    from app.modules.identity import wechat
    calls = []

    class Response:
        def __init__(self, result):
            self.result = result

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit):
            return json.dumps(self.result).encode()

    def fake_open(request, timeout):
        calls.append(request)
        return Response(responses.pop(0))

    monkeypatch.setattr(wechat, 'urlopen', fake_open)
    return calls


def test_blank_server_secret_is_reported_as_unconfigured(client):
    from pydantic import SecretStr
    from app.core.config import get_settings
    from app.core.errors import ApiError
    from app.modules.identity.wechat import get_wechat_client
    get_settings().wechat_ticket_appid = 'test-ticket'
    get_settings().wechat_ticket_appsecret = SecretStr('')
    with pytest.raises(ApiError) as error:
        get_wechat_client()
    assert error.value.code == 'WECHAT_NOT_CONFIGURED'


def test_wechat_codes_are_sent_to_separate_endpoints_and_token_is_cached(client, monkeypatch):
    from urllib.parse import parse_qs, urlsplit
    from app.modules.identity.wechat import WechatClient
    calls = transport(monkeypatch, [
        {'openid': 'real-openid', 'session_key': 'server-only'},
        {'access_token': 'server-token', 'expires_in': 7200},
        {'errcode': 0, 'phone_info': {'countryCode': '86', 'purePhoneNumber': '13800000001',
          'phoneNumber': '13800000001', 'watermark': {'appid': 'ticket-app', 'timestamp': 1700000000}}},
        {'errcode': 0, 'phone_info': {'countryCode': '86', 'purePhoneNumber': '13800000002'}},
    ])
    api = WechatClient('ticket-app', 'server-secret')
    assert api.exchange_login('login-code') == 'real-openid'
    assert api.exchange_phone('phone-code') == '+8613800000001'
    assert api.exchange_phone('phone-code-2') == '+8613800000002'
    assert parse_qs(urlsplit(calls[0].full_url).query)['js_code'] == ['login-code']
    assert json.loads(calls[2].data) == {'code': 'phone-code'}
    assert len([call for call in calls if '/stable_token' in call.full_url]) == 1


@pytest.mark.parametrize('reply', [
    {'errcode': 40029, 'errmsg': 'sensitive upstream text'},
    {'errcode': 0, 'phone_info': {'countryCode': '86', 'purePhoneNumber': 'not-a-phone'}},
    {'errcode': 0, 'phone_info': {'countryCode': '86', 'purePhoneNumber': '13800000001',
                                'watermark': {'appid': 'another-app'}}},
])
def test_phone_rejects_failed_malformed_or_wrong_app_authorization(client, monkeypatch, reply):
    from app.core.errors import ApiError
    from app.modules.identity.wechat import WechatClient
    transport(monkeypatch, [{'access_token': 'server-token', 'expires_in': 7200}, reply])
    with pytest.raises(ApiError) as error:
        WechatClient('ticket-app', 'secret').exchange_phone('phone-code')
    assert error.value.code == 'PHONE_AUTH_FAILED'
    assert 'sensitive' not in str(error.value)


def test_network_failure_does_not_disclose_secret_or_code(client, monkeypatch):
    from app.core.errors import ApiError
    from app.modules.identity import wechat

    def fail(*args, **kwargs):
        raise URLError('url with server-secret and login-code')

    monkeypatch.setattr(wechat, 'urlopen', fail)
    with pytest.raises(ApiError) as error:
        wechat.WechatClient('ticket-app', 'server-secret').exchange_login('login-code')
    assert error.value.code == 'WECHAT_UNAVAILABLE'
    assert 'server-secret' not in str(error.value)
    assert 'login-code' not in str(error.value)
