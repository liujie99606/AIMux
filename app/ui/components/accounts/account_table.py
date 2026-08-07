from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLineEdit, QPushButton, QWidget

from app.ui.components.common.data_table import Column, DataTable
from app.ui.components.common.priority_editor import PriorityEditor
from app.ui.components.accounts.status_badge import StatusBadge
from app.ui.formatting import format_time


class AccountTable(DataTable):
    """账号管理表格，复杂列通过 widget getter 声明式渲染。"""

    edit_requested = Signal(str)
    copy_requested = Signal(str)
    delete_requested = Signal(str)
    test_requested = Signal(str)
    toggle_requested = Signal(str)
    priority_changed = Signal(str, int)
    adjust_priority_requested = Signal(str, int)
    name_changed = Signal(str, str)
    selection_changed = Signal()

    COLUMNS = [
        Column("选择", lambda r: r["_checkbox"], widget=True, width=50),
        Column("名称", lambda r: r["_name_editor"], widget=True, width=170),
        Column("类型", lambda r: r["type"]),
        Column("状态", lambda r: StatusBadge(r["status"]), widget=True, width=120),
        Column("优先级", lambda r: r["_priority"], widget=True, width=90),
        Column("优先级快捷操作", lambda r: r["_priority_actions"], widget=True, width=170),
        Column("最近使用", lambda r: format_time(r.get("last_used_at")), width=150),
        Column("操作", lambda r: r["_actions"], widget=True, stretch=True),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)

    def set_accounts(self, accounts: list[dict]) -> None:
        """渲染账号列表，复选框、优先级与操作按钮在预处理中绑定信号。"""
        prepared = [self._prepare(account) for account in accounts]
        self._render(prepared)
        self.selection_changed.emit()

    def selected_ids(self) -> list[str]:
        """收集已勾选行的账号 ID。"""
        result: list[str] = []
        for row in range(self.rowCount()):
            holder = self.cellWidget(row, 0)
            check = holder.findChild(QCheckBox) if holder else None
            if check is not None and check.isChecked():
                result.append(check.property("account_id"))
        return result

    def set_all_selected(self, checked: bool) -> None:
        """切换当前列表中所有账号的勾选状态。"""
        for row in range(self.rowCount()):
            holder = self.cellWidget(row, 0)
            check = holder.findChild(QCheckBox) if holder else None
            if check is not None:
                check.setChecked(checked)
        self.selection_changed.emit()

    def _prepare(self, account: dict) -> dict:
        """为单行数据生成 widget 列所需的控件并连接信号。"""
        check = QCheckBox()
        check.setProperty("account_id", account["id"])
        check.setAccessibleName(f"选择 {account['name']}")
        holder = QWidget()
        holder_layout = QHBoxLayout(holder)
        holder_layout.setContentsMargins(0, 0, 0, 0)
        holder_layout.addWidget(check)
        holder_layout.setAlignment(check, Qt.AlignmentFlag.AlignCenter)
        check.toggled.connect(lambda: self.selection_changed.emit())

        name_editor = QLineEdit(account["name"])
        name_editor.setFrame(False)
        name_editor.setProperty("original", account["name"])
        name_editor.editingFinished.connect(
            lambda editor=name_editor, aid=account["id"]: self._emit_name(aid, editor)
        )

        priority = PriorityEditor(account["priority"])
        priority.valueChanged.connect(
            lambda value, account_id=account["id"]: self.priority_changed.emit(account_id, value)
        )

        actions = QWidget()
        buttons = QHBoxLayout(actions)
        buttons.setContentsMargins(0, 0, 0, 0)
        for label, signal in [
            ("测试", self.test_requested),
            ("编辑", self.edit_requested),
            ("复制", self.copy_requested),
            ("停用" if account["status"] == "active" else "启用", self.toggle_requested),
            ("删除", self.delete_requested),
        ]:
            button = QPushButton(label)
            button.clicked.connect(lambda _, aid=account["id"], event=signal: event.emit(aid))
            buttons.addWidget(button)
        # 优先级快捷调整按钮独立成列，避免混在常规操作中。
        priority_actions = QWidget()
        priority_buttons = QHBoxLayout(priority_actions)
        priority_buttons.setContentsMargins(0, 0, 0, 0)
        for label, delta in [("优先级+4", 4), ("优先级-4", -4)]:
            button = QPushButton(label)
            button.clicked.connect(
                lambda _, aid=account["id"], d=delta: self.adjust_priority_requested.emit(aid, d)
            )
            priority_buttons.addWidget(button)

        prepared = dict(account)
        prepared["_checkbox"] = holder
        prepared["_name_editor"] = name_editor
        prepared["_priority"] = priority
        prepared["_priority_actions"] = priority_actions
        prepared["_actions"] = actions
        return prepared

    def _emit_name(self, account_id: str, editor: QLineEdit) -> None:
        """名称编辑完成且非空、有变化时通知外部保存。"""
        name = editor.text().strip()
        if name and name != editor.property("original"):
            self.name_changed.emit(account_id, name)
