from __future__ import annotations

from datetime import datetime, timezone, timedelta

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem

# 使用记录统一按本地时区展示时间。
_LOCAL_TZ = timezone(timedelta(hours=8))


def _format_time(value: str | None) -> str:
    """把 UTC ISO 字符串格式化为本地时间 YYYY-MM-DD HH:MM:SS。"""
    if not value:
        return "-"
    try:
        # 兼容带 Z 与带 +00:00 的两种写法。
        text = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(_LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return value


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
                _format_time(item.get("started_at")),
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
