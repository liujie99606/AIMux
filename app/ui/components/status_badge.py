from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel


class StatusBadge(QLabel):
    def __init__(self, status: str, parent=None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_status(status)

    def set_status(self, status: str) -> None:
        active = status == "active"
        self.setText("启用" if active else "停用")
        color = "#237804" if active else "#8c8c8c"
        background = "#f6ffed" if active else "#f5f5f5"
        self.setStyleSheet(f"color: {color}; background: {background}; padding: 3px 8px;")
