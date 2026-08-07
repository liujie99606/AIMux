from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QLabel


class CurrentTimeLabel(QLabel):
    """显示本机当前时间，并每秒自动刷新。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebarClock")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._refresh)
        self._refresh()
        self.timer.start()

    def _refresh(self) -> None:
        """按本机时区刷新时分秒文本。"""
        self.setText(datetime.now().strftime("%H:%M:%S"))
