---
name: aimux-database-migrations
description: AIMux SQLx/SQLite 数据库迁移规范。修改表、字段、类型、默认值、索引、约束或回填持久化数据时使用。
---

# AIMux SQLx 数据库迁移规范

## 何时新增 migration

以下变化必须新增 `src-tauri/migrations/<编号>_<说明>.sql`：

- 新增、删除或重命名表和字段；
- 修改字段类型、可空性、默认值、唯一约束、CHECK、外键或索引；
- 需要转换、回填或清理已有持久化数据。

普通 DAO/Service 增删改查、查询条件、排序和分页不需要 migration。

## 项目约束

- `0001_baseline.sql` 是 Rust 首个版本的当前完整表结构，已经发布后不得修改。
- `0002_placeholder.sql` 仅作为后续 migration 的占位，不回写基线。
- SQLx migration 元数据存于 `_sqlx_migrations`；历史 `alembic_version` 只作为兼容数据库中的遗留表保留，不再由 Rust 读取或维护。
- migration SQL 文件必须使用 LF 换行符；SQLx 会校验文件字节的 SHA-384，CRLF/LF 差异会导致已有用户数据库无法启动。`.gitattributes` 已固定 `src-tauri/migrations/*.sql` 为 `eol=lf`，不得移除。
- Rust 启动时执行 `sqlx::migrate!`，不使用启动时临时 `ALTER TABLE` 或隐式建表。
- migration 必须兼容 SQLite，并考虑已有用户数据库、WAL、空表和旧数据。

## 工作流程

1. 读取 `src-tauri/migrations/`，确认当前最大编号和已有表结构。
2. 更新 `src-tauri/src/model/`、`schema/`、DAO/Service，使代码目标结构与 migration 一致。
3. 新增一个递增编号的 SQL 文件，写清楚升级语句、默认值和数据回填。
4. 在临时 SQLite 副本上验证从基线到最新 migration 的升级，并验证旧数据不丢失。
5. 检查打包产物会包含 `src-tauri/migrations/`，再运行受影响的 Rust 测试。

## 安全和数据保护

- 修改或删除数据前先明确确认目标和范围；破坏性迁移必须提供可恢复的备份/回滚说明。
- 所有用户输入使用 SQLx 参数绑定，migration 中不要拼接外部输入。
- 不把 API 密钥、完整请求体或真实用户数据库提交到测试 fixture、日志或仓库。

## 验证

```powershell
cargo fmt --manifest-path src-tauri/Cargo.toml -- --check
cargo check --manifest-path src-tauri/Cargo.toml
cargo test --manifest-path src-tauri/Cargo.toml --lib
```

修改后不自动 `git commit` 或 `git push`，除非用户明确要求。
