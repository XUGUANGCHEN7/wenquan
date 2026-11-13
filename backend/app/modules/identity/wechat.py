"""Server-side WeChat transport. No development identities or phone fallbacks."""
import json
import re
import threading
import time
from functools import lru_cache
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import get_settings
from app.core.errors import ApiError


class WechatClient:
    def __init__(self, appid: str, secret: str):
        self.appid = appid
        self._secret = secret
        self._access_token = ''
        self._token_until = 0.0
        self._lock = threading.Lock()

    def _request(self, path: str, *, query=None, payload=None) -> dict:
        url = 'https://api.weixin.qq.com' + path
        if query:
            url += '?' + urlencode(query)
        data = json.dumps(payload).encode() if payload is not None else None
        request = Request(url, data=data, headers={'Content-Type': 'application/json'})
        try:
            with urlopen(request, timeout=10) as response:
                result = json.loads(response.read(65536))
        except (URLError, TimeoutError, OSError, ValueError):
            # Do not include URLs, codes, upstream messages or credentials in API errors.
            raise ApiError(502, 'WECHAT_UNAVAILABLE', '微信服务暂不可用，请稍后重试') from None
        if not isinstance(result, dict):
            raise ApiError(502, 'WECHAT_UNAVAILABLE', '微信返回异常，请稍后重试')
        return result

    def exchange_login(self, code: str) -> str:
        result = self._request('/sns/jscode2session', query={
            'appid': self.appid, 'secret': self._secret, 'js_code': code,
            'grant_type': 'authorization_code',
        })
        openid = result.get('openid')
        if result.get('errcode') or not isinstance(openid, str) or not 1 <= len(openid) <= 128:
            raise ApiError(401, 'WECHAT_LOGIN_FAILED', '微信登录失败，请重新登录')
        return openid

    def _token(self) -> str:
        with self._lock:
            if self._access_token and time.monotonic() < self._token_until:
                return self._access_token
            result = self._request('/cgi-bin/stable_token', payload={
                'grant_type': 'client_credential', 'appid': self.appid, 'secret': self._secret,
            })
            token = result.get('access_token')
            expires = result.get('expires_in')
            if result.get('errcode') or not isinstance(token, str) or not token or not isinstance(expires, int):
                raise ApiError(502, 'WECHAT_TOKEN_FAILED', '微信服务配置或权限异常，请联系商家')
            self._access_token = token
            self._token_until = time.monotonic() + max(0, expires - 120)
            return token

    def exchange_phone(self, code: str) -> str:
        result = self._request('/wxa/business/getuserphonenumber',
                               query={'access_token': self._token()}, payload={'code': code})
        if result.get('errcode') in (40001, 40014, 42001):
            with self._lock:
                self._token_until = 0
            raise ApiError(502, 'WECHAT_TOKEN_EXPIRED', '微信凭证已失效，请重新授权手机号')
        info = result.get('phone_info') or {}
        if not isinstance(info, dict):
            info = {}
        country = str(info.get('countryCode', ''))
        number = info.get('purePhoneNumber', '')
        if result.get('errcode') or not isinstance(number, str) or not re.fullmatch(r'[1-9]\d{0,2}', country):
            raise ApiError(400, 'PHONE_AUTH_FAILED', '手机号授权失败，请重新授权')
        phone = '+' + country + number
        watermark = info.get('watermark')
        if watermark and (not isinstance(watermark, dict) or watermark.get('appid') != self.appid):
            raise ApiError(400, 'PHONE_AUTH_FAILED', '手机号授权来源不匹配')
        if not re.fullmatch(r'\+[1-9]\d{7,14}', phone):
            raise ApiError(400, 'PHONE_AUTH_FAILED', '微信返回的手机号格式异常')
        return phone


@lru_cache(maxsize=4)
def _client(appid: str, secret: str) -> WechatClient:
    return WechatClient(appid, secret)


def get_wechat_client() -> WechatClient:
    settings = get_settings()
    if not settings.wechat_ticket_appid or not settings.wechat_ticket_appsecret:
        raise ApiError(503, 'WECHAT_NOT_CONFIGURED', '商家尚未配置微信登录，请联系商家')
    return _client(settings.wechat_ticket_appid, settings.wechat_ticket_appsecret.get_secret_value())
