"""SevenMA Python SDK — single-file async version (curl_cffi)."""

from collections.abc import Iterable, Mapping
from curl_cffi.requests import AsyncSession
from datetime import datetime
from typing import Any, Literal, TypedDict, cast
import base64
import binascii
import json
import time
import random

type HttpMethod = Literal["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "TRACE", "PATCH"]
type NumberLike = int | float | str
type ServiceName = Literal["api", "auth", "absolute"]
type SMSKind = Literal["login"]
type LoginKind = Literal["sms_code"]
type CaptchaType = Literal["slider", "click"]
type CaptchaScene = Literal["login"]
type JSONData = dict[str, Any] | list[Any] | str | int | float | bool | None


# ---------------------------------------------------------------------------
# TypedDict models
# ---------------------------------------------------------------------------

class APIStatusEnvelope(TypedDict, total=False):
    status_code: int
    message: str


class SendSMSRequest(TypedDict):
    phone: str
    type: SMSKind
    scene: int


class SendSMSResponse(APIStatusEnvelope, total=False):
    data: JSONData


class LoginWithSMSRequest(TypedDict):
    phone: str
    code: str
    device_id: str
    login_type: LoginKind
    force_new_account: bool
    restore_confirm: bool


class LoginWithSMSData(TypedDict, total=False):
    token: str
    expire_time: str
    session_key: str
    openid: str


class LoginWithSMSResponse(APIStatusEnvelope, total=False):
    data: LoginWithSMSData


class SharedKeyResponse(TypedDict, total=False):
    session_id: int | str
    socketKey: str
    socketUrl: str


class CaptchaClientInfo(TypedDict, total=False):
    user_agent: str
    screen: str
    language: str


class CaptchaGenerateRequest(TypedDict):
    scene: CaptchaScene
    device_id: str
    login_key: str
    client_info: CaptchaClientInfo
    type: CaptchaType


class CaptchaGenerateData(TypedDict, total=False):
    type: CaptchaType
    tips: str
    background_img: str
    slider_img: str
    slider_y: NumberLike
    token: str


class CaptchaGenerateResponse(TypedDict, total=False):
    code: int
    message: str
    data: CaptchaGenerateData


class CaptchaPosition(TypedDict):
    x: NumberLike
    y: NumberLike


class CaptchaTrackPoint(TypedDict):
    x: NumberLike
    y: NumberLike
    t: int


class CaptchaVerifyRequest(TypedDict):
    token: str
    position: CaptchaPosition
    track: list[CaptchaTrackPoint]
    device_id: str
    duration: int


class CaptchaGatewayValidateResult(TypedDict, total=False):
    code: int
    message: str


class CaptchaVerifyData(TypedDict, total=False):
    success: bool
    verify_token: str
    gateway_validated: bool
    gateway_response: CaptchaGatewayValidateResult | None


class CaptchaVerifyResponse(TypedDict, total=False):
    code: int
    message: str
    data: CaptchaVerifyData


class CaptchaValidateResponse(TypedDict, total=False):
    code: int
    status_code: int
    message: str
    data: dict[str, Any]


class SurroundingCarsQuery(TypedDict):
    latitude: float
    longitude: float


class SurroundingCarItem(TypedDict, total=False):
    number: str
    car_number: str
    carmodel_id: int
    latitude: NumberLike
    longitude: NumberLike


class NewSurroundingCarGroup(TypedDict, total=False):
    total: int
    cars: list[SurroundingCarItem]


class NewSurroundingCarsResponse(APIStatusEnvelope, total=False):
    data: dict[str, NewSurroundingCarGroup]


class SurroundingCarsResponse(APIStatusEnvelope, total=False):
    data: list[SurroundingCarItem]


class CarLocationData(TypedDict, total=False):
    latitude: NumberLike
    longitude: NumberLike


class CarLocationResponse(APIStatusEnvelope, total=False):
    data: CarLocationData


class WSCarLocationData(TypedDict):
    number: str
    longitude: float
    latitude: float


class WSCarLocationPayload(TypedDict):
    biz_id: int
    data: WSCarLocationData
    timeout: int


type SendSMSData = JSONData
type NewSurroundingCarsData = dict[str, NewSurroundingCarGroup]
type SurroundingCarsData = list[SurroundingCarItem]
type CaptchaValidateData = dict[str, Any] | None


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class SevenMAError(Exception):
    """Base error for this SDK."""


class APIHTTPError(SevenMAError):
    """Raised when the HTTP layer fails or returns non-2xx."""

    def __init__(
        self,
        message: str,
        *,
        http_status: int | None = None,
        payload: Any = None,
    ) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.payload = payload


class APIStatusError(SevenMAError):
    """Raised when ``status_code`` in API JSON payload is not expected."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        payload: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class UnauthorizedError(APIStatusError):
    """Raised when token is invalid or expired (401)."""


class CaptchaRequiredError(APIStatusError):
    """Raised when API returns anti-bot challenge status_code=40301."""


class RateLimitError(APIStatusError):
    """Raised when API signals rate limiting or temporary outage (429/600)."""


class InvalidTokenError(SevenMAError):
    """Raised when JWT format/payload is invalid."""


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def decode_jwt_payload(token: str) -> dict[str, Any]:
    """Decode JWT payload without signature verification."""
    parts = token.split(".")
    if len(parts) != 3:
        raise InvalidTokenError("Invalid JWT format: expected 3 segments")
    payload_b64 = parts[1]
    missing_padding = len(payload_b64) % 4
    if missing_padding:
        payload_b64 += "=" * (4 - missing_padding)
    try:
        payload_json = base64.urlsafe_b64decode(payload_b64).decode("utf-8")
        payload = json.loads(payload_json)
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidTokenError("Invalid JWT payload") from exc
    if not isinstance(payload, dict):
        raise InvalidTokenError("Invalid JWT payload: expected JSON object")
    return cast(dict[str, Any], payload)


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
        else:
            out.append(ch)
    return "".join(out)


# ---------------------------------------------------------------------------
# WebSocket biz IDs
# ---------------------------------------------------------------------------

WS_BIZ_IDS: dict[str, int] = {
    "car_location": 3006,
}


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class SevenMaClient:
    """Async client for 7ma auth / location / map endpoints (curl_cffi)."""

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
        user_agent: str = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 "
            "MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Mac "
            "MacWechat/WMPF MacWechat/3.8.7(0x13080712) "
            "UnifiedPCMacWechat(0xf2641721) XWEB/18788"
        ),
    ):
        self.base_url = base_url.rstrip("/")
        self.auth_base_url = auth_base_url.rstrip("/")
        self.timeout = timeout

        self._owns_session = session is None
        self.session = session or AsyncSession()
        self._last_captcha_login_key: str | None = None

        self.token: str | None = token
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

    # -- token helpers -------------------------------------------------------

    def set_token(self, token: str) -> None:
        payload = decode_jwt_payload(token)
        exp_raw = payload.get("exp")
        exp_seconds: float | None = None
        if isinstance(exp_raw, int | float) and not isinstance(exp_raw, bool):
            exp_seconds = float(exp_raw)
        elif isinstance(exp_raw, str):
            try:
                exp_seconds = float(exp_raw.strip())
            except ValueError:
                exp_seconds = None
        self.token = token
        self.user_id = payload.get("user_id")
        self.phone_number = payload.get("phone")
        self.token_expire_time_ms = (
            int(exp_seconds * 1000)
            if exp_seconds is not None and exp_seconds > 0
            else None
        )
        self.username = payload.get("username")
        self.nickname = payload.get("nickname")
        self.school_name = payload.get("school_name")

    def clear_token(self) -> None:
        self.token = None
        self.token_expire_time_ms = None
        self.user_id = None
        self.phone_number = None
        self.username = None
        self.nickname = None
        self.school_name = None
        self.genielamp_h_session = None

    def is_token_expired(self, *, now_ms: int | None = None, leeway_ms: int = 0) -> bool:
        if not self.token:
            return True
        if self.token_expire_time_ms is None:
            return False
        current = now_ms if now_ms is not None else int(datetime.now().timestamp() * 1000)
        return current + leeway_ms >= self.token_expire_time_ms

    # -- header builders -----------------------------------------------------

    @property
    def headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "phone-model": self.phone_model,
            "xweb_xhr": "1",
            "phone-system": self.phone_system,
            "phone-brand": self.phone_brand,
            "client": self.client,
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
        headers = self.headers.copy()
        if self.token:
            headers["authorization"] = f"Bearer {self.token}"
        if self.user_id is not None:
            headers["u-user-id"] = str(self.user_id)
        return headers

    # -- lifecycle -----------------------------------------------------------

    async def close(self) -> None:
        if self._owns_session:
            await self.session.close()

    async def __aenter__(self) -> "SevenMaClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    # -- generic request helper (with structured error handling) --------------

    async def _request(
        self,
        method: HttpMethod,
        path: str,
        *,
        service: ServiceName = "api",
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
        extra_headers: Mapping[str, str] | None = None,
        allowed_status_codes: Iterable[int] | None = (200,),
        timeout: float | None = None,
        auth: bool = True,
    ) -> JSONData:
        url = self._build_url(service, path)
        request_headers = self.auth_headers if auth else self.headers
        if extra_headers:
            request_headers.update(extra_headers)
        timeout_val = self.timeout if timeout is None else timeout

        try:
            resp = await self.session.request(  # type: ignore[reportUnknownMemberType]
                method=method,
                url=url,
                params=dict(params) if params else None,
                json=dict(json_body) if json_body else None,
                headers=request_headers,
                timeout=timeout_val,
            )
        except Exception as exc:
            raise APIHTTPError(f"HTTP request failed: {exc}") from exc

        # update runtime headers from response
        if "x-trace-id" in resp.headers:
            self.x_trace_id = resp.headers["x-trace-id"]
        if "genielamp-h-session" in resp.headers:
            self.genielamp_h_session = resp.headers["genielamp-h-session"]

        payload: JSONData = self._decode_response_payload(resp)
        business_code = self._extract_status_code(payload)
        message = self._extract_message(payload)

        # 401 Unauthorized
        if resp.status_code == 401 or business_code == 401:
            self.clear_token()
            raise UnauthorizedError(
                message or "Unauthorized", status_code=401, payload=payload
            )

        # 40301 Captcha required
        if business_code == 40301:
            raise CaptchaRequiredError(
                message or "Captcha required", status_code=40301, payload=payload
            )

        # 429 / 600 Rate limit
        if resp.status_code == 429 or business_code in {429, 600}:
            code = 429 if resp.status_code == 429 else (business_code or 429)
            raise RateLimitError(
                message or "Rate limited", status_code=code, payload=payload
            )

        # other HTTP-level errors
        if resp.status_code >= 400:
            raise APIHTTPError(
                message or f"HTTP error {resp.status_code}",
                http_status=resp.status_code,
                payload=payload,
            )

        # business status_code validation
        if allowed_status_codes is not None and business_code is not None:
            allowed_set: set[int] = {int(c) for c in allowed_status_codes}
            if business_code not in allowed_set:
                raise APIStatusError(
                    message or f"Unexpected status_code={business_code}",
                    status_code=business_code,
                    payload=payload,
                )

        return payload

    async def _request_data[T = Any](
        self,
        method: HttpMethod,
        path: str,
        *,
        service: ServiceName = "api",
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
        extra_headers: Mapping[str, str] | None = None,
        allowed_status_codes: Iterable[int] | None = (200,),
        timeout: float | None = None,
        auth: bool = True,
    ) -> T:
        payload = await self._request(
            method,
            path,
            service=service,
            params=params,
            json_body=json_body,
            extra_headers=extra_headers,
            allowed_status_codes=allowed_status_codes,
            timeout=timeout,
            auth=auth,
        )
        return cast(T, self._extract_data(payload))

    # -- URL / response helpers ----------------------------------------------

    def _build_url(self, service: ServiceName, path: str) -> str:
        clean = path if path.startswith("/") else f"/{path}"
        if service == "api":
            return f"{self.base_url}{clean}"
        if service == "auth":
            return f"{self.auth_base_url}{clean}"
        if service == "absolute":
            return path
        raise ValueError(f"Unknown service '{service}', expected api/auth/absolute")

    @staticmethod
    def _decode_response_payload(resp: Any) -> JSONData:
        try:
            parsed: Any = resp.json()
        except (ValueError, TypeError):
            fallback: dict[str, Any] = {
                "http_status": getattr(resp, "status_code", None),
                "raw_text": getattr(resp, "text", ""),
            }
            return fallback

        # Normalize unknown JSON payloads into a known JSONData shape.
        if isinstance(parsed, dict):
            return cast(dict[str, Any], parsed)
        if isinstance(parsed, list):
            return cast(list[Any], parsed)
        if isinstance(parsed, str | int | float | bool) or parsed is None:
            return parsed
        return {"raw_payload": parsed}

    @staticmethod
    def _extract_status_code(payload: JSONData) -> int | None:
        if not isinstance(payload, dict):
            return None
        value = payload.get("status_code")
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return None

    @staticmethod
    def _extract_message(payload: JSONData) -> str:
        if isinstance(payload, dict):
            msg = payload.get("message")
            if isinstance(msg, str):
                return msg
        return ""

    @staticmethod
    def _extract_data(payload: JSONData) -> JSONData:
        if isinstance(payload, dict) and "data" in payload:
            return cast(JSONData, payload.get("data"))
        return payload

    @staticmethod
    def _parse_expire_time_ms(value: Any) -> int | None:
        if value is None or isinstance(value, bool):
            return None

        numeric_value: float | None = None
        if isinstance(value, int | float):
            numeric_value = float(value)
        elif isinstance(value, str):
            raw = value.strip()
            if not raw:
                return None

            try:
                numeric_value = float(raw)
            except ValueError:
                normalized = raw.replace("/", "-")
                iso_candidate = normalized.replace(" ", "T")
                if iso_candidate.endswith("Z"):
                    iso_candidate = f"{iso_candidate[:-1]}+00:00"
                dt: datetime | None = None
                for candidate in (iso_candidate, normalized):
                    try:
                        dt = datetime.fromisoformat(candidate)
                        break
                    except ValueError:
                        continue
                if dt is None:
                    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
                        try:
                            dt = datetime.strptime(normalized, fmt)
                            break
                        except ValueError:
                            continue
                if dt is None:
                    return None
                return int(dt.timestamp() * 1000)
        else:
            return None

        if numeric_value <= 0:
            return None
        if numeric_value >= 1_000_000_000_000:
            return int(numeric_value)
        return int(numeric_value * 1000)

    def _save_token_from_payload(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            return
        d = cast(dict[str, Any], payload)
        data = d.get("data")
        if not isinstance(data, dict):
            return
        dd = cast(dict[str, Any], data)
        token = dd.get("token")
        if isinstance(token, str) and token:
            self.set_token(token)
        expire_time_ms = self._parse_expire_time_ms(dd.get("expire_time"))
        if expire_time_ms is not None:
            self.token_expire_time_ms = expire_time_ms

    # -----------------------------------------------------------------------
    # Auth / login APIs
    # -----------------------------------------------------------------------

    async def send_sms(
        self,
        phone_number: str,
        *,
        scene: int = 1,
        sms_type: SMSKind = "login",
    ) -> SendSMSData:
        """发送短信验证码。"""
        payload: SendSMSRequest = {
            "phone": phone_number.replace(" ", ""),
            "type": sms_type,
            "scene": scene,
        }
        return await self._request_data(
            "POST", "/sms/send",
            service="auth",
            json_body=payload,
            allowed_status_codes={200},
            auth=False,
        )

    async def login_with_sms(
        self,
        phone_number: str,
        code: str,
        device_id: str = "",
        *,
        force_new_account: bool = False,
        restore_confirm: bool = False,
    ) -> str:
        """短信验证码登录，返回 token。"""
        if not device_id:
            device_id = self.phone_model + "_not_openid"
        payload: LoginWithSMSRequest = {
            "phone": phone_number,
            "code": code,
            "device_id": device_id,
            "login_type": "sms_code",
            "force_new_account": force_new_account,
            "restore_confirm": restore_confirm,
        }
        resp = cast(
            LoginWithSMSResponse,
            await self._request(
                "POST", "/login",
                service="auth",
                json_body=payload,
                allowed_status_codes={200},
                auth=False,
            ),
        )
        self._save_token_from_payload(resp)
        token = self.token
        if not token:
            raise APIStatusError(
                f"Login response does not contain token: {resp}",
                payload=resp,
            )
        return token

    async def get_shared_key(self) -> SharedKeyResponse:
        """获取共享密钥。"""
        return await self._request_data(
            "GET",
            "/shared_key",
            service="auth",
        )

    # -----------------------------------------------------------------------
    # Captcha APIs (40301)
    # -----------------------------------------------------------------------

    async def captcha_generate(
        self,
        *,
        scene: CaptchaScene,
        device_id: str,
        login_key: str,
        client_info: CaptchaClientInfo,
        captcha_type: CaptchaType = "slider",
    ) -> CaptchaGenerateData:
        payload: CaptchaGenerateRequest = {
            "scene": scene,
            "device_id": device_id,
            "login_key": login_key,
            "client_info": client_info,
            "type": captcha_type,
        }
        self._last_captcha_login_key = login_key
        return await self._request_data(
            "POST", "/captcha/polaris/captcha/generate",
            service="auth",
            json_body=payload,
            allowed_status_codes=None,
        )

    async def captcha_verify(
        self,
        *,
        token: str,
        position: CaptchaPosition,
        track: list[CaptchaTrackPoint],
        device_id: str,
        duration: int,
        login_key: str | None = None,
    ) -> CaptchaVerifyData:
        """校验验证码；有 login_key 时会自动补充网关 validate 结果。"""
        payload: CaptchaVerifyRequest = {
            "token": token,
            "position": position,
            "track": track,
            "device_id": device_id,
            "duration": duration,
        }
        verify_data_raw = await self._request_data(
            "POST",
            "/captcha/polaris/captcha/verify",
            service="auth",
            json_body=payload,
            allowed_status_codes=None,
        )
        if not isinstance(verify_data_raw, dict):
            raise APIStatusError(
                "Captcha verify response data is not an object",
                payload=verify_data_raw,
            )
        verify_data = cast(CaptchaVerifyData, verify_data_raw)

        key_for_validate = login_key or self._last_captcha_login_key
        verify_token = verify_data.get("verify_token")
        verify_success = bool(verify_data.get("success"))
        if not (verify_success and isinstance(verify_token, str) and verify_token):
            verify_data.setdefault("gateway_validated", False)
            verify_data.setdefault("gateway_response", None)
            return verify_data
        if not key_for_validate:
            verify_data["gateway_validated"] = False
            verify_data["gateway_response"] = {
                "code": -1,
                "message": "missing_login_key",
            }
            return verify_data

        gateway_response: CaptchaGatewayValidateResult | None = None
        gateway_validated = False
        try:
            validate_payload = await self._request(
                "GET",
                "/captcha/validate",
                service="auth",
                params={"token": verify_token, "login_key": key_for_validate},
                allowed_status_codes=None,
            )
            if isinstance(validate_payload, dict):
                code_raw = validate_payload.get("code", validate_payload.get("status_code"))
                code: int | None = None
                if isinstance(code_raw, int) and not isinstance(code_raw, bool):
                    code = code_raw
                elif isinstance(code_raw, str):
                    try:
                        code = int(code_raw.strip())
                    except ValueError:
                        code = None
                message_raw = validate_payload.get("message")
                message = message_raw if isinstance(message_raw, str) else ""
                gateway_response = {
                    "code": code if code is not None else -1,
                    "message": message,
                }
                gateway_validated = code in {0, 200}
            else:
                gateway_response = {
                    "code": -1,
                    "message": "gateway_validate_unexpected_payload",
                }
        except Exception:
            gateway_response = {
                "code": -1,
                "message": "gateway_validate_error",
            }

        verify_data["gateway_validated"] = gateway_validated
        verify_data["gateway_response"] = gateway_response
        return verify_data

    async def captcha_validate(
        self, *, verify_token: str, login_key: str
    ) -> CaptchaValidateData:
        return await self._request_data(
            "GET", "/captcha/validate",
            service="auth",
            params={"token": verify_token, "login_key": login_key},
            allowed_status_codes=None,
        )

    # -----------------------------------------------------------------------
    # Location APIs
    # -----------------------------------------------------------------------

    async def get_new_surrounding_cars(
        self, *, latitude: float, longitude: float
    ) -> NewSurroundingCarsData:
        params: SurroundingCarsQuery = {"latitude": latitude, "longitude": longitude}
        return await self._request_data(
            "GET", "/new/surrounding/car",
            params=params,
        )

    async def get_surrounding_cars(
        self, *, latitude: float, longitude: float
    ) -> SurroundingCarsData:
        params: SurroundingCarsQuery = {"latitude": latitude, "longitude": longitude}
        return await self._request_data(
            "GET", "/surrounding/car",
            params=params,
        )

    async def get_car_location(
        self,
        *,
        car_number: str,
        longitude: float | None = None,
        latitude: float | None = None,
    ) -> CarLocationData:
        params: dict[str, Any] = {}
        if longitude is not None:
            params["longitude"] = longitude
        if latitude is not None:
            params["latitude"] = latitude
        return await self._request_data(
            "GET", f"/car/{car_number}/location",
            params=params or None,
        )


    # -----------------------------------------------------------------------
    # WebSocket payload builders
    # -----------------------------------------------------------------------

    @staticmethod
    def build_ws_car_location_payload(
        *,
        car_number: str,
        longitude: float,
        latitude: float,
        timeout: int = 20000,
    ) -> WSCarLocationPayload:
        return {
            "biz_id": WS_BIZ_IDS["car_location"],
            "data": {
                "number": car_number,
                "longitude": longitude,
                "latitude": latitude,
            },
            "timeout": timeout,
        }


    # -----------------------------------------------------------------------
    # Public generic request (escape hatch)
    # -----------------------------------------------------------------------

    async def request[T = Any](
        self,
        *,
        method: HttpMethod,
        path: str,
        service: ServiceName = "api",
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
        extra_headers: Mapping[str, str] | None = None,
        allowed_status_codes: Iterable[int] | None = (200,),
        timeout: float | None = None,
    ) -> T:
        """Public generic wrapper around ``_request`` for ad-hoc calls.

        Example:
            response: LoginWithSMSResponse = await client.request(
                method="POST",
                path="/login",
                service="auth",
                json_body={...},
            )
        """
        return cast(
            T,
            await self._request(
                method,
                path,
                service=service,
                params=params,
                json_body=json_body,
                extra_headers=extra_headers,
                allowed_status_codes=allowed_status_codes,
                timeout=timeout,
            ),
        )


# ---------------------------------------------------------------------------
# Quick demo
# ---------------------------------------------------------------------------

async def main() -> None:
    async with SevenMaClient() as client:
        # 1. 发送验证码
        phone_number = "13800000000"  # 替换为你要测试的手机号
        response = await client.send_sms(phone_number)
        print(response)
        # 2. 登录
        code = input("请输入验证码: ")
        token = await client.login_with_sms(phone_number, code)
        print(f"登录成功，token: {token}")
        print(
            f"用户ID: {client.user_id}, 手机号: {client.phone_number}, "
            f"昵称: {client.nickname}, 学校: {client.school_name}"
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
