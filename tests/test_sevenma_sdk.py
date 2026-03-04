import base64
import json
import unittest
from typing import Any

from sevenma_sdk import (
    APIStatusError,
    CaptchaRequiredError,
    InvalidTokenError,
    SevenMaClient,
    decode_jwt_payload,
)


def _b64(data: dict[str, Any]) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _jwt(payload: dict[str, Any]) -> str:
    return f"{_b64({'alg': 'none', 'typ': 'JWT'})}.{_b64(payload)}.sig"


class _FakeResponse:
    def __init__(self, *, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers: dict[str, str] = {}
        self.text = ""

    def json(self) -> Any:
        return self._payload


class _FakeSession:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response

    async def request(self, **_: Any) -> _FakeResponse:
        return self._response

    async def close(self) -> None:
        return None


class TokenTests(unittest.TestCase):
    def test_decode_invalid_token_raises_sdk_error(self) -> None:
        with self.assertRaises(InvalidTokenError):
            decode_jwt_payload("bad-token")

    def test_set_token_invalid_token_raises_sdk_error(self) -> None:
        client = SevenMaClient()
        with self.assertRaises(InvalidTokenError):
            client.set_token("bad-token")

    def test_clear_token_removes_identity_and_auth_headers(self) -> None:
        token = _jwt(
            {
                "user_id": 123456,
                "phone": "13800000000",
                "exp": 9999999999,
                "username": "u",
                "nickname": "n",
                "school_name": "s",
            }
        )
        client = SevenMaClient(token=token)
        self.assertIn("authorization", client.auth_headers)
        self.assertIn("u-user-id", client.auth_headers)

        client.clear_token()

        self.assertIsNone(client.user_id)
        self.assertIsNone(client.phone_number)
        self.assertIsNone(client.username)
        self.assertIsNone(client.nickname)
        self.assertIsNone(client.school_name)
        self.assertNotIn("authorization", client.auth_headers)
        self.assertNotIn("u-user-id", client.auth_headers)
        self.assertNotIn("u-user-id", client.headers)


class LoginWithSmsTests(unittest.IsolatedAsyncioTestCase):
    async def test_login_with_sms_raises_captcha_for_40301(self) -> None:
        response = _FakeResponse(
            status_code=200,
            payload={"status_code": 40301, "message": "need captcha", "data": {}},
        )
        client = SevenMaClient(session=_FakeSession(response))
        with self.assertRaises(CaptchaRequiredError):
            await client.login_with_sms("13800000000", "123456")

    async def test_login_with_sms_rejects_403001(self) -> None:
        response = _FakeResponse(
            status_code=200,
            payload={"status_code": 403001, "message": "account action required", "data": {}},
        )
        client = SevenMaClient(session=_FakeSession(response))
        with self.assertRaises(APIStatusError) as ctx:
            await client.login_with_sms("13800000000", "123456")
        self.assertEqual(ctx.exception.status_code, 403001)


if __name__ == "__main__":
    unittest.main()
