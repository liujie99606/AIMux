# AIMux

AIMux 是本地桌面端的 OpenAI 与 Anthropic API 账号池。它只保留账号管理、实时调度、协议原样转发和使用记录。

## 启动

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m app
```

服务默认监听 `http://127.0.0.1:7788`。桌面端通过左侧菜单进入账号管理、使用记录和设置。两种协议不会相互转换，只会匹配同类型账号。

## 兼容接口

OpenAI 兼容接口：`/v1/models`、`/v1/chat/completions`、`/v1/completions`、`/v1/responses`、`/v1/embeddings`、`/v1/moderations`、`/v1/images/generations`、`/v1/audio/speech`、`/v1/rerank`，以及 Responses 的 `cancel`、`compact` 操作。

Anthropic 兼容接口：`/v1/messages`、`/v1/messages/count_tokens`、`/v1/messages/batches`、旧版 `/v1/complete`，模型目录为 `/v1/anthropic/models`。账号中显式填写的支持模型会出现在模型目录中。

兼容接口仅转发 JSON 请求体；不执行 OpenAI 与 Anthropic 之间的协议转换，也不模拟 multipart 文件上传。`OpenAI-Beta`、`Idempotency-Key`、`anthropic-beta` 等协议头会按类型受限透传，上游认证头始终由本地账号配置注入。

如果端口已被另一个 AIMux 实例占用，第二次启动会提示已有实例正在运行，不会再显示未处理异常。需要同时运行多个实例时，请先在设置中修改端口。

数据目录由 `platformdirs` 获取：Windows 位于 `%APPDATA%\aimux`，macOS 位于 `~/Library/Application Support/aimux`。数据库和配置都在这个目录中；上游密钥使用机器绑定的 Fernet 密钥加密保存。

启动 API 时会自动创建 `accounts`、`usage_records` 及索引。需要手动初始化空 SQLite 数据库时，可执行 [scripts/schema.sql](scripts/schema.sql)。

## 测试与打包

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe scripts\build.py
```

打包脚本会自动生成 `assets/icons/aimux.png`、`aimux.ico`、`aimux.icns`，并根据当前平台选择 Windows 或 macOS 图标。单独更新图标可运行 ` .\.venv\Scripts\python.exe scripts\generate_icon.py`。
