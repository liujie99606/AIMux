from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QCheckBox, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QWidget

from app.ui.components.priority_editor import PriorityEditor
from app.ui.components.status_badge import StatusBadge


class AccountTable(QTableWidget):
    edit_requested = Signal(str)
    delete_requested = Signal(str)
    test_requested = Signal(str)
    toggle_requested = Signal(str)
    super_requested = Signal(str)
    priority_changed = Signal(str, int)

    def __init__(self, parent=None) -> None:
        super().__init__(0, 8, parent)
        self.setHorizontalHeaderLabels(["选择", "名称", "类型", "状态", "优先级", "支持模型", "最近使用", "操作"])
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.horizontalHeader().setStretchLastSection(True)

    def set_accounts(self, accounts: list[dict]) -> None:
        self.setRowCount(len(accounts))
        for row, account in enumerate(accounts):
            selected = QCheckBox(); selected.setProperty("account_id", account["id"]); selected.setAccessibleName(f"选择 {account['name']}")
            holder = QWidget(); layout = QHBoxLayout(holder); layout.setContentsMargins(0, 0, 0, 0); layout.addWidget(selected)
            # PySide6 不接受旧版 Qt 的裸整数对齐值，必须使用枚举常量。
            layout.setAlignment(selected, Qt.AlignmentFlag.AlignCenter)
            self.setCellWidget(row, 0, holder)
            self.setItem(row, 1, QTableWidgetItem(account["name"]))
            self.setItem(row, 2, QTableWidgetItem(account["type"]))
            self.setCellWidget(row, 3, StatusBadge(account["status"]))
            priority = PriorityEditor(account["priority"])
            priority.valueChanged.connect(lambda value, account_id=account["id"]: self.priority_changed.emit(account_id, value))
            self.setCellWidget(row, 4, priority)
            self.setItem(row, 5, QTableWidgetItem(", ".join(account.get("supported_models") or ["全部"])) )
            self.setItem(row, 6, QTableWidgetItem(account.get("last_used_at") or "-"))
            actions = QWidget(); buttons = QHBoxLayout(actions); buttons.setContentsMargins(0, 0, 0, 0)
            for label, signal in [("测试", self.test_requested), ("编辑", self.edit_requested), ("切换", self.toggle_requested), ("置顶", self.super_requested), ("删除", self.delete_requested)]:
                button = QPushButton(label); button.clicked.connect(lambda _, aid=account["id"], event=signal: event.emit(aid)); buttons.addWidget(button)
            self.setCellWidget(row, 7, actions)

    def selected_ids(self) -> list[str]:
        result: list[str] = []
        for row in range(self.rowCount()):
            check = self.cellWidget(row, 0).findChild(QCheckBox)
            if check.isChecked(): result.append(check.property("account_id"))
        return result
