from __future__ import annotations

from PySide6.QtWidgets import QLabel, QMessageBox, QVBoxLayout, QWidget

from app.ui.client import ApiClient
from app.ui.components.statistics_cards import TokenStatisticsCards


class StatisticsView(QWidget):
    """展示本地今日和昨日的 Token 使用统计。"""

    def __init__(self, client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.client = client
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(18)
        title = QLabel("数据统计")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        self.cards = TokenStatisticsCards(self)
        layout.addWidget(self.cards)
        self.refresh()

    def refresh(self) -> None:
        """读取并展示最新的今日和昨日 Token 汇总。"""
        try:
            self.cards.set_statistics(self.client.get("/api/usage/statistics"))
        except Exception as exc:
            QMessageBox.warning(self, "查询失败", str(exc))
