from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget

from app.ui.components.common.data_table import Column, DataTable
from app.ui.components.monitor_status_grid import MonitorStatusGrid
from app.ui.formatting import format_duration_ms, format_time

_STATUS_COUNT = 30
_SUCCESS_COLOR = "#2e9f63"
_FAILURE_COLOR = "#c43d4b"


class MonitorTable(DataTable):
    """以表格展示启用账号及其最近三十次监控状态。"""

    COLUMNS = [
        Column("账号", lambda row: row.get("account_name") or "-", width=150),
        Column("类型", lambda row: row.get("account_type") or "-", width=80),
        Column(
            "测试模型",
            lambda row: row.get("model") or row["_latest"].get("model") or "-",
            width=160,
        ),
        Column("最近检查", lambda row: format_time(row["_latest"].get("checked_at")), width=165),
        Column("耗时", lambda row: format_duration_ms(row["_latest"].get("duration_ms")), width=75),
        Column("结果", lambda row: row["_result"], width=75, color=lambda row: row["_result_color"]),
        Column("最近30次检测记录", lambda row: row["_status_grid"], widget=True, stretch=True),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.verticalHeader().setDefaultSectionSize(38)
        self.verticalHeader().setVisible(False)

    def set_records(self, accounts: list[dict]) -> None:
        """渲染账号信息与按旧到新排列的三十格状态条。"""
        self._render([self._prepare(account) for account in accounts])

    @staticmethod
    def _prepare(account: dict) -> dict:
        """将单账号记录补齐为固定数量的状态单元格。"""
        records = account.get("records", [])[-_STATUS_COUNT:]
        latest = records[-1] if records else {}
        result = "-"
        result_color: QColor | None = None
        if latest:
            success = bool(latest.get("success"))
            result = "成功" if success else "失败"
            result_color = QColor(_SUCCESS_COLOR if success else _FAILURE_COLOR)
        prepared = dict(account)
        prepared["_latest"] = latest
        prepared["_result"] = result
        prepared["_result_color"] = result_color
        status_grid = MonitorStatusGrid()
        status_grid.set_records(records)
        prepared["_status_grid"] = status_grid
        return prepared
