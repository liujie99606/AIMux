# 模型映射开发计划

## 1. 需求背景

账号管理中的“模型映射”用于解决客户端模型名与某个上游账号实际模型名不一致的问题。

示例：

```text
客户端请求模型：gpt-5.5
账号 A 的模型映射：gpt-5.5 -> grok4.6
发送给账号 A 上游的模型：grok4.6
```

映射属于账号级配置。不同账号可以为同一个客户端模型配置不同的上游模型，也可以完全不配置映射。没有匹配项时，保持原模型名发送。

本功能的目标是改变“发给当前账号上游的请求模型”，不是修改客户端请求本身，也不是修改模型维护目录中的模型名称。

## 2. 现有代码分析

当前请求链路为：

```text
OpenAI/Anthropic 兼容接口
    -> controller 读取 JSON body
    -> dispatch_service.forward_non_stream / forward_stream
    -> pick(session, body["model"], account_type)
    -> account_dao.pick_one 按客户端模型、状态、优先级、倍率选择账号
    -> forwarders.post / open_stream 原样发送 body
    -> UsageRecord.model 保存 body["model"]
```

当前有几个必须保留的行为：

1. `pick_one()` 根据客户端请求模型匹配账号的 `supported_models`。模型映射不能提前应用，否则会导致账号选择依据变成上游模型，破坏现有调度语义。
2. 非流式和流式转发都在每次重试循环中重新 `pick()`。映射必须在每次选中账号后重新解析，不能在循环外只计算一次。
3. 现有 `UsageRecord.model` 表示客户端请求模型，使用记录、统计和筛选都依赖这个语义。模型映射不应静默改写该字段。
4. `forwarders` 当前接收一个请求 body 并直接 JSON 转发。应由调度服务为当前尝试生成副本，避免修改入口 body 后影响重试、日志或响应处理。
5. 账号管理测试和后台监控也会调用 `monitor_service.send_ping()`，不经过 `dispatch_service`。因此不能只在 `dispatch_service` 中接入映射；测试/监控必须在 `send_ping()` 内复用同一个解析方法。

## 3. 推荐方案

### 3.1 存储方式

在 `accounts` 表增加可空文本字段 `model_mappings`，内容为 JSON 对象：

```json
{
  "gpt-5.5": "grok4.6",
  "claude-sonnet-4-8": "provider-model-name"
}
```

推荐使用 JSON 字段而不是新建映射表，原因是：

- 映射是账号配置的一部分，不需要独立生命周期、分页或跨账号查询。
- 账号编辑页可以一次性读取和保存完整映射。
- 目前项目已经用 JSON 文本保存 `supported_models` 和 `tags`，符合现有 SQLite/SQLModel 约定。
- 迁移简单，旧账号使用 `NULL` 即表示没有映射，完全向后兼容。

字段名保持 `model_mappings`，不改已有字段名。新增 Alembic revision，例如 `003_add_account_model_mappings.py`，只执行 `ALTER TABLE accounts ADD COLUMN model_mappings`，不可修改已发布的 `001`、`002`。

### 3.2 映射格式与校验

前端提交和后端 Schema 都使用 `dict[str, str] | None`。保存前统一做以下规范化：

- key 和 value 去除首尾空格。
- 空 key、空 value、非字符串值拒绝保存。
- 同一个客户端模型只能有一个目标模型；表单中重复 key 应在前端阻止。
- 映射为空时存 `NULL`，不存 `{}`，与项目现有可选 JSON 字段习惯一致。
- 客户端模型候选来自当前账号已勾选的支持模型；上游模型候选来自当前账号协议类型的模型维护目录。编辑历史账号时，如果上游目标已从目录删除，表单暂时保留该历史值供用户改选，但新增值不允许自由输入。
- 建议禁止 key 与 value 完全相同，或将其视为无效映射并直接省略，避免制造无意义配置。
- 初期不支持通配符、正则表达式、链式映射和协议转换，避免匹配优先级和安全边界复杂化。

### 3.3 解析时机

新增一个纯函数，例如：

