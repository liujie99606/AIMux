# AIMux

AIMux 是本地桌面端的 OpenAI 与 Anthropic API 账号池。它只保留账号管理、实时调度、协议原样转发和使用记录。

## 启动

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m app
```

服务默认监听 `http://127.0.0.1:7788`。OpenAI 请求使用 `/v1/chat/completions`、`/v1/responses`；Anthropic 请求使用 `/v1/messages`。两种请求不会协议转换，只会匹配同类型账号。

如果端口已被另一个 AIMux 实例占用，第二次启动会提示已有实例正在运行，不会再显示未处理异常。需要同时运行多个实例时，请先在设置中修改端口。

数据目录由 `platformdirs` 获取：Windows 位于 `%APPDATA%\aimux`，macOS 位于 `~/Library/Application Support/aimux`。数据库和配置都在这个目录中；上游密钥使用机器绑定的 Fernet 密钥加密保存。

启动 API 时会自动创建 `accounts`、`usage_records` 及索引。需要手动初始化空 SQLite 数据库时，可执行 [scripts/schema.sql](scripts/schema.sql)。

## 测试与打包

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\python.exe scripts\build.py
```
