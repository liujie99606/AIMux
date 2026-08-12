---
name: aimux-frontend
description: AIMux 项目前端（PySide6 桌面端）开发规范。涵盖视图/组件分层、信号通信、ApiClient 调用、弹窗与表单、表格与样式、组件抽取原则。在新增/修改 app/ui/ 下的视图、组件、弹窗、表格、主窗口，或调整账号管理/模型维护/使用记录/设置页交互时使用。
agent_created: true
---

# AIMux 前端开发规范（PySide6 桌面端）

AIMux 桌面端用 PySide6 构建，通过左侧导航在账号管理、模型维护、使用记录、设置四个视图间切换。前端通过 `ApiClient` 调用本地 FastAPI 后端（默认 `http://127.0.0.1:7788`）。

## 技术栈

- PySide6（Qt for Python 官方绑定）
- httpx（`ApiClient` 内部用 `httpx.request` 调本地 API）
- 测试用 `QT_QPA_PLATFORM=offscreen` 无头运行

## 目录结构

```
app/ui/
├── main_window.py     # QMainWindow：导航 + QStackedWidget 内容栈 + 托盘
├── client.py          # ApiClient：HTTP 封装（get/post/put/delete）
├── views/             # 顶层页面（QWidget），每页对应一个导航项
│   ├── accounts_view.py
│   ├── models_view.py
│   ├── usage_view.py
│   └── settings_view.py
└── components/        # 可复用控件（QTableWidget/QDialog 等）
    ├── account_table.py
    ├── account_form.py
    ├── account_test_dialog.py
    ├── batch_toolbar.py
    ├── model_form.py
    ├── model_test_dialog.py
    ├── priority_editor.py
    ├── status_badge.py
    ├── summary_card.py
    ├── usage_table.py
    └── usage_filter.py
```

## 视图 vs 组件（关键分层）

- **视图（views/）**：顶层页面，挂在 `MainWindow` 的 `QStackedWidget` 中。负责：拉取数据、筛选、调用 API、错误提示、把子组件的信号接到业务方法。构造签名固定 `__init__(self, client: ApiClient, parent=None)`。
- **组件（components/）**：可复用控件。负责：自身渲染、内部交互、通过 `Signal` 向外通知。不直接持有视图引用，依赖通过构造参数注入。
- **抽取原则**：只要某块 UI（弹窗、表格、表单、工具栏）会被复用或逻辑独立，就抽成 `components/` 下独立文件，自包含。例如测试弹窗 `AccountTestDialog` 独立成件，视图层只负责"拉模型列表 + 判空 + 打开弹窗"。

## 通用编码规范

- 每个文件首行 `from __future__ import annotations`。
- 全量类型注解；用 `str | None`、`list[dict]` 等现代语法。
- 中文单行 docstring 说明类/函数意图。
- 错误处理：视图层 `try/except Exception as exc: self._error(exc)`，`_error` 统一 `QMessageBox.warning(self, "操作失败", str(exc))`。组件内部不做弹窗，把异常抛给视图或用信号。
- PySide6 枚举必须用完整枚举常量，不接受旧版 Qt 裸整数。例：
  - `Qt.AlignmentFlag.AlignCenter`（不是 `Qt.AlignCenter` 的整数）
  - `QAbstractItemView.SelectionBehavior.SelectRows`
  - `QAbstractItemView.EditTrigger.NoEditTriggers`
  - `QLineEdit.EchoMode.Password`
  - `QDialogButtonBox.StandardButton.Save`
  - `QMessageBox.StandardButton.Yes`
  - `Qt.ItemFlag.ItemIsUserCheckable`
  - `Qt.CheckState.Checked` / `Qt.CheckState.Unchecked`

## 信号通信规范

- 组件用 `Signal(...)` 声明对外事件，视图在 `__init__` 末尾 `connect` 到业务方法。
- 表格类信号命名：`<动作>_requested`，参数为账号/模型 id。例：
  ```python
  class AccountTable(QTableWidget):
      edit_requested = Signal(str)
      copy_requested = Signal(str)
      delete_requested = Signal(str)
      test_requested = Signal(str)
      priority_changed = Signal(str, int)   # 多参数用元组类型
  ```
- 按钮回调绑定用 `lambda` + 默认参数捕获循环变量，避免闭包延迟求值问题：
  ```python
  button.clicked.connect(lambda _, aid=account["id"], event=signal: event.emit(aid))
  ```
- 视图连接示例：`self.table.copy_requested.connect(self.copy)`。

## ApiClient 调用规范

- `ApiClient`（`../../app/ui/client.py`）封装 `get/post/put/delete`，内部 `httpx.request(..., timeout=30)`。
- 204 返回 `None`；非 2xx `raise_for_status()`（由视图 `_error` 捕获）。
- 查询参数传 `params=`，JSON 体传 `json=`。
- 视图持有 `self.client` 与 `self.accounts: dict[str, dict]`（id → 视图数据）缓存，便于编辑/复制时取数。

## 表格规范（QTableWidget）

- 继承 `QTableWidget`，`__init__` 设列数、表头、`SelectRows`、`NoEditTriggers`、`setStretchLastSection(True)`。
- 复杂单元格（复选框、状态徽章、优先级编辑器、操作按钮组）用 `setCellWidget(row, col, widget)`；纯文本用 `setItem(row, col, QTableWidgetItem(text))`。
- 复选框列：用 `QWidget` + `QHBoxLayout(margins=0,0,0,0)` 包裹 `QCheckBox`，`setProperty("account_id", id)` 存 id，`setAccessibleName` 供无障碍。
- 操作按钮组：`QWidget` + `QHBoxLayout`，循环创建 `QPushButton`，统一 lambda 绑定信号。
- 勾选 id 收集：遍历行 `cellWidget(row,0).findChild(QCheckBox)` 读 `property("account_id")`。
- 列调整时同步更新 `setHorizontalHeaderLabels`、列数、所有 `setCellWidget`/`setItem` 的列索引。

