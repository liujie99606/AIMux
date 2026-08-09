---
name: aimux-backend
description: AIMux 项目后端开发规范。涵盖 Python 3.13 + FastAPI + SQLModel + Pydantic 的分层架构、目录约定、数据模型、加密、配置与测试规范。在新增/修改 app/ 下的 controller、service、dao、models、schemas、utils 模块，或调整 API、数据库表、账号/模型/用量相关业务逻辑时使用。
agent_created: true
---

# AIMux 后端开发规范

AIMux 是本地桌面端的 OpenAI 与 Anthropic API 账号池。后端只保留账号管理、实时调度、协议原样转发和使用记录，不做协议转换。

## 技术栈

- Python 3.13（managed 解释器优先）
- FastAPI（API 路由与依赖注入）
- SQLModel + SQLAlchemy（ORM，SQLite 存储）
- Pydantic v2（请求/响应 schema 与校验）
- httpx（向上游转发请求）
- cryptography.Fernet（上游密钥加密，机器绑定密钥）
- pytest（测试）

## 分层架构（严格遵循）

请求流向：`controller → service → dao → models`，禁止跨层调用（如 controller 直接操作 dao/model 字段）。

| 层 | 目录 | 职责 | 禁止 |
|----|------|------|------|
| controller | `../../app/controller` | 路由、参数解析、调用 service、组装响应 | 直接写 SQL、操作加密 |
| service | `../../app/service` | 业务规则、字段映射、加密调用、调用 dao | 直接暴露加密密钥 |
| dao | `../../app/dao` | 持久化 CRUD、查询过滤、排序 | 含业务判断 |
| models | `../../app/models.py` | SQLModel 表定义、约束、索引 | 含业务方法 |
| schemas | `../../app/schemas.py` | Pydantic I/O 模型与校验 | 与表定义耦合 |
| utils | `../../app/utils` | 加密、转发、路径、SSE、自启动等纯工具 | 依赖业务层 |

## 目录结构

```
app/
├── main.py            # create_app()：建表、挂载路由、CORS、local_token 守卫
├── config.py          # Settings dataclass + JSON 配置 + AIMUX_* 环境变量覆盖
├── db.py              # 全局 engine、get_session 依赖、建表与默认数据播种
├── models.py          # SQLModel 表：Account / CatalogModel / UsageRecord
├── schemas.py         # Pydantic：*Create / *Update / *View / TestResult 等
├── controller/        # *_api.py（FastAPI router）+ dependencies.py
├── service/           # *_service.py + priority.py（优先级算法）
├── dao/               # *_dao.py（纯持久化）
└── utils/             # crypto / forwarders / paths / sse / autostart / resources / tokens
```

## 通用编码规范

- 每个文件首行 `from __future__ import annotations`，启用延迟注解求值。
- 全量类型注解；用 `str | None` 而非 `Optional[str]`（models.py 例外，沿用 `Optional` 兼容 SQLModel 字段）。
- 中文单行 docstring 说明函数意图；复杂逻辑用行内 `#` 注释。
- import 顺序：标准库 → 第三方 → 本项目（`app.xxx`），各组之间空行。
- 时间统一用 `app.models.utc_now()` 生成 UTC ISO 字符串（`%Y-%m-%dT%H:%M:%SZ`），不直接调 `datetime.now()`。
- 主键用 `str(uuid.uuid4())`，默认值用 `default_factory=lambda: ...`。

## 数据模型规范（models.py）

- 表类继承 `SQLModel, table=True`，显式 `__tablename__`。
- 约束放 `__table_args__`：`CheckConstraint`（枚举/范围）、`UniqueConstraint`、`Index`（命名 `idx_` / `uq_` / `ck_` 前缀 + 表名）。
- 枚举字段用 `str` + CheckConstraint（如 `type IN ('openai','anthropic')`），不建独立枚举表。
- 列表字段（`supported_models`、`tags`）以 JSON 字符串存 `Optional[str]`，读写时在 service/dao 层 `json.dumps/loads` 转换；空列表存 `None` 表示"不限"。
- 敏感字段用 `_encrypted` 后缀 + `bytes` 类型（如 `api_key_encrypted`），绝不存明文。

