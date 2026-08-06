from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget


class BatchToolbar(QWidget):
    test_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.test_button = QPushButton("批量测试")
        self.test_button.clicked.connect(self.test_requested)
        layout.addWidget(self.test_button)
