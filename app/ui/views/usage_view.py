from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QVBoxLayout, QWidget

from app.ui.client import ApiClient
from app.ui.components.summary_card import SummaryCards
from app.ui.components.usage_detail_dialog import UsageDetailDialog
from app.ui.components.usage_filter import UsageFilter
from app.ui.components.usage_table import UsageTable


class UsageView(QWidget):
    def __init__(self, client: ApiClient, parent=None) -> None:
        super().__init__(parent); self.client = client
        root = QVBoxLayout(self); self.filter = UsageFilter(); root.addWidget(self.filter); self.summary = SummaryCards(); root.addWidget(self.summary); self.table = UsageTable(); root.addWidget(self.table)
        self.filter.refresh_button.clicked.connect(self.refresh); self.table.detail_requested.connect(self.show_detail); self.refresh()

    def refresh(self) -> None:
        try:
            data = self.client.get("/api/usage/records", params=self.filter.parameters()); self.table.set_records(data["items"]); self.summary.set_summary(data["summary"])
        except Exception as exc: QMessageBox.warning(self, "查询失败", str(exc))

    def show_detail(self, record_id: str) -> None:
        """拉取使用记录详情并打开结构化弹窗展示全部字段。"""
        try:
            record = self.client.get(f"/api/usage/records/{record_id}")
            UsageDetailDialog(record, self).exec()
        except Exception as exc: QMessageBox.warning(self, "读取失败", str(exc))
