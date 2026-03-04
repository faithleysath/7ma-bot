# SevenMA Python SDK 文档

基于 `curl-cffi` 的异步 Python SDK，封装了 7ma 的登录、验证码、车辆位置查询等接口。

## 1. 环境要求

- Python：`>=3.14`（见 `pyproject.toml`）
- 依赖：`curl-cffi>=0.14.0`

## 2. 安装

在项目根目录执行：

```bash
uv sync
```

或使用 `pip`：

```bash
pip install -e .
```

## 3. 快速开始

```python
import asyncio
from sevenma_sdk import SevenMaClient


async def run():
    async with SevenMaClient() as client:
        # 1) 发送短信验证码
        await client.send_sms("13800000000")

        # 2) 验证码登录（将 123456 替换为真实验证码）
        token = await client.login_with_sms("13800000000", "123456")
        print("token:", token)
        print("user_id:", client.user_id)

        # 3) 查询附近车辆
        cars = await client.get_surrounding_cars(latitude=31.2304, longitude=121.4737)
        print(cars)


asyncio.run(run())
```

## 4. 客户端初始化

`SevenMaClient(...)` 主要参数：

- `base_url`: 业务接口基础地址，默认 `https://newmapi.7mate.cn/api/v1`
- `auth_base_url`: 鉴权接口基础地址，默认 `https://newmapi.7mate.cn/auth`
- `timeout`: 请求超时秒数，默认 `15.0`
- `session`: 可注入自定义 `AsyncSession`
- `token`: 初始化时可直接传入 JWT
- `phone_model` / `phone_system` / `phone_brand` / `phone_system_version` / `client` / `x_app_id` / `app_version` / `user_agent`: 请求头相关字段

支持异步上下文管理：

```python
async with SevenMaClient() as client:
    ...
```

或手动关闭：

```python
client = SevenMaClient()
try:
    ...
finally:
    await client.close()
```

## 5. Token 管理

- `set_token(token: str) -> None`
  - 解析 JWT payload 并同步写入 `user_id`、`phone_number`、`username`、`nickname`、`school_name`、`token_expire_time_ms`
- `clear_token() -> None`
  - 清空 token 和用户相关状态
- `is_token_expired(now_ms: int | None = None, leeway_ms: int = 0) -> bool`
  - 判断 token 是否过期（支持预留 `leeway_ms`）

工具函数：

- `decode_jwt_payload(token: str) -> dict[str, Any]`
- `generate_trace_id() -> str`

## 6. API 一览

### 6.1 登录与鉴权

- `send_sms(phone_number: str, scene: int = 1, sms_type: SMSKind = "login") -> SendSMSData`
  - 发送短信验证码
  - 默认只接受业务状态码 `200`，`406` 会抛 `APIStatusError`
- `login_with_sms(phone_number: str, code: str, device_id: str = "", force_new_account: bool = False, restore_confirm: bool = False) -> str`
  - 短信验证码登录，成功返回 `token`
  - SDK 会自动调用 `set_token(...)`
- `get_shared_key() -> SharedKeyResponse`
  - 获取共享密钥

### 6.2 验证码挑战（40301）

- `captcha_generate(scene, device_id, login_key, client_info, captcha_type="slider") -> CaptchaGenerateData`
- `captcha_verify(token, position, track, device_id, duration) -> CaptchaVerifyData`
- `captcha_validate(verify_token, login_key) -> CaptchaValidateData`

说明：以上三个接口默认 `allowed_status_codes=None`，由调用方自行判断业务码与返回结构。

### 6.3 位置查询

- `get_new_surrounding_cars(latitude: float, longitude: float) -> NewSurroundingCarsData`
- `get_surrounding_cars(latitude: float, longitude: float) -> SurroundingCarsData`
- `get_car_location(car_number: str, longitude: float | None = None, latitude: float | None = None) -> CarLocationData`

### 6.4 WebSocket 负载构建

