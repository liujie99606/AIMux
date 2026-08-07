from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton


class StatusBadge(QPushButton):
    """可点击的账号状态按钮，展示当前启用或禁用状态。"""

    def __init__(self, status: str, parent=None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_status(status)

    def set_status(self, status: str) -> None:
        active = status == "active"
        self.setText("启用" if active else "禁用")
        self.setAccessibleName(f"账号状态：{'启用' if active else '禁用'}")
        self.setToolTip("点击切换为禁用" if active else "点击切换为启用")
        # 启用绿色、禁用灰色，配色适配深色主题背景。
        if active:
            color = "#52c41a"
            background = "#162312"
            border = "#274916"
        else:
            color = "#8c8c8c"
            background = "#262626"
            border = "#3a3a3a"
        self.setStyleSheet(
            "QPushButton {"
            f"color: {color}; background: {background}; border: 1px solid {border};"
            " padding: 3px 10px; border-radius: 10px; font-size: 12px;"
            "}"
            "QPushButton:hover { background: #3a3a3a; }"
        )
