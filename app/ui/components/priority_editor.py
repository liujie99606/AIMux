from __future__ import annotations

from PySide6.QtWidgets import QSpinBox


class PriorityEditor(QSpinBox):
    def __init__(self, priority: int, parent=None) -> None:
        super().__init__(parent)
        self.setRange(0, 9)
        self.setValue(priority)
        self.setToolTip("优先级越高越先被调度")
