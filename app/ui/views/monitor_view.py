from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel, QMessageBox, QVBoxLayout, QWidget

from app.ui.client import ApiClient
from app.ui.components.common.background_loader import BackgroundLoader
from app.ui.components.monitor_table import MonitorTable


class MonitorView(QWidget):
    """展示当前启用账号最近三十次监控结果。"""

    def __init__(self, client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.client = client
        self.loader = BackgroundLoader(self)
        self.loader.loaded.connect(self._apply_records)
        self.loader.failed.connect(self._error)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)
        self.status = QLabel()
        self.status.setObjectName("monitorStatus")
        root.addWidget(self.status)
        self.table = MonitorTable(self)
        root.addWidget(self.table, 1)
        self.timer = QTimer(self)
        self.timer.setInterval(30_000)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.refresh()

    def refresh(self) -> None:
        """查询最新监控记录并刷新监控矩阵。"""
        self.table.set_loading(True)
        self.loader.load(lambda: self.client.get("/api/monitor/records", params={"limit": 30}))

    def _apply_records(self, data: object) -> None:
        """在主线程渲染后台查询返回的监控记录。"""
        payload = data if isinstance(data, dict) else {}
        self.status.setText("监控已开启" if payload.get("monitoring_enabled", True) else "监控已关闭")
        self.table.set_loading(False)
        items = payload.get("items", [])
        self.table.set_records(items if isinstance(items, list) else [])

    def _error(self, exc: object) -> None:
        """显示后台监控查询失败原因。"""
        self.table.set_loading(False)
        QMessageBox.warning(self, "监控查询失败", str(exc))
