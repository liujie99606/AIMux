# 跨平台 UI 样式优化开发计划

## 1. 背景

AIMux 使用 Vue 3、Element Plus 和 Tauri 2。在 Windows 和 macOS 上，WebView 字体、系统滚动条、窗口尺寸和默认控件渲染存在差异，容易造成表格列宽、弹窗高度、输入框和导航间距不一致。

## 2. 目标

- 统一页面基础字体、颜色、边框、间距和控件高度。
- 账号表单、模型映射、支持模型和测试弹窗在不同平台保持紧凑对齐。
- 表格列使用明确的最小/固定宽度，长文本采用省略和详情展示。
- 页面具备加载、空数据、错误和窄窗口状态，不出现内容重叠。
- 保持 Tauri 原生窗口的最小化、关闭、托盘和开发者工具行为。

## 3. 实现范围

- `src/styles/index.scss`：全局 tokens、Element Plus 覆盖、紧凑布局和响应式约束。
- `src/layouts/MainLayout.vue`：侧边栏、动态时间、GitHub 和版本入口。
- `src/components/accounts/`：账号表单、模型映射和测试弹窗。
- `src/components/usage/`：筛选、表格、Token 用量和详情弹窗。
- `src/pages/monitor/`、`statistics/`、`models/`、`settings/`：统一工具栏、表格和卡片布局。

## 4. 交互原则

- 表单验证失败保持弹窗打开，错误显示在对应字段附近。
- 页面切换和写操作完成后加载最新数据。
- 复用 API 类型、格式化方法和已有组件，不在页面重复实现同一逻辑。
- 图标按钮提供 tooltip/aria-label；危险操作需要确认。

## 5. 验证

```powershell
npm run format:check
npm run build
```

在 Windows 和 macOS 实机或 Tauri 构建产物中检查账号、监控、使用记录和设置页面，重点观察表格对齐、弹窗尺寸、字体可读性和窗口缩放。