- `WS_BIZ_IDS["car_location"] == 3006`
- `SevenMaClient.build_ws_car_location_payload(car_number, longitude, latitude, timeout=20000) -> WSCarLocationPayload`

示例：

```python
payload = SevenMaClient.build_ws_car_location_payload(
    car_number="A12345",
    longitude=121.4737,
    latitude=31.2304,
)
```

### 6.5 通用请求出口

- `request[T = Any](method, path, service="api", params=None, json_body=None, extra_headers=None, allowed_status_codes=(200,), timeout=None) -> T`

适合 SDK 未封装的新接口临时调用。
注意：`request[T]` 返回的是接口原始响应体，不会自动提取 `data`。

- `service="api"` -> `base_url + path`
- `service="auth"` -> `auth_base_url + path`
- `service="absolute"` -> 直接使用 `path` 作为完整 URL

### 6.6 TypedDict 与泛型 request

SDK 已内置主要接口的类型定义（`TypedDict` + 类型别名），包括（节选）：

- `SendSMSRequest` / `SendSMSData`
- `LoginWithSMSRequest` / `LoginWithSMSResponse` / `LoginWithSMSData`
- `SharedKeyResponse`
- `CaptchaGenerateRequest` / `CaptchaGenerateData`
- `CaptchaVerifyRequest` / `CaptchaVerifyData`
- `NewSurroundingCarsData` / `SurroundingCarsData`
- `CarLocationData`
- `WSCarLocationPayload`

字符串字面量约束（节选）：

- `SMSKind = Literal["login"]`
- `LoginKind = Literal["sms_code"]`
- `CaptchaType = Literal["slider", "click"]`
- `CaptchaScene = Literal["login"]`
- `ServiceName = Literal["api", "auth", "absolute"]`

如果你要调用 SDK 尚未封装的新接口，可以利用泛型 `request[T]` 在调用点声明返回类型：

```python
from sevenma_sdk import SevenMaClient, LoginWithSMSResponse

async def demo(client: SevenMaClient, payload: dict):
    resp: LoginWithSMSResponse = await client.request(
        method="POST",
        path="/login",
        service="auth",
        json_body=payload,
        allowed_status_codes={200},
    )
    return resp
```

## 7. 异常处理

异常层次：

- `SevenMAError`
  - `APIHTTPError`：HTTP 失败或非 2xx（且未被更具体异常捕获）
  - `APIStatusError`：业务 `status_code` 非预期
    - `UnauthorizedError`：401，触发后会自动 `clear_token()`
    - `CaptchaRequiredError`：业务码 `40301`
    - `RateLimitError`：HTTP `429` 或业务码 `429/600`
  - `InvalidTokenError`：JWT 格式或 payload 非法

建议捕获方式：

```python
from sevenma_sdk import (
    SevenMaClient,
    UnauthorizedError,
    CaptchaRequiredError,
    RateLimitError,
    APIStatusError,
    APIHTTPError,
)

try:
    ...
except CaptchaRequiredError as e:
    # 进入验证码流程
    print(e.payload)
except UnauthorizedError:
    # 重新登录
    ...
except RateLimitError:
    # 退避重试
    ...
except APIStatusError as e:
    print("业务错误:", e.status_code, e.payload)
except APIHTTPError as e:
    print("HTTP错误:", e.http_status, e.payload)
```

## 8. 返回值约定

- SDK 主要 API 方法默认返回 `data` 字段（而不是完整响应体）
- `login_with_sms(...)` 返回 `str`（token）
- `request[T]` 返回原始响应体，默认 `T = Any`，推荐在调用处显式标注 `T`

## 9. 注意事项

- 该 SDK 为异步实现，必须在事件循环中调用。
- 请求头中的 `x-trace-id`、`genielamp-h-session` 会根据响应自动更新。
- `send_sms` 会对手机号做空格清理；`login_with_sms` 不会自动清理手机号格式。
