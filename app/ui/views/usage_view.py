from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QVBoxLayout, QWidget

from app.ui.client import ApiClient
from app.ui.components.common.background_loader import BackgroundLoader
from app.ui.components.usage.summary_card import SummaryCards
from app.ui.components.usage.usage_detail_dialog import UsageDetailDialog
from app.ui.components.usage.usage_filter import UsageFilter
from app.ui.components.usage.usage_pagination import UsagePagination
from app.ui.components.usage.usage_table import UsageTable

_PAGE_SIZE = 20


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
    def __init__(self, client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.client = client
        self.loader = BackgroundLoader(self)
        self.loader.loaded.connect(self._apply_records)
        self.loader.failed.connect(self._query_error)
        self._requested_page = 0
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)
        self.filter = UsageFilter()
        root.addWidget(self.filter)
        self.summary = SummaryCards()
        root.addWidget(self.summary)
        self.table = UsageTable()
        root.addWidget(self.table)
        self.pagination = UsagePagination(_PAGE_SIZE)
        root.addWidget(self.pagination)
        self.filter.refresh_button.clicked.connect(self._refresh_from_first_page)
        self.filter.reset_requested.connect(self._refresh_from_first_page)
        self.filter.cleanup_requested.connect(self.cleanup_expired_records)
        self.pagination.page_requested.connect(self.refresh)
        self.table.detail_requested.connect(self.show_detail)
        self.refresh()

    def _refresh_from_first_page(self) -> None:
        """筛选条件变化后从第一页重新查询。"""
        self.refresh(0)

    def refresh(self, page: int | None = None) -> None:
        """按当前页查询使用记录。"""
        self.table.set_loading(True)
        current_page = self.pagination.page if page is None else max(page, 0)
        self._requested_page = current_page
        params = self.filter.parameters(offset=current_page * _PAGE_SIZE, limit=_PAGE_SIZE)
        self.loader.load(
            lambda: self.client.get(
                "/api/usage/records",
                params=params,
            )
        )

    def _apply_records(self, data: object) -> None:
        """在主线程渲染后台查询返回的当前页记录。"""
        payload = data if isinstance(data, dict) else {}
        items = payload.get("items", [])
        self.table.set_loading(False)
        self.table.set_records(items)
        self.summary.set_summary(_page_summary(items))
        self.pagination.set_total(payload.get("total", 0), self._requested_page)

    def _query_error(self, exc: object) -> None:
        """显示后台列表查询失败原因。"""
        self.table.set_loading(False)
        QMessageBox.warning(self, "查询失败", str(exc))

    def show_detail(self, record_id: str) -> None:
        """拉取使用记录详情并打开结构化弹窗展示全部字段。"""
        try:
            record = self.client.get(f"/api/usage/records/{record_id}")
            UsageDetailDialog(record, self).exec()
        except Exception as exc:
            QMessageBox.warning(self, "读取失败", str(exc))

    def cleanup_expired_records(self) -> None:
        """经用户确认后删除严格早于三天前的使用记录。"""
        result = QMessageBox.question(
            self,
            "清除历史数据",
            "将永久删除超过 3 天的使用记录，且无法恢复。确定继续吗？",
        )
        if result != QMessageBox.StandardButton.Yes:
            return
        try:
            response = self.client.delete("/api/usage/records/expired")
            QMessageBox.information(self, "清除完成", f"已清除 {response.get('deleted', 0)} 条使用记录。")
            self._refresh_from_first_page()
        except Exception as exc:
            QMessageBox.warning(self, "清除失败", str(exc))
