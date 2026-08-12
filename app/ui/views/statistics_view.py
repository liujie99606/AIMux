from __future__ import annotations

from PySide6.QtWidgets import QLabel, QMessageBox, QVBoxLayout, QWidget

from app.ui.client import ApiClient
from app.ui.components.account_token_statistics_table import AccountTokenStatisticsTable
from app.ui.components.common.background_loader import BackgroundLoader
from app.ui.components.statistics_cards import TokenStatisticsCards


class StatisticsView(QWidget):
    """展示本地今日和昨日的 Token 使用统计。"""

    def __init__(self, client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.client = client
        self.loader = BackgroundLoader(self)
        self.loader.loaded.connect(self._apply_statistics)
        self.loader.failed.connect(self._error)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(18)
        title = QLabel("数据统计")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        self.cards = TokenStatisticsCards(self)
        layout.addWidget(self.cards)
        account_title = QLabel("启用账号今日统计")
        account_title.setObjectName("statisticsGroupTitle")
        layout.addWidget(account_title)
        self.account_table = AccountTokenStatisticsTable(self)
        layout.addWidget(self.account_table, 1)
        self.refresh()

    def refresh(self) -> None:
        """读取并展示最新的今日和昨日 Token 汇总。"""
        self.loader.load(lambda: self.client.get("/api/usage/statistics"))

    def _apply_statistics(self, data: object) -> None:
        """在主线程渲染后台查询返回的 Token 汇总。"""
        payload = data if isinstance(data, dict) else {}
        self.cards.set_statistics(payload)
        accounts = payload.get("accounts_today", [])
        self.account_table.set_statistics(accounts if isinstance(accounts, list) else [])

    def _error(self, exc: object) -> None:
        """显示后台统计查询失败原因。"""
        QMessageBox.warning(self, "查询失败", str(exc))