## Schema 规范（schemas.py）

- 命名三件套：`*Create`（创建入参）、`*Update`（更新入参，字段全 `Optional`）、`*View`（对外响应，不含密钥）。
- 用 `Literal` 定义受限枚举类型别名（`AccountType = Literal["openai", "anthropic"]`）复用。
- 校验用 `Field(min_length=..., ge=..., le=...)` + `@field_validator` 装饰器（`@classmethod`）。
- 更新场景用 `payload.model_fields_set` 判断"是否显式提供"，仅更新已提供字段。
- `base_url` 等字段用 validator `rstrip("/")` 规整尾斜杠。
- 响应视图绝不包含 `api_key` / `api_key_encrypted`；通过 service 的 `to_view()` 显式字段映射。

## Controller 规范（app/controller/）

- 每个 `*_api.py` 创建 `router = APIRouter(prefix="/api/<resource>", tags=[...])`。
- 兼容协议路由（openai_api / anthropic_api）不带 `/api` 前缀，按上游协议路径原样暴露（`/v1/...`）。
- 依赖注入：`session: Session = Depends(get_session)`、`settings: Settings = Depends(app_settings)`。
- 管理 API（accounts/models/usage/settings）挂载时加 `dependencies=[Depends(verify_local_token)]`；兼容转发路由不加（客户端自带上游凭证）。
- 路由函数优先 `async def`（转发上游用 `await`）；纯 DB 操作可同步。
- 业务异常用 `HTTPException(status_code=..., detail=...)`；资源不存在返 404。
- 列表接口支持 `offset`/`limit`，并对 limit 做 `min(limit, 200)` 上限钳制。
- 删除接口用 `status_code=204` 且无返回体。

## Service 规范（app/service/）

- `to_view(model)`：model → dict 转换，显式列出对外字段，JSON 字符串反序列化为列表，绝不输出密钥。
- 加密只在 service 层调用 `app.utils.crypto.encrypt_api_key` / `decrypt_api_key`。
- 测试结果记录：成功调 `record_test_success`（优先级 +3、清错误、记模型），失败调 `record_test_failure`（优先级 -1、存错误）；真实请求成功调 `record_request_success`（优先级 +1、清错误），失败调 `record_request_failure`（优先级 -1、存错误，绝不自动停用账号）。
- 优先级算法集中在 `../../app/service/priority.py`，范围保持 0–9。

## DAO 规范（app/dao/）

- 函数签名首位恒为 `session: Session`，返回模型对象或 `None`。
- `create`/`save` 内部 `session.add` + `commit` + `refresh`；`save` 额外刷新 `updated_at`。
- 查询用 `select(Model)` + `session.exec(statement).all()`；过滤条件动态拼 `where`。
- 排序在 Python 层用 `list.sort(key=...)`（便于组合多键，如 `(-priority, name.lower(), id)`）。
- 统计累加（`total_requests`/`total_tokens`）用独立函数 `mark_used`/`add_tokens`，空值短路。
- 硬删除用 `session.delete` + `commit`。

## 加密规范（app/utils/crypto.py）

- Fernet 密钥由机器稳定信息派生：`aimux:{system}:{node}:{mac}` → SHA256 → urlsafe_b64encode。
- 不落盘密钥文件；换机器后旧密文不可解（符合"机器绑定"设计）。
- 仅在向上游发起请求前 `decrypt_api_key`；其余场景只持有密文。

## 配置规范（app/config.py）

