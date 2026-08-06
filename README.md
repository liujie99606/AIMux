# AIMux

AIMux 是本地桌面端的 OpenAI 与 Anthropic API 账号池。它只保留账号管理、实时调度、协议原样转发和使用记录。

## 为什么会有这个项目

市面上中转站层出不穷，但稳定性参差不齐：要么突然跑路，要么高峰期限流降速，单点依赖一个中转站风险很高。虽然 [CC Switch](https://github.com/farion1231/cc-switch) 这类工具能切换上游配置，但每次切换都要重启 Codex / Claude Code 等客户端，打断工作流，体验不够顺滑。

AIMux 解决的核心问题是**多账号路由**：把多个上游 Key（官方直连或中转站）统一录入本地账号池，客户端只需配置一次 `http://127.0.0.1:7788`，后续所有请求由 AIMux 按优先级和健康状态自动分配到可用账号。某个账号限流或报错时自动降级并重试下一个，无需手动切换、无需重启客户端。

设计原则：

- **只做路由，不做统计计费**：使用记录仅用于排查问题（耗时、状态码、错误信息），不统计 Token 费用、不生成账单
- **协议原样转发**：OpenAI 请求走 OpenAI 账号，Anthropic 请求走 Anthropic 账号，不做协议转换，保持上游行为一致
- **本地运行，数据不出机器**：所有配置和密钥加密存储在本地，不上报任何信息
- **故障自动降级**：请求失败自动降低该账号优先级并重试其他账号，测试通过后自动恢复

## 启动

### 一键启动

项目根目录提供了平台启动脚本，首次运行会自动创建虚拟环境并安装依赖，后续直接启动：

| 脚本 | 平台 | 用法 |
|------|------|------|
| `win_start.bat` | Windows | 双击运行，或终端执行 `.\win_start.bat` |
| `mac_start.sh` | macOS | 终端执行 `chmod +x mac_start.sh && ./mac_start.sh` |

两个脚本行为一致：检测到 `.venv` 不存在时自动创建虚拟环境并 `pip install -e ".[dev]"`，已存在则直接启动应用。

### 手动启动

如需手动控制环境，可逐步执行：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m app
```

服务默认监听 `http://127.0.0.1:7788`。桌面端通过左侧菜单进入账号管理、模型维护、使用记录和设置。两种协议不会相互转换，只会匹配同类型账号。

## 模型目录

数据库包含独立的 `models` 表（名称、类型、创建和更新时间）。每次启动会自动建表，并幂等补充默认模型：OpenAI 的 `gpt-5.5`、`gpt-5.5-pro`、`gpt-5.6`、`gpt-5.6-sol`、`gpt-5.6-terra`、`gpt-5.6-luna`，以及 Anthropic 的 `claude-opus-4-8`、`claude-sonnet-4-8`、`claude-haiku-4-8`。

在“模型维护”页可新增、编辑、删除模型。新增或编辑账号时，支持模型会随 OpenAI/Anthropic 类型切换为相应可多选列表；连接测试也会要求从同类型模型目录选择测试模型。批量测试需要选择相同类型的账号。

## 兼容接口

OpenAI 兼容接口：`/v1/models`、`/v1/chat/completions`、`/v1/completions`、`/v1/responses`、`/v1/embeddings`、`/v1/moderations`、`/v1/images/generations`、`/v1/audio/speech`、`/v1/rerank`，以及 Responses 的 `cancel`、`compact` 操作。

Anthropic 兼容接口：`/v1/messages`、`/v1/messages/count_tokens`、`/v1/messages/batches`、旧版 `/v1/complete`，模型目录为 `/v1/anthropic/models`。账号中显式填写的支持模型会出现在模型目录中。

兼容接口仅转发 JSON 请求体；不执行 OpenAI 与 Anthropic 之间的协议转换，也不模拟 multipart 文件上传。`OpenAI-Beta`、`Idempotency-Key`、`anthropic-beta` 等协议头会按类型受限透传，上游认证头始终由本地账号配置注入。

如果端口已被另一个 AIMux 实例占用，第二次启动会提示已有实例正在运行，不会再显示未处理异常。需要同时运行多个实例时，请先在设置中修改端口。

数据目录由 `platformdirs` 获取：Windows 位于 `%APPDATA%\aimux`，macOS 位于 `~/Library/Application Support/aimux`。数据库和配置都在这个目录中；上游密钥使用机器绑定的 Fernet 密钥加密保存。

启动 API 时会自动创建 `accounts`、`models`、`usage_records` 及索引。需要手动初始化空 SQLite 数据库时，可执行 [scripts/schema.sql](scripts/schema.sql)。

## 测试与打包

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe scripts\build.py
```

打包脚本会自动生成 `assets/icons/aimux.png`、`aimux.ico`、`aimux.icns`，并根据当前平台选择 Windows 或 macOS 图标。单独更新图标可运行 ` .\.venv\Scripts\python.exe scripts\generate_icon.py`。
