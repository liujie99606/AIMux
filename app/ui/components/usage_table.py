from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem

from app.ui.formatting import format_time


class UsageTable(QTableWidget):
    detail_requested = Signal(str)
    def __init__(self, parent=None) -> None:
        super().__init__(0, 10, parent)
        self._records: list[dict] = []
        self.setHorizontalHeaderLabels(["时间", "账号", "类型", "模型", "接口", "结果", "耗时", "首Token", "推理强度", "Token"])
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.horizontalHeader().setStretchLastSection(True)
        # 时间列默认宽度调到 1.5 倍，避免格式化后显示不全。
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.setColumnWidth(0, 300)
        self.cellDoubleClicked.connect(self._open_detail)

    def set_records(self, records: list[dict]) -> None:
        self._records = records
        self.setRowCount(len(records))
        for row, item in enumerate(records):
            first_token = item.get("first_token_ms")
            values = [
                format_time(item.get("started_at")),
                item.get("account_name") or "-",
                item.get("account_type") or "-",
                item.get("model") or "-",
                item.get("endpoint") or "-",
                "成功" if item["success"] else "失败",
                f"{item.get('duration_ms') or 0} ms",
                f"{first_token} ms" if first_token is not None else "-",
                item.get("reasoning_effort") or "-",
                str(item.get("total_tokens") or 0),
            ]
            for column, value in enumerate(values): self.setItem(row, column, QTableWidgetItem(value))

    def _open_detail(self, row: int, _: int) -> None:
        if 0 <= row < len(self._records): self.detail_requested.emit(self._records[row]["id"])
