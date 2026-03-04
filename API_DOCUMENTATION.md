# SevenMA SDK API 文档

## 目录

- [概述](#概述)
- [初始化](#初始化)
- [认证与登录 API](#认证与登录-api)
- [验证码 API](#验证码-api)
- [车辆与位置 API](#车辆与位置-api)
- [地图与围栏 API](#地图与围栏-api)
- [WebSocket 负载构建器](#websocket-负载构建器)
- [异常处理](#异常处理)
- [实用工具](#实用工具)

---

## 概述

SevenMA SDK 是一个异步 Python SDK，用于与 7mate 共享单车平台的 API 进行交互。基于 `curl_cffi` 实现，提供了完整的认证、车辆查询、地图围栏等功能。

### 特性

- ✅ 完全异步 (asyncio)
- ✅ 自动 token 管理和过期检测
- ✅ 结构化异常处理
- ✅ 支持短信验证码登录
- ✅ 车辆位置和详情查询
- ✅ 地图围栏和停车区域查询
- ✅ WebSocket 消息构建

---

## 初始化

### SevenMaClient

```python
from sevenma_sdk import SevenMaClient

client = SevenMaClient(
    base_url="https://newmapi.7mate.cn/api/v1",
    auth_base_url="https://newmapi.7mate.cn/auth",
    timeout=15.0,
    token=None,  # 可选：已有的 token
    phone_model="Mac14,15",
    phone_system="Android",
    phone_brand="apple",
    phone_system_version="Mac OS X 15.7.4 arm64",
    client="Wechat_MiniAPP",
    x_app_id="default",
    app_version="1.3.165",
    user_agent="..."
)
```

#### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `base_url` | str | `https://newmapi.7mate.cn/api/v1` | API 基础 URL |
| `auth_base_url` | str | `https://newmapi.7mate.cn/auth` | 认证 API 基础 URL |
| `timeout` | float | `15.0` | 请求超时时间（秒） |
| `token` | str \| None | `None` | 已有的 JWT token |
| `phone_model` | str | `Mac14,15` | 手机型号 |
| `phone_system` | str | `Android` | 手机系统 |
| `phone_brand` | str | `apple` | 手机品牌 |
| `phone_system_version` | str | `Mac OS X 15.7.4 arm64` | 系统版本 |
| `client` | str | `Wechat_MiniAPP` | 客户端类型 |
| `x_app_id` | str | `default` | 应用 ID |
| `app_version` | str | `1.3.165` | 应用版本 |
| `user_agent` | str | ... | User-Agent 字符串 |

#### 使用上下文管理器

```python
async with SevenMaClient() as client:
    # 使用 client 进行 API 调用
    response = await client.get_surrounding_cars(
        latitude=39.9042,
        longitude=116.4074
    )
```

---

## 认证与登录 API

### send_sms

发送短信验证码到指定手机号。

```python
await client.send_sms(
    phone_number: str,
    scene: int = 1,
    sms_type: str = "login"
) -> Any
```

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `phone_number` | str | ✅ | 手机号码 |
| `scene` | int | ❌ | 场景 ID（默认: 1） |
| `sms_type` | str | ❌ | 短信类型（默认: "login"） |

#### 返回值

返回 API 响应的 JSON 数据。

#### 示例

```python
response = await client.send_sms("13800138000")
# 响应示例: {"status_code": 200, "message": "发送成功"}
```

---

### login_with_sms

使用短信验证码登录，返回 JWT token。

```python
await client.login_with_sms(
    phone_number: str,
    code: str,
    device_id: str = "",
    force_new_account: bool = False,
    restore_confirm: bool = False
) -> str
```

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `phone_number` | str | ✅ | 手机号码 |
| `code` | str | ✅ | 短信验证码 |
| `device_id` | str | ❌ | 设备 ID（默认自动生成） |
| `force_new_account` | bool | ❌ | 强制创建新账户 |
| `restore_confirm` | bool | ❌ | 恢复确认 |

#### 返回值

返回 JWT token 字符串。登录成功后，token 会自动保存到 `client.token`，并解析出用户信息：

- `client.user_id`: 用户 ID
- `client.phone_number`: 手机号
- `client.username`: 用户名
- `client.nickname`: 昵称
- `client.school_name`: 学校名称
- `client.token_expire_time_ms`: token 过期时间（毫秒时间戳）

#### 示例

```python
token = await client.login_with_sms("13800138000", "123456")
print(f"登录成功！用户ID: {client.user_id}, 昵称: {client.nickname}")
```

---

### get_shared_key

获取共享密钥（需要认证）。

```python
await client.get_shared_key() -> Any
```

#### 返回值

返回包含共享密钥的 JSON 数据。

#### 示例

```python
key_info = await client.get_shared_key()
```

---

## 验证码 API

当 API 返回 `status_code=40301` 时，需要完成人机验证。

### captcha_generate

生成验证码挑战。

```python
await client.captcha_generate(
    scene: str,
    device_id: str,
    login_key: str,
    client_info: Mapping[str, Any],
    captcha_type: str = "slider"
) -> Any
```

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `scene` | str | ✅ | 验证场景 |
| `device_id` | str | ✅ | 设备 ID |
| `login_key` | str | ✅ | 登录密钥 |
| `client_info` | Mapping | ✅ | 客户端信息 |
| `captcha_type` | str | ❌ | 验证码类型（默认: "slider"） |

---

### captcha_verify

验证用户完成的验证码操作。

```python
await client.captcha_verify(
    token: str,
    position: Mapping[str, Any],
    track: list[Mapping[str, Any]],
    device_id: str,
    duration: int
) -> Any
```

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `token` | str | ✅ | 验证码 token |
| `position` | Mapping | ✅ | 滑块位置信息 |
| `track` | list | ✅ | 滑动轨迹 |
| `device_id` | str | ✅ | 设备 ID |
| `duration` | int | ✅ | 完成时长（毫秒） |

---

### captcha_validate

验证验证码令牌。

```python
await client.captcha_validate(
    verify_token: str,
    login_key: str
) -> Any
```

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `verify_token` | str | ✅ | 验证令牌 |
| `login_key` | str | ✅ | 登录密钥 |

---

## 车辆与位置 API

### get_surrounding_cars

获取指定坐标周围的车辆列表。

```python
await client.get_surrounding_cars(
    latitude: float,
    longitude: float
) -> Any
```

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `latitude` | float | ✅ | 纬度 |
| `longitude` | float | ✅ | 经度 |

#### 示例

```python
cars = await client.get_surrounding_cars(
    latitude=39.9042,
    longitude=116.4074
)
```

---

### get_new_surrounding_cars

获取指定坐标周围的新车辆列表（新版接口）。

```python
await client.get_new_surrounding_cars(
    latitude: float,
    longitude: float
) -> Any
```

#### 参数

同 `get_surrounding_cars`。

---

### get_car_location

获取指定车辆的位置信息。

```python
await client.get_car_location(
    car_number: str,
    longitude: float | None = None,
    latitude: float | None = None
) -> Any
```

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `car_number` | str | ✅ | 车辆编号 |
| `longitude` | float | ❌ | 用户当前经度 |
| `latitude` | float | ❌ | 用户当前纬度 |

#### 示例

```python
location = await client.get_car_location(
    car_number="BJ12345",
    longitude=116.4074,
    latitude=39.9042
)
```

---

### get_car_detail

获取车辆详细信息。

```python
await client.get_car_detail(car_number: str) -> Any
```

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `car_number` | str | ✅ | 车辆编号 |

#### 示例

```python
detail = await client.get_car_detail(car_number="BJ12345")
```

---

### get_car_lock_status

获取车辆锁状态。

```python
await client.get_car_lock_status(car_number: str) -> Any
```

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `car_number` | str | ✅ | 车辆编号 |

---

### get_user_car_authority

获取用户的车辆权限信息。

```python
await client.get_user_car_authority() -> Any
```

#### 返回值

返回用户可用的车辆权限列表。

---

## 地图与围栏 API

### get_parking_ranges

获取指定位置的停车范围信息。

```python
await client.get_parking_ranges(
    longitude: float,
    latitude: float
) -> Any
```

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `longitude` | float | ✅ | 经度 |
| `latitude` | float | ✅ | 纬度 |

---

### get_near_operation_area

获取附近的运营区域。

```python
await client.get_near_operation_area(
    longitude: float,
    latitude: float
) -> Any
```

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `longitude` | float | ✅ | 经度 |
| `latitude` | float | ✅ | 纬度 |

---

### get_at_operation_areas

获取当前位置所在的运营区域。

```python
await client.get_at_operation_areas(
    latitude: float,
    longitude: float
) -> Any
```

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `latitude` | float | ✅ | 纬度 |
| `longitude` | float | ✅ | 经度 |

---

### get_parking_detail

获取停车场详情。

```python
await client.get_parking_detail(
    parking_id: int,
    longitude: float,
    latitude: float
) -> Any
```

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `parking_id` | int | ✅ | 停车场 ID |
| `longitude` | float | ✅ | 用户当前经度 |
| `latitude` | float | ✅ | 用户当前纬度 |

---

### get_bicycling_route

获取骑行路线规划。

```python
await client.get_bicycling_route(
    origin_longitude: float,
    origin_latitude: float,
    destination_longitude: float,
    destination_latitude: float
) -> Any
```

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `origin_longitude` | float | ✅ | 起点经度 |
| `origin_latitude` | float | ✅ | 起点纬度 |
| `destination_longitude` | float | ✅ | 终点经度 |
| `destination_latitude` | float | ✅ | 终点纬度 |

#### 示例

```python
route = await client.get_bicycling_route(
    origin_longitude=116.4074,
    origin_latitude=39.9042,
    destination_longitude=116.3913,
    destination_latitude=39.9069
)
```

---

### in_fences

检查指定坐标点是否在围栏内。

```python
await client.in_fences(
    points: str,
    back_type: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    lock_status: str | None = None,
    action_type: str | None = None,
    yunjia_in_fence: int | None = None
) -> Any
```

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `points` | str | ✅ | 坐标点字符串 |
| `back_type` | str | ❌ | 返回类型 |
| `latitude` | float | ❌ | 纬度 |
| `longitude` | float | ❌ | 经度 |
| `lock_status` | str | ❌ | 锁状态 |
| `action_type` | str | ❌ | 动作类型 |
| `yunjia_in_fence` | int | ❌ | 云驾围栏标识 |

---

## WebSocket 负载构建器

SDK 提供了静态方法来构建 WebSocket 消息负载。

### build_ws_car_location_payload

构建车辆位置 WebSocket 消息负载。

```python
SevenMaClient.build_ws_car_location_payload(
    car_number: str,
    longitude: float,
    latitude: float,
    timeout: int = 20000
) -> dict[str, Any]
```

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `car_number` | str | ✅ | 车辆编号 |
| `longitude` | float | ✅ | 经度 |
| `latitude` | float | ✅ | 纬度 |
| `timeout` | int | ❌ | 超时时间（毫秒，默认 20000） |

#### 返回值

```python
{
    "biz_id": 3006,
    "data": {
        "number": "BJ12345",
        "longitude": 116.4074,
        "latitude": 39.9042
    },
    "timeout": 20000
}
```

---

### build_ws_in_fences_payload

构建围栏检查 WebSocket 消息负载。

```python
SevenMaClient.build_ws_in_fences_payload(
    points: str,
    timeout: int = 20000,
    back_type: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    lock_status: str | None = None,
    action_type: str | None = None,
    yunjia_in_fence: int | None = None
) -> dict[str, Any]
```

#### 参数

参数说明同 `in_fences` 方法。

#### 返回值

```python
{
    "biz_id": 3004,
    "data": {
        "points": "116.4074,39.9042",
        # ... 其他字段
    },
    "timeout": 20000
}
```

---

### build_ws_order_state_payload

构建订单状态 WebSocket 消息负载。

```python
SevenMaClient.build_ws_order_state_payload(
    timeout: int = 20000,
    data: Mapping[str, Any] | None = None
) -> dict[str, Any]
```

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `timeout` | int | ❌ | 超时时间（毫秒，默认 20000） |
| `data` | Mapping | ❌ | 自定义数据 |

---

## 异常处理

SDK 定义了以下异常类型：

### SevenMAError

所有 SDK 异常的基类。

---

### APIHTTPError

HTTP 层错误或非 2xx 响应。

#### 属性

- `http_status`: HTTP 状态码
- `payload`: 响应负载

#### 示例

```python
try:
    await client.get_car_detail(car_number="INVALID")
except APIHTTPError as e:
    print(f"HTTP 错误: {e.http_status} - {e}")
```

---

### APIStatusError

业务状态码不符合预期。

#### 属性

- `status_code`: 业务状态码
- `payload`: 响应负载

---

### UnauthorizedError

认证失败或 token 过期（401）。继承自 `APIStatusError`。

#### 处理方式

```python
try:
    await client.get_user_car_authority()
except UnauthorizedError:
    # 重新登录
    token = await client.login_with_sms(phone, code)
```

---

### CaptchaRequiredError

需要完成人机验证（status_code=40301）。继承自 `APIStatusError`。

#### 处理方式

```python
try:
    await client.send_sms(phone)
except CaptchaRequiredError as e:
    # 需要完成验证码流程
    login_key = e.payload.get("data", {}).get("login_key")
    # ... 调用 captcha_generate/verify/validate
```

---

### RateLimitError

API 限流或临时不可用（429/600）。继承自 `APIStatusError`。

---

## 实用工具

### Token 管理

#### set_token

手动设置 token 并解析用户信息。

```python
client.set_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
```

#### clear_token

清除当前 token。

```python
client.clear_token()
```

#### is_token_expired

检查 token 是否过期。

```python
if client.is_token_expired(leeway_ms=60000):  # 提前 60 秒视为过期
    # 重新登录
    pass
```

#### 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `now_ms` | int \| None | 当前时间（毫秒时间戳），默认当前时间 |
| `leeway_ms` | int | 提前时间（毫秒），默认 0 |

---

### 辅助函数

#### decode_jwt_payload

解码 JWT token 的 payload（不验证签名）。

```python
from sevenma_sdk import decode_jwt_payload

payload = decode_jwt_payload(token)
print(payload["user_id"])
```

#### generate_trace_id

生成跟踪 ID（UUID v4 格式）。

```python
from sevenma_sdk import generate_trace_id

trace_id = generate_trace_id()
# 示例: "a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7g8"
```

---

## 完整示例

### 基本登录流程

```python
import asyncio
from sevenma_sdk import SevenMaClient, CaptchaRequiredError

async def login_example():
    async with SevenMaClient() as client:
        phone = "13800138000"
        
        # 1. 发送验证码
        try:
            await client.send_sms(phone)
            print("验证码已发送")
        except CaptchaRequiredError:
            print("需要完成人机验证")
            # 在这里处理验证码逻辑
            return
        
        # 2. 输入验证码并登录
        code = input("请输入验证码: ")
        token = await client.login_with_sms(phone, code)
        
        print(f"登录成功！")
        print(f"用户ID: {client.user_id}")
        print(f"昵称: {client.nickname}")
        print(f"学校: {client.school_name}")
        
        # 3. 查询周围车辆
        cars = await client.get_surrounding_cars(
            latitude=39.9042,
            longitude=116.4074
        )
        print(f"周围车辆: {cars}")

asyncio.run(login_example())
```

---

### 查询车辆信息

```python
async def query_car_info(client: SevenMaClient, car_number: str):
    """查询指定车辆的完整信息"""
    
    # 获取车辆详情
    detail = await client.get_car_detail(car_number=car_number)
    print(f"车辆详情: {detail}")
    
    # 获取车辆位置
    location = await client.get_car_location(
        car_number=car_number,
        longitude=116.4074,
        latitude=39.9042
    )
    print(f"车辆位置: {location}")
    
    # 获取锁状态
    lock_status = await client.get_car_lock_status(car_number=car_number)
    print(f"锁状态: {lock_status}")
```

---

### 路线规划

```python
async def plan_route(client: SevenMaClient):
    """规划骑行路线"""
    route = await client.get_bicycling_route(
        origin_longitude=116.4074,
        origin_latitude=39.9042,
        destination_longitude=116.3913,
        destination_latitude=39.9069
    )
    
    # 处理路线信息
    print(f"路线规划: {route}")
```

---

### Token 持久化

```python
import asyncio
import json
from sevenma_sdk import SevenMaClient

async def login_with_persistence():
    """带 token 持久化的登录示例"""
    
    # 尝试从文件加载 token
    try:
        with open("token.json", "r") as f:
            data = json.load(f)
            token = data.get("token")
    except FileNotFoundError:
        token = None
    
    async with SevenMaClient(token=token) as client:
        # 检查 token 是否过期
        if client.is_token_expired(leeway_ms=300000):  # 提前 5 分钟
            print("Token 已过期，重新登录...")
            phone = input("手机号: ")
            await client.send_sms(phone)
            code = input("验证码: ")
            token = await client.login_with_sms(phone, code)
            
            # 保存新 token
            with open("token.json", "w") as f:
                json.dump({"token": token}, f)
        
        # 使用 client 进行 API 调用
        cars = await client.get_surrounding_cars(
            latitude=39.9042,
            longitude=116.4074
        )
        print(f"找到 {len(cars.get('data', []))} 辆车")

asyncio.run(login_with_persistence())
```

---

## 注意事项

1. **异步编程**: 所有 API 方法都是异步的，必须在 `async` 函数中使用 `await` 调用。

2. **Token 管理**: 
   - token 会在登录后自动保存
   - 遇到 401 错误时会自动清除 token
   - 建议定期检查 `is_token_expired()` 并在需要时重新登录

3. **错误处理**: 
   - 始终捕获并处理特定的异常类型
   - 注意 `CaptchaRequiredError`，可能需要人工干预

4. **速率限制**: 
   - API 有速率限制，频繁请求可能触发 `RateLimitError`
   - 建议添加适当的延迟和重试逻辑

5. **坐标系统**: 
   - API 使用的坐标系需确认（可能是 GCJ-02 或 WGS-84）
   - 确保传入的经纬度坐标使用正确的坐标系

---

## 更新日志

### v1.0.0 (当前版本)
- ✅ 完整的认证和登录功能
- ✅ 车辆查询和位置 API
- ✅ 地图围栏和路线规划
- ✅ WebSocket 消息构建器
- ✅ 结构化异常处理
- ✅ Token 自动管理

---

## 许可证

请参考项目许可证文件。

---

## 技术支持

如有问题或建议，请提交 issue 或联系维护者。
