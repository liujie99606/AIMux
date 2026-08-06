from __future__ import annotations

from PySide6.QtCore import Signal

from app.ui.components.data_table import Column, DataTable
from app.ui.formatting import format_time


def _first_token(record: dict) -> str:
    """首 Token 用时有值带单位，无值显示占位符。"""
    value = record.get("first_token_ms")
    return f"{value} ms" if value is not None else "-"


class UsageTable(DataTable):
    """使用记录表格，列配置声明式驱动渲染。"""

    detail_requested = Signal(str)

    COLUMNS = [
        Column("时间", lambda r: format_time(r.get("started_at")), width=180),
        Column("账号", lambda r: r.get("account_name") or "-"),
        Column("类型", lambda r: r.get("account_type") or "-"),
        Column("模型", lambda r: r.get("model") or "-"),
        Column("接口", lambda r: r.get("endpoint") or "-"),
        Column("结果", lambda r: "成功" if r["success"] else "失败"),
        Column("耗时", lambda r: f"{r.get('duration_ms') or 0} ms"),
        Column("首Token", _first_token),
        Column("推理强度", lambda r: r.get("reasoning_effort") or "-"),
        # Column("Token", lambda r: str(r.get("total_tokens") or 0)),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)
        self.row_activated.connect(self._open_detail)

    def set_records(self, records: list[dict]) -> None:
        """刷新使用记录列表。"""
        self._render(records)

    def _open_detail(self, row: int) -> None:
        data = self.row_data(row)
        if data is not None:
            self.detail_requested.emit(data["id"])