```python
def resolve_upstream_model(account: Account, requested_model: str | None) -> str | None:
    """按当前账号的映射解析发往上游的模型名。"""
```

规则：

1. `requested_model is None` 时返回 `None`，不向请求体凭空增加模型。
2. 当前账号没有映射时返回客户端模型。
3. 存在精确 key 时返回映射 value。
4. 没有匹配项时返回客户端模型。
5. 映射 JSON 损坏时按无映射处理，并记录日志或返回配置错误提示；不能让一个账号的坏配置导致整个服务启动失败。

真实客户端请求在 `forward_non_stream` 和 `forward_stream` 的每次尝试中：

```python
account = pick(session, requested_model, account_type)
upstream_model = resolve_upstream_model(account, requested_model)
attempt_body = dict(body)
if upstream_model is not None:
    attempt_body["model"] = upstream_model
```

然后仅把 `attempt_body` 传给 `forwarders.post` 或 `forwarders.open_stream`。账号 A 失败后重新选择账号 B 时，必须重新生成 `attempt_body`，确保 A、B 的映射互不污染。

账号管理测试和后台监控的链路不同：它们已经拿到具体账号，再调用 `monitor_service.send_ping(account, model, settings)`。推荐在 `send_ping()` 内执行同一解析流程：

```python
upstream_model = resolve_upstream_model(account, model)
endpoint, body = build_ping_request(account, upstream_model)
return await forwarders.post(account, endpoint, body, settings)
```

因此三类入口的统一规则是：真实请求先按客户端模型 `pick()` 选账号，再映射；账号测试和监控先确定账号/逻辑测试模型，再在 `send_ping()` 中映射。`resolve_upstream_model()` 只能有一份实现，不能在测试、监控和调度中各自复制一套。

### 3.4 记录和响应语义

推荐保持现有 `UsageRecord.model` 为客户端请求模型，因为用户是按这个模型发起请求的，现有使用记录筛选、统计和模型维度不会被破坏。

为便于排查“客户端模型与上游模型不同”的问题，建议在本计划的第二阶段增加可选字段 `upstream_model` 到 `UsageRecord`，或至少在详细记录中显示它。若本次只实现最小功能，可以先不增加该字段，但必须在代码注释和文档中明确：当前记录的 `model` 是客户端模型，不代表实际发送到上游的名称。

响应正文原则上原样返回，不改写上游响应中的 `model` 字段。上游通常会返回实际模型名；网关不应伪造或转换响应协议。若后续需要让客户端始终看到原模型名，应另立响应重写需求，不能混入本次实现。

### 3.5 作用范围建议

推荐映射作用于所有经过账号转发的、且请求体包含 `model` 的上游请求：

- OpenAI Chat Completions、Responses、Completions、Embeddings、图片/音频等兼容端点。
- Anthropic Messages 和旧版 Complete 等包含模型字段的端点。
- 账号手动测试和后台监控请求。

这样“账号配置的上游模型名”在所有入口保持一致，避免真实请求和监控测试使用不同模型导致误判。监控记录中的 `model` 继续表示逻辑测试模型；若增加 `upstream_model`，再同时展示实际测试模型。

对于没有 `model` 字段的端点，不做任何处理。映射不做 OpenAI/Anthropic 协议转换，也不修改 URL、认证头或其他请求参数。

## 4. 需要改动的模块

### 4.1 数据库和模型

- `app/models.py`：`Account` 增加 `model_mappings: Optional[str] = None`。
- `migrations/versions/003_add_account_model_mappings.py`：新增可空字段。
- `tests/test_database_migrations.py`：验证全新库、`002` 数据库升级后字段存在，旧账号数据不丢失。

### 4.2 Schema、DAO 和 Service

- `app/schemas.py`：`AccountCreate`、`AccountUpdate`、`AccountView` 增加模型映射字段及类型约束。
- `app/service/account_service.py`：增加 JSON 序列化/反序列化和规范化；`to_view()` 返回字典供编辑回显。
- 建议在 `app/service/dispatch_service.py` 或独立 `app/service/model_mapping.py` 增加纯解析函数，禁止 controller 直接读取数据库 JSON。
- `pick_one()` 不改排序和候选资格逻辑，仍按客户端模型选择账号。

