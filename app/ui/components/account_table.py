from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QPushButton, QWidget

from app.ui.components.data_table import Column, DataTable
from app.ui.components.priority_editor import PriorityEditor
from app.ui.components.status_badge import StatusBadge
from app.ui.formatting import format_time


class AccountTable(DataTable):
    """账号管理表格，复杂列通过 widget getter 声明式渲染。"""

    edit_requested = Signal(str)
    copy_requested = Signal(str)
    delete_requested = Signal(str)
    test_requested = Signal(str)
    toggle_requested = Signal(str)
    super_requested = Signal(str)
    priority_changed = Signal(str, int)

    COLUMNS = [
        Column("选择", lambda r: r["_checkbox"], widget=True, width=48),
        Column("名称", lambda r: r["name"]),
        Column("类型", lambda r: r["type"]),
        Column("状态", lambda r: StatusBadge(r["status"]), widget=True, width=80),
        Column("优先级", lambda r: r["_priority"], widget=True, width=90),
        Column("最近使用", lambda r: format_time(r.get("last_used_at"))),
        Column("操作", lambda r: r["_actions"], widget=True, stretch=True),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)

    def set_accounts(self, accounts: list[dict]) -> None:
        """渲染账号列表，复选框、优先级与操作按钮在预处理中绑定信号。"""
        prepared = [self._prepare(account) for account in accounts]
        self._render(prepared)

    def selected_ids(self) -> list[str]:
        """收集已勾选行的账号 ID。"""
        result: list[str] = []
        for row in range(self.rowCount()):
            holder = self.cellWidget(row, 0)
            check = holder.findChild(QCheckBox) if holder else None
            if check is not None and check.isChecked():
                result.append(check.property("account_id"))
        return result

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
            ("切换", self.toggle_requested),
            ("置顶", self.super_requested),
            ("删除", self.delete_requested),
        ]:
            button = QPushButton(label)
            button.clicked.connect(lambda _, aid=account["id"], event=signal: event.emit(aid))
            buttons.addWidget(button)

        prepared = dict(account)
        prepared["_checkbox"] = holder
        prepared["_priority"] = priority
        prepared["_actions"] = actions
        return prepared
