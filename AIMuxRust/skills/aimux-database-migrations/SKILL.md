---
name: aimux-database-migrations
description: AIMux Alembic 数据库迁移维护规范。修改 SQLModel 表结构、字段类型或可空性、数据库默认值、索引、唯一/CHECK/外键约束、表或字段命名，或需要转换/回填已有持久化数据时使用。普通 DAO/Service 增删改查、查询条件、排序、分页和业务逻辑调整不触发此 skill。
---

# AIMux 数据库迁移规范

同时遵守 `../aimux-backend/SKILL.md`，并以 `../../docs/plan/数据库迁移升级规划.md` 为兼容边界。

## 判断是否需要 migration

以下改动必须同步新增 Alembic revision：

- 新增、删除、重命名表或字段。
- 修改字段类型、长度、精度、NULL 属性或数据库默认值。
- 新增、删除或修改索引、主键、唯一、CHECK、外键约束。
- 修改数据库中已有值的格式、含义或存储方式，需要回填、清洗或转换数据。
- 任何导致 `SQLModel.metadata` 与当前 Alembic head schema 不一致的改动。

以下改动不创建 migration：

- DAO/Service 的普通增删改查逻辑。
- 查询条件、排序、分页、聚合或返回字段调整。
- 仅修改 Pydantic Schema、API 或 UI，且数据库结构和已有数据语义不变。
- 仅修改 Python 侧默认值，且不要求改变数据库默认值或已有记录。

无法确定时，比较变更前后的 SQLModel metadata；数据库 schema 或既有数据解释发生变化就必须迁移。

## Revision 规则

1. 先读取 `../../../migrations/versions`，确认唯一当前 head 和编号。
2. 从当前 head 追加 revision；使用连续编号和清晰名称，例如 `002_add_account_region.py`。
3. 正确设置 `revision` 和 `down_revision`，保持单线 revision 图，除非需求明确要求分支合并。
4. 使用 Alembic Python migration API；SQLite 改列、删列或改约束时使用 batch table rebuild。
5. migration 必须显式、确定且可审查。自动生成只能作为草稿，提交前人工核对 DDL、数据转换和索引。
6. 已提交或发布的 revision 不得修改、删除、重命名或重排，只能追加新 revision 修正。
7. 不在 migration 中写入 API 密钥、业务正文、机器路径或环境特定数据。
8. 默认模型等幂等业务初始化继续由 service 负责，不写死在 schema migration 中。
9. `../../../app/database_migrations.py` 只负责固定的 Alembic runner、revision 校验、备份和基线接管；后续新增字段、索引或约束不得通过修改该文件适配。新增数据库结构只修改 SQLModel、追加 migration，并补充对应迁移测试。

## 实施顺序

1. 修改 `../../../app/models.py` 中的目标结构。
2. 新增对应 revision；结构变化和必要的数据回填必须放在同一次可理解的升级流程中。
3. 调整 Schema、DAO、Service 和 API，使应用代码只依赖迁移后的目标结构。
4. 禁止用 `create_all()`、`ALTER TABLE`、`_ensure_columns()` 或启动时临时 DDL 代替 revision。
5. 新增 migration 后确认 `../../../scripts/build.py` 仍会打包整个 `../../../migrations`，通常无需逐文件修改构建配置。
6. 更新数据库规划、架构或发布说明中受影响的兼容边界。

## 基线接管规则

- 没有 `alembic_version` 的历史数据库只允许精确符合不可变的 `001_current_baseline`；校验通过后备份、`stamp 001`，再由 Alembic 执行后续 revision。
- 无版本数据库如果已经包含 `002` 或更高版本字段，或结构存在其他差异，必须拒绝启动，不能在 `database_migrations.py` 中增加字段白名单、临时 `ALTER TABLE` 或猜测其迁移历史。
- 已有合法 revision 的数据库统一执行 `upgrade head`。因此以后新增字段时，正常改动范围是 `models.py`、新的 `migrations/versions/<next_revision>.py`、业务代码和测试；不修改 `../../../app/database_migrations.py`。

## 数据迁移安全

- 数据转换前明确处理 NULL、非法值、重复值和约束冲突；不能静默丢弃或猜测修复用户数据。
- 对新增非空字段提供确定的回填策略，再建立 NOT NULL 约束。
- 创建唯一约束前检查历史重复数据，并定义拒绝、合并或显式修复策略。
- SQLite batch 重建必须显式保留字段、数据、索引和约束；重建后校验记录数与关键值。
- 不自动 downgrade 用户数据库。`downgrade()` 可明确拒绝；只有需求明确且能保证数据安全时才实现。
- 迁移失败必须向上抛出，不能继续启动 API 或监控。

## 测试要求

数据库结构属于共享基础设施，新增 revision 后运行完整测试，并至少覆盖：

- 全新数据库从 `base` 升级到 `head`。
- 上一 revision 升级到新 head，验证既有数据完整保留和正确回填。
- 已在 head 的数据库重复启动，不重复修改或创建无意义备份。
- Alembic head schema 与 `SQLModel.metadata` 一致。
- 非法历史数据、迁移失败或未知 revision 按预期拒绝启动。
- migration 文件能通过 `app.utils.resources.resource_path()` 定位并进入 PyInstaller 构建参数。

完整测试命令：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

提交前运行 `git diff --check`，检查 revision 文件、模型和测试在同一组改动中。默认不自动创建 commit 或推送；只有用户明确要求时，才按项目规范创建中文本地 commit 或推送。
