from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QPushButton, QWidget


class BatchToolbar(QWidget):
    test_requested = Signal()
    select_all_changed = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.select_all_checkbox = QCheckBox("全选")
        self.select_all_checkbox.setAccessibleName("全选账号")
        self.select_all_checkbox.toggled.connect(self.select_all_changed)
        self.test_button = QPushButton("批量测试")
        self.test_button.clicked.connect(self.test_requested)
        layout.addWidget(self.select_all_checkbox)
        layout.addWidget(self.test_button)

    def set_select_all_state(self, checked: bool) -> None:
        """同步全选控件状态，避免手动勾选时产生信号递归。"""
        self.select_all_checkbox.blockSignals(True)
        self.select_all_checkbox.setChecked(checked)
        self.select_all_checkbox.blockSignals(False)
