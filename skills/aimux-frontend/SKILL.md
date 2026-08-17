---
name: aimux-frontend
description: AIMux Vue 3/Tauri 前端开发规范。修改 src 下的页面、组件、Pinia store、API 客户端、弹窗、表格或样式时使用。
---

# AIMux 前端规范

## 技术栈和分层

- Vue 3 Composition API、TypeScript、Vite、Element Plus、Element Plus Icons、Pinia、少量 SCSS/CSS。
- `src/api/` 负责 HTTP 客户端和 API 类型；`src/stores/` 负责跨页面状态；`src/pages/` 负责页面级数据加载和布局；`src/components/` 负责可复用交互。
- Tauri 能力通过 `@tauri-apps/api` 或后端 API 调用，不在页面中直接访问 Rust 内部状态。

## 交互约束

- 页面切换时加载对应页面的最新数据；保存、删除、启停、优先级等写操作完成后刷新受影响列表。
- 表单校验在弹窗内完成，校验失败时保持弹窗打开并在字段附近显示错误，不用关闭弹窗后再提示。
- 长列表必须使用后端分页；分页、筛选和重置条件变化时清晰刷新加载状态。
- 复用已有弹窗、表格、格式化和状态组件；同一业务的单个测试和批量测试使用同一测试弹窗组件。
- 交互按钮优先使用 Element Plus Icons；图标按钮提供 `aria-label` 或 tooltip；不要用不可理解的纯字符替代图标。
- 保持紧凑、对齐、可扫描的桌面布局，避免在页面中堆叠不必要的卡片和重复说明。

## API 和状态

- API 响应和请求使用明确的 TypeScript 类型，不用 `any` 绕过类型检查。
- 网络请求统一通过 `src/api/client.ts`，集中处理 base URL、超时和错误提示。
- 页面卸载或筛选变化时避免旧请求覆盖新数据；加载、空数据、错误和保存中的状态都要可见。
- 后端返回的时间、耗时和 Token 统一复用现有格式化方法，避免页面各自实现不同规则。

## 验证

聚焦页面改动先运行：

```powershell
npm run format:check
npm run build
```

涉及 API 契约、全局布局或多个页面时，再同时运行 Rust 检查。修改后不自动 `git commit` 或 `git push`，除非用户明确要求。
