from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from app.ui.components.common.data_table import Column, DataTable
from app.ui.formatting import format_time


def _first_token(record: dict) -> str:
    """首 Token 用时有值带单位，无值显示占位符。"""
    value = record.get("first_token_ms")
    return f"{value} ms" if value is not None else "-"


class UsageTable(DataTable):
    """使用记录表格，列配置声明式驱动渲染。"""

    detail_requested = Signal(str)

    COLUMNS = [
        Column("时间", lambda r: format_time(r.get("started_at")), width=150),
        Column("账号", lambda r: r.get("account_name") or "-"),
        Column("类型", lambda r: r.get("account_type") or "-"),
        Column("模型", lambda r: r.get("model") or "-"),
        Column("接口", lambda r: r.get("endpoint") or "-"),
        Column("结果", lambda r: "成功" if r["success"] else "失败"),
        Column("耗时", lambda r: f"{r.get('duration_ms') or 0} ms"),
        Column("首Token", _first_token),
        Column("推理强度", lambda r: r.get("reasoning_effort") or "-"),
        Column("操作", lambda r: r["_actions"], widget=True, stretch=True),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)
        self.row_activated.connect(self._open_detail)

    def set_records(self, records: list[dict]) -> None:
        """刷新使用记录列表，操作按钮在预处理中连接信号。"""
        self._render([self._prepare(record) for record in records])

    def _prepare(self, record: dict) -> dict:
        """为单行生成详情按钮并连接信号。"""
        actions = QWidget()
        layout = QHBoxLayout(actions)
        layout.setContentsMargins(0, 0, 0, 0)
        detail = QPushButton("详情")
        detail.clicked.connect(lambda _, rid=record["id"]: self.detail_requested.emit(rid))
        layout.addWidget(detail)
        prepared = dict(record)
        prepared["_actions"] = actions
        return prepared

    def _open_detail(self, row: int) -> None:
        data = self.row_data(row)
        if data is not None:
            self.detail_requested.emit(data["id"])
