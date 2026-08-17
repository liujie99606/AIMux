# 模型映射开发计划

## 1. 需求

账号级“模型映射”解决客户端模型名与某个上游账号实际模型名不一致的问题。例如客户端请求 `gpt-5.5`，账号配置 `gpt-5.5 -> grok4.6`，该账号本次上游请求使用 `grok4.6`。客户端请求、使用记录和统计仍保留 `gpt-5.5`。

## 2. 调度边界

调度必须先使用客户端模型选择账号，再对已选账号解析映射：

```text
account = pick_one(requested_model, account_type)
upstream_model = resolve_upstream_model(account, requested_model)
```

映射不能提前参与 `pick_one`，否则会破坏支持模型匹配和账号优先级规则。每次失败重试都重新取号并重新解析当前账号的映射。账号管理测试和后台监控也必须调用同一解析方法。

## 3. 存储

沿用 `accounts.model_mappings` 文本字段，保存 JSON 对象：

```json
{
  "gpt-5.5": "grok4.6"
}
```

该字段已经在 Rust 基线中存在；未来若数据库还没有该字段，应新增 SQLx migration，不修改 `0001_baseline.sql`。空映射保存为 `NULL`，key/value 必须是非空字符串。

## 4. 前端交互

- 客户端模型下拉选项来自当前账号已勾选的支持模型。
- 上游模型下拉选项来自当前账号协议类型的模型目录。
- 编辑旧映射时，即使目标模型已经从目录删除，也先回显历史值，避免无提示丢配置。
- 阻止重复客户端模型、空值和无意义的相同映射。
- 保存失败时保持账号弹窗打开并显示字段错误。

## 5. 后端实现位置

- `src-tauri/src/model/account.rs`：账号映射字段。
- `src-tauri/src/schema/account_schema.rs`：请求和响应类型。
- `src-tauri/src/service/account_service.rs`：映射规范化和编辑回显。
- `src-tauri/src/service/scheduler_service.rs`：集中实现 `resolve_upstream_model`。
- `src-tauri/src/gateway/`：每次请求尝试生成上游请求副本，不修改客户端 body。
- `src-tauri/src/service/monitor_service.rs`：测试/监控使用相同解析逻辑。

## 6. 风险和验证

- 映射只改变上游 `model` 字段，不改提示词、消息、缓存字段和客户端响应。
- 映射目标不一定被上游支持，仍按正常上游失败处理并记录原因。
- 非流式、流式、账号测试、后台监控和重试路径必须分别验证。
- 使用记录的 `model`、统计筛选和模型目录不能被上游模型名污染。

验证重点：

1. 没有映射时请求模型保持不变。
2. 命中映射时只有发往当前账号的 body 使用目标模型。
3. 重试切换账号时使用新账号自己的映射。
4. 流结束或失败时使用记录仍保存客户端模型和最终状态。