### 4.3 请求转发

- `app/service/dispatch_service.py`：非流式和流式每次尝试分别解析当前账号映射，构造请求 body 副本。
- `app/service/monitor_service.py`：`send_ping()` 调用同一个解析方法，覆盖账号管理测试和后台监控；`build_ping_request()` 接收解析后的上游模型。不能出现真实请求支持映射、监控却不支持映射的分裂行为。
- `app/utils/forwarders.py`：原则上不承载账号选择和业务映射，只负责发送传入 body，避免工具层反向依赖业务规则。

### 4.4 账号管理界面

- `app/ui/components/accounts/account_form.py`：新增“模型映射”编辑区域，建议使用可增删行的表格/列表：客户端模型、上游模型、删除按钮。
- 映射客户端模型使用当前协议已勾选的“支持模型”下拉框；上游模型使用当前协议全部模型目录下拉框。编辑旧数据时保留已保存但已从目录删除的目标值，避免打开表单后立即丢失配置。
- 保存前前端校验：key/value 非空、key 不重复、目标模型非空；校验失败保持弹窗打开。
- `app/ui/components/accounts/account_table.py`：首期不建议增加“模型映射”列，避免列表过宽；可在编辑页查看和维护。
- `tests/test_ui_components.py`：覆盖新增、编辑、切换协议、重复 key、删除行、旧映射回显和空映射提交。

### 4.5 文档

- `docs/账号管理功能.md`：说明映射格式、匹配规则、作用范围和保存校验。
- `docs/调度逻辑说明`（实际文件名以仓库为准）：说明先按客户端模型选账号，再按账号映射生成上游请求模型。
- `README.md` 或 FAQ：增加“客户端模型与上游模型不同”的示例和排障说明。

## 5. 风险与处理

### 5.1 调度资格被错误改变

**风险**：先把 `gpt-5.5` 替换为 `grok4.6` 再调用 `pick_one()`，账号可能因不支持 `grok4.6` 被错误排除。

**处理**：永远使用客户端原模型调用 `pick_one()`，映射只在账号选定后应用。

### 5.2 重试污染

**风险**：直接修改共享 `body["model"]`，第一次尝试的映射会影响后续重试和 UsageRecord。

**处理**：每次尝试 `dict(body)` 复制，并分别解析当前账号映射；原始 body 和客户端模型变量只读。

### 5.3 账号映射配置损坏

**风险**：历史数据库中 JSON 非法，读取账号列表或启动时异常。

**处理**：读取时容错为空映射；保存时严格校验；迁移只增加可空列，不回填复杂数据。

### 5.4 供应商模型名不存在

**风险**：目标模型拼写错误，所有请求返回上游 4xx，账号优先级按失败规则下降。

**处理**：保存前提示但不强制目标模型必须在本地目录；测试默认模型和监控应使用映射后的真实模型验证配置；文档明确目标模型由用户负责。

### 5.5 统计和详情含义混乱

**风险**：使用记录把 `gpt-5.5` 显示成 `grok4.6`，用户无法按客户端模型查询；或者响应模型和记录不一致。

**处理**：本期 `UsageRecord.model` 保持客户端模型；后续用 `upstream_model` 单独记录实际发送模型；不改写响应。

### 5.6 流式请求处理不一致

**风险**：非流式支持映射，流式忘记支持，或首块前重试时使用了错误映射。

**处理**：两条路径共用一个解析函数；为每次流式尝试单独构造 body 并测试账号切换。

### 5.7 模型目录和支持模型的边界

**风险**：强制映射目标必须在模型维护目录中，导致无法配置供应商私有模型；完全不校验又容易输错。

**处理**：key 候选关联支持模型，value 自由输入；提供明确的输入提示和手动测试入口，不把本地目录当成上游事实来源。

## 6. 测试计划

### 6.1 单元测试

