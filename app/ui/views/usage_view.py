from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QVBoxLayout, QWidget

from app.ui.client import ApiClient
from app.ui.components.usage.summary_card import SummaryCards
from app.ui.components.usage.usage_detail_dialog import UsageDetailDialog
from app.ui.components.usage.usage_filter import UsageFilter
from app.ui.components.usage.usage_table import UsageTable


def _page_summary(items: list[dict]) -> dict:
    """仅基于当前页数据计算统计，与列表展示范围一致。"""
    count = len(items)
    successes = sum(1 for item in items if item.get("success"))
    durations = [item.get("duration_ms") for item in items if item.get("duration_ms") is not None]
    tokens = sum(item.get("total_tokens") or 0 for item in items)
    return {
        "request_count": count,
        "success_rate": successes / count if count else 0,
        "average_duration_ms": round(sum(durations) / len(durations)) if durations else 0,
        "total_tokens": tokens,
    }


class UsageView(QWidget):
    def __init__(self, client: ApiClient, parent=None) -> None:
        super().__init__(parent); self.client = client
        root = QVBoxLayout(self); root.setContentsMargins(20, 18, 20, 18); root.setSpacing(14)
        self.filter = UsageFilter(); root.addWidget(self.filter)
        self.summary = SummaryCards(); root.addWidget(self.summary)
        self.table = UsageTable(); root.addWidget(self.table)
        self.filter.refresh_button.clicked.connect(self.refresh); self.table.detail_requested.connect(self.show_detail); self.refresh()

    def refresh(self) -> None:
        try:
            data = self.client.get("/api/usage/records", params=self.filter.parameters())
            items = data["items"]
            self.table.set_records(items)
            self.summary.set_summary(_page_summary(items))
        except Exception as exc: QMessageBox.warning(self, "查询失败", str(exc))

    def show_detail(self, record_id: str) -> None:
        """拉取使用记录详情并打开结构化弹窗展示全部字段。"""
        try:
            record = self.client.get(f"/api/usage/records/{record_id}")
            UsageDetailDialog(record, self).exec()
        except Exception as exc: QMessageBox.warning(self, "读取失败", str(exc))