## 表单/弹窗规范（QDialog）

- 继承 `QDialog`，`setWindowTitle` 区分新增/编辑/测试。
- 表单用 `QFormLayout`，`addRow("标签", widget)` 逐行加；底部 `QDialogButtonBox(Save | Cancel)`，`accepted→accept`、`rejected→reject`。
- 模式切换用布尔参数控制标题与提交方式，避免重复建类。例：`AccountForm(models, account, parent, copy=False)`，`copy=True` 时标题显示"新增账号"但预填数据。
- API 密钥字段：QLineEdit 明文可见回显（本地单机，不用 EchoMode.Password），`setPlaceholderText("必填")`；编辑/复制时预填 `account["api_key"]`，`payload()` 始终校验非空。
- 多选列表：`QListWidget` + `QListWidgetItem`，`setFlags(flags | ItemIsUserCheckable)`，`setCheckState` 控制勾选。
- 弹窗尺寸用 `setMinimumSize`/`setMinimumWidth` 约束最小可读宽度（表单类约 460–920，结果展示类 ≥ 900×700）。
- 集成型弹窗（如 `AccountTestDialog`）：自包含"选模型 + 触发请求 + 渲染结果"，通过构造注入 `client/account/models`，内部完成 HTTP 调用与日志渲染，视图层只 `dialog.exec()`。

## 日志/结果展示规范

- 深色等宽区域用 `QTextEdit`（支持 HTML 着色）+ `setReadOnly(True)` + `setStyleSheet` 设背景/字体。
- 配色建议：标签青 `#9cdcfe`、成功绿 `#4ec9b0`、失败橙红 `#f48771`、提示蓝 `#569cd6`、正文 `#d4d4d4`、背景 `#1e1e1e`。
- 追加 HTML 用 `append(html)`；追加纯文本需先转义 `&<>` 再把 `\n` 换成 `<br>`。
- JSON 响应体先 `json.loads` + `json.dumps(indent=2)` 美化，解析失败则原样展示。

## 主窗口规范（main_window.py）

- `QMainWindow`，左侧 `QFrame#sidebar`（固定 176px 宽）+ 右侧 `QStackedWidget`。
- 导航用 `QListWidget#navigation`，`currentRowChanged → content.setCurrentIndex`。
- 图标优先用 `style().standardIcon(QStyle.StandardPixmap.SP_*)`，应用图标用 `resource_path("assets","icons","aimux.png")`。
- 关闭默认最小化到托盘（`QSystemTrayIcon`），`_closing` 标志区分真正退出。
- 全局 `setStyleSheet` 集中定义侧栏/导航项样式（选中蓝、hover 灰）。

## 样式规范

- 控件内联样式用 `setStyleSheet("...")`，避免散落全局。
- 中文标签直接用字面量；按钮文案简洁（"新增账号"、"刷新"、"测试"、"编辑"、"复制"、"切换"、"置顶"、"删除"）。
- 数值范围控件用 `QSpinBox` + `setRange`（如优先级 0–9）。

## 测试规范（tests/test_ui_components.py）

- 首行 `os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")`，再 `QApplication.instance() or QApplication([])`。
- 断言聚焦行为（`rowCount`、`selected_ids`、表单模型过滤结果），不断言渲染像素。
- 构造组件传入最小 dict 数据即可，无需真实 API。
- 默认按 UI 改动影响范围运行聚焦测试：组件改动运行 `tests/test_ui_components.py` 中对应测试，具体视图或页面交互改动运行对应视图/API 集成测试；必要时同时运行受影响的后端契约测试。
- 只有在跨多个页面或前后端模块、修改共享组件/客户端/API 契约、影响主窗口或全局状态，聚焦测试无法覆盖完整影响范围，或准备发布/打包时，才运行全量测试：`./.venv/Scripts/python.exe -m pytest`。
- 提交前应记录实际执行的测试命令及结果；仅文档或注释改动可只执行 `git diff --check`。

## Git 提交规范

- 每次改动完成并测试通过后，**立即 git commit**，但**不推送**（不执行 `git push`）。
- 提交信息用中文简述本次改动；多文件改动可按逻辑拆成多个提交。
- 用 `/commit` 命令提交（自动处理安全协议与 pre-commit hooks），不要加 `--no-verify` 跳过钩子。
- 仓库保持"本地领先远程"状态，由用户决定何时批量推送。

## 改动自检清单

新增/修改前端代码时逐条核对：

1. 视图/组件是否分清层级？可复用 UI 是否抽成 `components/` 独立文件？
2. 文件首行是否有 `from __future__ import annotations`？类型注解齐全？
3. PySide6 枚举是否用完整常量（如 `Qt.AlignmentFlag.AlignCenter`），无裸整数？
4. 组件对外事件是否用 `Signal` 声明，视图是否 `connect` 到业务方法？
5. lambda 回调是否用默认参数捕获循环变量（`aid=account["id"]`）？
6. API 调用是否走 `ApiClient`？异常是否被视图 `_error` 捕获？
7. 表格列增减时，表头、列数、所有 `setCellWidget`/`setItem` 索引是否同步？
8. 弹窗是否用 `QDialog` + `QFormLayout` + `QDialogButtonBox`？模式是否用参数区分？
9. 深色日志区是否只读、等宽、HTML 转义安全？
10. 是否运行了与本次改动影响范围匹配的测试；若属于跨模块、共享组件/API 契约或发布前改动，是否补充运行全量测试？
11. 是否已 `git commit`（仅提交，不推送）？
