from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from app.ui.components.common.data_table import Column, DataTable
from app.ui.formatting import format_percentage, format_token_count


class AccountTokenStatisticsTable(DataTable):
    """展示各启用账号今日 Token 汇总。"""

    COLUMNS = [
        Column("账号", lambda row: row.get("account_name") or "-", width=180),
        Column("类型", lambda row: row.get("account_type") or "-", width=90),
        Column("优先级", lambda row: row.get("priority", 0), width=75),
        Column("总Token", lambda row: format_token_count(row.get("total_tokens"))),
        Column("总输入", lambda row: format_token_count(row.get("input_tokens"))),
        Column("总输出", lambda row: format_token_count(row.get("output_tokens"))),
        Column("总缓存", lambda row: format_token_count(row.get("cached_tokens"))),
        Column("缓存率", lambda row: format_percentage(row.get("cache_rate")), stretch=True),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)

    def set_statistics(self, statistics: list[dict]) -> None:
        """刷新各账号统计，并统一右对齐数值列。"""
        self._render(statistics)
        for row in range(self.rowCount()):
            for column in range(2, self.columnCount()):
                item = self.item(row, column)
                if item is not None:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
