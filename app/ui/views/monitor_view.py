from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget

from app.ui.client import ApiClient
from app.ui.components.monitor_status_grid import MonitorStatusGrid
from app.ui.formatting import format_duration_ms, format_time


class MonitorView(QWidget):
    """展示当前启用账号最近三十次监控结果。"""

    def __init__(self, client: ApiClient, parent=None) -> None:
        super().__init__(parent)
        self.client = client
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)
        self.status = QLabel()
        root.addWidget(self.status)
        self.rows = QVBoxLayout()
        self.rows.setSpacing(8)
        root.addLayout(self.rows)
        root.addStretch()
        self.timer = QTimer(self)
        self.timer.setInterval(30_000)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.refresh()

    def refresh(self) -> None:
        """查询最新监控记录并重建当前启用账号行。"""
        try:
            data = self.client.get("/api/monitor/records", params={"limit": 30})
            self.status.setText("监控已开启" if data.get("monitoring_enabled", True) else "监控已关闭")
            self._clear_rows()
            for item in data.get("items", []):
                self.rows.addLayout(self._row(item))
        except Exception as exc:
            QMessageBox.warning(self, "监控查询失败", str(exc))

    def _row(self, item: dict) -> QHBoxLayout:
        """构建一个账号监控状态行。"""
        records = item.get("records", [])
        latest = records[-1] if records else {}
        layout = QHBoxLayout()
        layout.setSpacing(10)
        name = QLabel(item.get("account_name") or "-")
        name.setFixedWidth(160)
        layout.addWidget(name)
        layout.addWidget(QLabel(item.get("account_type") or "-"))
        model = QLabel(item.get("model") or latest.get("model") or "-")
        model.setFixedWidth(180)
        layout.addWidget(model)
        layout.addWidget(QLabel(format_time(latest.get("checked_at"))))
        layout.addWidget(QLabel(format_duration_ms(latest.get("duration_ms"))))
        grid = MonitorStatusGrid()
        grid.set_records(records)
        layout.addWidget(grid, 1)
        return layout

    def _clear_rows(self) -> None:
        """释放旧账号行控件。"""
        while self.rows.count():
            item = self.rows.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
            elif item.layout() is not None:
                self._clear_layout(item.layout())

    def _clear_layout(self, layout: QHBoxLayout) -> None:
        """递归释放行布局中的控件。"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