- 映射 JSON 解析：正常对象、空值、空字符串、非法 JSON、非对象、空 key/value。
- 精确匹配、未匹配回退、`model=None`、同名映射和 Unicode 模型名。
- 请求 body 副本不修改原始 body。
- 账号 A、B 使用不同映射时，连续重试分别发送各自目标模型。

### 6.2 调度和转发测试

- 非流式成功请求：客户端模型用于选号，上游收到映射模型，UsageRecord 保存客户端模型。
- 非流式失败重试：第一次账号映射模型 A 失败，第二个账号映射模型 B 成功。
- 流式首块前失败重试：每次候选账号的上游 body 映射正确。
- 流式首块后失败：记录当前尝试实际使用的账号和客户端模型，不重放请求。
- 账号管理手动测试：账号逻辑测试模型为 `gpt-5.5` 时，上游收到该账号映射后的模型。
- 后台监控：监控逻辑测试模型为 `gpt-5.5` 时，上游收到该账号映射后的模型，监控记录仍保存逻辑模型。
- 没有映射时，非流式/流式行为与现有完全一致。
- OpenAI 和 Anthropic 请求格式均保留原协议，只有 `model` 值变化。

### 6.3 API 和数据库测试

- 创建、编辑、详情、列表账号都能保存和返回映射。
- 空映射规范化为 `NULL`，编辑回显为空列表/空对象。
- migration 从 `002` 升级到 `003` 并保留账号数据。
- 非法映射请求返回清晰的 422，不能写入坏 JSON。

### 6.4 UI 测试

- 新增表单可添加、删除和编辑映射行。
- 重复客户端模型、空模型、空目标模型保存时保持弹窗打开。
- 切换协议时过滤 key 候选，不丢失旧映射。
- 编辑旧账号正确回显映射；没有映射的旧账号正常打开。

## 7. 实施顺序

1. 已确定字段语义：`model_mappings` 保存“客户端模型 -> 当前账号上游模型”；本期 `UsageRecord.model` 继续保存客户端模型，不新增 `upstream_model`。
2. 阅读数据库 migration skill，新增 `003_add_account_model_mappings.py`，完成模型和 migration 测试。
3. 增加 Schema、service 序列化/反序列化和账号 API 回显。
4. 实现独立模型映射解析函数，并接入非流式、流式、测试和监控。
5. 增加账号表单映射编辑器和前端校验。
6. 更新账号管理、调度逻辑和 README 文档。
7. 运行受影响测试：数据库迁移、账号 API、调度转发、监控和账号表单；因为涉及数据库、调度核心和多个模块，完成后再运行一次全量测试。
8. 默认不自动创建 git commit 或推送，等待用户明确指示。

## 8. 验收标准

- 客户端发送 `gpt-5.5` 时，账号 A 配置映射后上游收到 `grok4.6`。
- 账号 A 没有映射或没有匹配项时，上游仍收到 `gpt-5.5`。
- 调度始终先按 `gpt-5.5` 选择账号，不能因映射目标改变候选资格。
- 重试切换账号时，每次使用当前账号自己的映射，不发生 body 污染。
- 非流式、流式、手动测试和后台监控的映射行为一致。
- 现有使用记录、Token 统计、优先级和无映射请求行为不回归。
- 旧数据库可通过 migration 正常升级，旧账号无需手工修复。
- 映射配置错误有明确提示，且不会关闭账号编辑弹窗。

## 9. 待用户确认的问题

实现前需要最终确认以下产品决策：

1. 映射是否作用于手动测试和后台监控？本计划已按“所有账号上游请求都生效”设计，并要求在 `send_ping()` 中复用解析函数。
2. “支持模型”是否继续表示客户端可请求模型，还是要同时允许映射目标？本计划保持前者，目标模型自由输入。
3. `UsageRecord` 是否需要本期新增 `upstream_model` 字段？推荐本期至少保留客户端模型语义，若需要审计则一并新增字段和 migration。
4. 映射是仅支持精确匹配，还是未来需要通配符/正则？本计划只实现精确匹配。
