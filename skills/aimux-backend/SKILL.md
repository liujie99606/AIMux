---
name: aimux-backend
description: AIMux Rust 后端开发规范。修改 src-tauri/src 下的 controller、service、dao、model、schema、gateway、upstream、数据库访问或兼容 API 时使用。
---

# AIMux Rust 后端规范

## 技术和分层

- Rust stable、Tokio、Axum、Reqwest、Tracing、SQLx、SQLite。
- `controller/` 负责 HTTP 路由、请求解析、响应组装和状态码。
- `service/` 负责调度、监控、统计、设置和账号业务规则。
- `dao/` 只负责 SQLx 查询、分页、排序和持久化，不放业务决策。
- `model/` 是数据库实体；`schema/` 是 API 输入输出类型；`gateway/` 负责 OpenAI/Anthropic 兼容转发和 SSE。
- 上游请求统一经过 `upstream/`，代理、超时和错误转换不得散落在 controller 中。

## 业务约束

- 账号选择顺序必须保持：协议和模型匹配、启用状态、优先级降序、倍率升序、名称/稳定 ID 作为确定性兜底。
- 每次重试都重新选择当前可用账号；账号映射只改变已选账号发往上游的模型，不改变调度模型。
- 请求记录在请求开始时创建；流式请求结束或读取异常时更新最终状态，不能因为断流丢记录。
- OpenAI 和 Anthropic 请求原样转发，不改写提示词、消息、模型上下文或缓存相关字段。
- 所有数据库访问使用用户数据目录中的 `aimux.db`，稳定网关和开发网关共用同一数据库。

## 错误、日志和并发

- 使用项目错误类型和 `Result`，在 controller 层将错误转换为稳定的 JSON 错误响应。
- 使用 `tracing` 记录启动、请求、上游错误、流结束和数据库错误；请求日志不得默认打印 API 密钥、完整请求体或完整响应体。
- 共享状态通过 `Arc` 和 Tokio 同步原语管理；避免在异步路径中执行阻塞文件或数据库操作。
- 上游 HTTP 客户端必须遵守设置中的超时和代理；流式响应使用超时保护并确保资源释放。

## 数据库

- 表结构变更必须追加 `src-tauri/migrations/<编号>_<说明>.sql`，不修改已发布 migration，也不在启动时临时 `ALTER TABLE`。
- 普通 DAO/Service 查询、排序、分页不需要新增 migration。
- 列表分页在 SQL 层完成 `ORDER BY`、`LIMIT`、`OFFSET`；排序必须有稳定的唯一键兜底。
- 写入和更新使用参数绑定，禁止拼接用户输入 SQL。

## 验证

先运行影响范围内的检查；跨模块、共享生命周期或发布前再运行完整检查：

```powershell
cargo fmt --manifest-path src-tauri/Cargo.toml -- --check
cargo check --manifest-path src-tauri/Cargo.toml
cargo test --manifest-path src-tauri/Cargo.toml --lib
```

修改后不自动执行 `git commit` 或 `git push`，除非用户明确要求。