- `Settings` 为 `@dataclass(slots=True)`；默认值即文档。
- `load_settings()` 读 JSON 配置文件，再用 `AIMUX_*` 环境变量覆盖（bool 类型识别 `1/true/yes/on`）。
- `resolved_db_path` 属性：用户指定优先，否则落 `platformdirs` 用户数据目录。
- 数据目录：Windows `%APPDATA%\aimux`，macOS `~/Library/Application Support/aimux`。

## 数据库规范（app/db.py）

- 全局单例 `_engine`；`configure_database(path)` 创建引擎、建表、播种默认模型。
- SQLite `connect_args={"check_same_thread": False}` 以适配 FastAPI 线程模型。
- `get_session()` 为生成器依赖，请求结束自动关闭会话。
- 启动自动 `SQLModel.metadata.create_all`，已有库升级时也会补建新表。

## 转发规范（app/utils/forwarders.py）

- 兼容接口仅转发 JSON 请求体；不做 OpenAI ↔ Anthropic 协议转换。
- 不模拟 multipart 文件上传；`OpenAI-Beta`、`Idempotency-Key`、`anthropic-beta` 等头按类型受限透传。
- 上游认证头始终由本地账号配置注入，不透传客户端凭证。
- 每次客户端请求最多尝试 `request_retry_attempts` 次（默认 10）；每次失败都按最新优先级重新选账号，不排除已失败账号。
- 每次上游尝试都单独写入 `UsageRecord`，同一客户端请求共享 `trace_id`，并用 `attempts` 记录该尝试序号；失败重试不能只保留最终结果。
- 测试账号：`max_tokens=1` + `"ping"`，endpoint 按类型选 `/v1/messages` 或 `/v1/chat/completions`。

## 测试规范（tests/）

- `pytest`；UI 测试首行 `os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")`。
- 用 FastAPI `TestClient`；测试数据通过 API 真实写入临时库。
- 命名 `test_<被测行为>_<关键约束>()`，断言聚焦行为而非实现细节。
- 默认只运行与本次改动影响范围匹配的测试，避免每次小改动都执行全量测试。例如：账号调度改动运行对应的账号/调度测试，API 或 Schema 改动运行对应的 API 测试，监控改动运行监控测试，纯工具改动运行该工具的直接测试及其调用方测试。
- 当改动跨越多个业务模块、修改共享模型/Schema/数据库结构、影响应用生命周期/全局配置/调度核心逻辑、聚焦测试无法覆盖完整影响范围，或准备发布/打包时，再运行全量测试：`./.venv/Scripts/python.exe -m pytest`。
- 无论采用哪种范围，都应在提交前记录实际执行的测试命令及结果；文档或注释改动且不涉及代码行为时可只执行 `git diff --check`。

## Git 提交规范

- 每次改动完成并测试通过后，**立即 git commit**，但**不推送**（不执行 `git push`）。
- 提交信息用中文简述本次改动；多文件改动可按逻辑拆成多个提交。
- 用 `/commit` 命令提交（自动处理安全协议与 pre-commit hooks），不要加 `--no-verify` 跳过钩子。
- 仓库保持"本地领先远程"状态，由用户决定何时批量推送。

## 改动自检清单

新增/修改后端代码时逐条核对：

1. 是否遵循 controller→service→dao→models 分层，无跨层？
2. 文件首行是否有 `from __future__ import annotations`？类型注解齐全？
3. 敏感字段是否加密存储，`to_view` 是否泄漏密钥？
4. 列表接口 limit 是否钳制到 200？删除是否 204？
5. 时间是否用 `utc_now()`？主键是否 UUID 字符串？
6. 新增表是否带 `__tablename__` 与命名一致的约束/索引？
7. Schema 是否 `*Create`/`*Update`/`*View` 三件套？更新是否用 `model_fields_set`？
8. 路由是否按需挂 `verify_local_token` 依赖？
9. 是否运行了与本次改动影响范围匹配的测试；若属于跨模块、共享基础设施或发布前改动，是否补充运行全量测试？
10. 是否已 `git commit`（仅提交，不推送）？
