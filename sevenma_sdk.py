from curl_cffi import AsyncSession
from typing import Any, cast
import base64
import json
import time
import random

def decode_jwt_payload(token: str) -> dict[str, Any]:
    # JWT 结构是 Header.Payload.Signature
    _, payload_b64, _ = token.split('.')
    
    # 补齐 Base64 填充符 '='
    missing_padding = len(payload_b64) % 4
    if missing_padding:
        payload_b64 += '=' * (4 - missing_padding)
        
    payload_json = base64.urlsafe_b64decode(payload_b64).decode('utf-8')
    return json.loads(payload_json)

def generate_trace_id() -> str:
    e = int(time.time() * 1000)
    template = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx"
    out: list[str] = []

    for ch in template:
        if ch in ("x", "y"):
            n = int((e + 16 * random.random()) % 16)
            e //= 16
            v = n if ch == "x" else (n & 0x3) | 0x8
            out.append(f"{v:x}")

    return "".join(out)

class SevenMaClient:

    def __init__(
        self,
        base_url: str = "https://newmapi.7mate.cn/api/v1",
        auth_base_url: str = "https://newmapi.7mate.cn/auth",
        timeout: float = 15.0,
        session: AsyncSession | None = None,
        token: str | None = None,
        phone_model: str = "Mac14,15",
        phone_system: str = "Android",
        phone_brand: str = "apple",
        phone_system_version: str = "Mac OS X 15.7.4 arm64",
        client: str = "Wechat_MiniAPP",
        x_app_id: str = "default",
        app_version: str = "1.3.165",
        user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Mac MacWechat/WMPF MacWechat/3.8.7(0x13080712) UnifiedPCMacWechat(0xf2641721) XWEB/18788"
    ):
        self.base_url = base_url.rstrip("/")
        self.auth_base_url = auth_base_url.rstrip("/")
        self.timeout = timeout

        self.session = session or AsyncSession()

        self.token = token
        self.token_expire_time_ms: int | None = None
        self.user_id: int | None = None
        self.phone_number: str | None = None
        self.username: str | None = None
        self.nickname: str | None = None
        self.school_name: str | None = None

        if token:
            self.set_token(token)

        self.phone_model = phone_model
        self.phone_system = phone_system
        self.phone_brand = phone_brand
        self.phone_system_version = phone_system_version
        self.client = client
        self.x_trace_id: str | None = None
        self.genielamp_h_session: str | None = None
        self.x_app_id = x_app_id
        self.app_version = app_version
        self.user_agent = user_agent

    def set_token(self, token: str):
        self.token = token
        payload = decode_jwt_payload(token)
        self.user_id = payload.get("user_id")
        self.phone_number = payload.get("phone")
        self.token_expire_time_ms = int(cast(float, payload.get("exp", 0)) * 1000)
        self.username = payload.get("username")
        self.nickname = payload.get("nickname")
        self.school_name = payload.get("school_name")

    @property
    def headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "phone-model": self.phone_model,
            "xweb_xhr": "1",
            "phone-system": self.phone_system,
            "phone-brand": self.phone_brand,
            "client": self.client,
            "u-user-id": str(random.randint(2900000, 3000000)),
            "x-app-id": self.x_app_id,
            "app-version": self.app_version,
            "user-agent": self.user_agent,
            "accept": "application/vnd.ws.v1+json",
            "phone-system-version": self.phone_system_version,
            "referer": "https://servicewechat.com/wx9a6a1a8407b04c5d/344/page-frame.html",
        }
        if self.x_trace_id:
            headers["x-trace-id"] = self.x_trace_id
        if self.genielamp_h_session:
            headers["genielamp-h-session"] = self.genielamp_h_session
        return headers
    
    @property
    def auth_headers(self) -> dict[str, str]:
        return self.headers | {
            "authorization": f"Bearer {self.token}" if self.token else "",
            "u-user-id": str(self.user_id) if self.user_id else "",
        }

    async def close(self):
        await self.session.close()

    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *_):
        await self.close()

    async def _post(self, url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        resp = await self.session.post(url, json=payload, headers=headers, timeout=self.timeout)
        self.x_trace_id = resp.headers.get("x-trace-id")
        if "genielamp-h-session" in resp.headers:
            self.genielamp_h_session = resp.headers["genielamp-h-session"]
        if resp.status_code != 200:
            raise Exception(f"Failed to send request: {resp.status_code} {resp.text}")
        return resp.json() # type: ignore[no-any-return]

    async def send_sms(self, phone_number: str) -> dict[str, Any]:
        url = f"{self.auth_base_url}/sms/send"
        payload: dict[str, str | int] = {
            "phone": phone_number,
            "type": "login",
            "scene": 1
        }
        resp = await self._post(url, payload, self.headers)
        return resp.get("data", {})
    
    async def login_with_sms(self, phone_number: str, code: str, device_id: str = "") -> str:
        if not device_id:
            device_id = self.phone_model + "_not_openid"
        url = f"{self.auth_base_url}/login"
        payload: dict[str, str | bool] = {
            "phone": phone_number,
            "code": code,
            "device_id": device_id,
            "login_type": "sms_code",
            "force_new_account": False,
            "restore_confirm": False
        }
        resp = await self._post(url, payload, self.headers)
        token: str = resp.get("data", {}).get("token")
        if not token:
            raise Exception(f"Login response does not contain token: {resp}")
        self.set_token(token)
        return token

    
async def main():
    async with SevenMaClient() as client:
        pass
        # 1. 测试发送验证码接口(done)
        phone_number = "13800000000"  # 替换为你要测试的手机号
        response = await client.send_sms(phone_number)
        print(response)
        # 2. 测试登录接口(done, 需要配合验证码接口)
        code = input("请输入验证码: ")
        token = await client.login_with_sms(phone_number, code)
        print(f"登录成功，token: {token}")
        print(f"用户ID: {client.user_id}, 手机号: {client.phone_number}, 昵称: {client.nickname}, 学校: {client.school_name}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())