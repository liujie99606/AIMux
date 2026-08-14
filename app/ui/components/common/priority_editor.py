from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSpinBox


class PriorityEditor(QSpinBox):
    """表格内固定尺寸的账号优先级编辑器。"""

    def __init__(self, priority: int, parent=None) -> None:
        super().__init__(parent)
        self.setRange(0, 9)
        self.setValue(priority)
        self.setFixedSize(82, 30)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setToolTip("优先级越高越先被调度")
