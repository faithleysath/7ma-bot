# 7ma-bot

`7ma-bot` 是一个围绕 **7MA 出行** 的研究型仓库，包含两部分内容：

1. `sevenma_sdk.py`：单文件异步 Python SDK（基于 `curl-cffi`），封装了短信登录、验证码、车辆定位等接口。
2. `7ma出行/`：微信小程序前端资源（编译后产物），可用于页面结构与接口行为分析。

## 目录结构

```text
.
├── sevenma_sdk.py            # 核心 SDK（异步）
├── main.py                   # 占位入口
├── pyproject.toml            # Python 项目配置
├── uv.lock
└── 7ma出行/                  # 小程序资源目录
    ├── app.js
    ├── app.json
    ├── app-config.json
    ├── common/
    └── pages/
```

## 环境要求

- Python `>=3.14`（与 `pyproject.toml` 一致）
- 依赖：`curl-cffi>=0.14.0`
- 可选：`uv`（推荐）
- 如需查看小程序页面：微信开发者工具

## 安装依赖

### 使用 uv（推荐）

```bash
uv sync
```

### 使用 venv + pip

```bash
python -m venv .venv
source .venv/bin/activate
pip install "curl-cffi>=0.14.0"
```

## SDK 快速开始

### 1) 获取附近车辆（无需登录）

```python
import asyncio
from sevenma_sdk import SevenMaClient

async def run():
    async with SevenMaClient() as client:
        cars = await client.get_new_surrounding_cars(
            latitude=32.200905,
            longitude=118.711972,
        )
        print(cars)

asyncio.run(run())
```

### 2) 短信验证码登录

```python
import asyncio
from sevenma_sdk import SevenMaClient

PHONE = "13800000000"  # 替换为真实手机号

async def run():
    async with SevenMaClient() as client:
        await client.send_sms(PHONE)
        code = input("请输入验证码: ").strip()
        token = await client.login_with_sms(PHONE, code)
        print("token:", token)
        print("user_id:", client.user_id)

asyncio.run(run())
```

### 3) 直接运行内置示例

```bash
python sevenma_sdk.py
```

说明：默认执行 `get_cars_demo()`；如需短信登录示例，可在文件底部切换到 `main()`。

## 已封装能力（`SevenMaClient`）

- 登录鉴权：
  - `send_sms`
  - `login_with_sms`
  - `get_shared_key`
- 40301 验证码流程：
  - `captcha_generate`
  - `captcha_verify`
  - `captcha_validate`
- 地图/车辆：
  - `get_new_surrounding_cars`
  - `get_car_location`
- 通用请求：
  - `request`（自定义 method/path/service）
- 工具函数：
  - `decode_jwt_payload`
  - `build_ws_car_location_payload`

## 异常类型

SDK 提供了结构化异常，便于调用方处理：

- `UnauthorizedError`：token 失效或未授权（401）
- `CaptchaRequiredError`：触发 40301 验证码
- `RateLimitError`：请求过快或限流（429/600）
- `APIStatusError`：业务状态码不符合预期
- `APIHTTPError`：HTTP 层异常

## 小程序资源说明（`7ma出行/`）

该目录包含微信小程序页面与编译后的公共脚本（如 `common/vendor.js`）。可用于：

- 页面结构与路由梳理
- 接口调用路径与参数分析
- 登录/验证码/骑行业务流程逆向

如需在微信开发者工具中打开：

1. 导入目录：`7ma出行/`
2. 选择测试 AppID（或你自己的 AppID）
3. 按需关闭域名校验（`project.private.config.json` 已设置 `urlCheck: false`）

## 注意事项

- 本仓库更适合学习、调试和接口研究，不保证线上接口长期稳定。
- 请勿在代码中提交真实手机号、验证码、token 等敏感信息。
- 若服务端接口字段变化，优先更新 `sevenma_sdk.py` 的 `TypedDict` 与状态码处理逻辑。
