from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHeaderView, QTableWidgetItem, QWidget

from app.ui.components.common.data_table import Column, DataTable
from app.ui.formatting import format_duration_ms, format_time

_STATUS_COUNT = 30
_STATUS_WIDTH = 25
_EMPTY_COLOR = "#59606b"
_SUCCESS_COLOR = "#2e9f63"
_FAILURE_COLOR = "#c43d4b"


class MonitorTable(DataTable):
    """以监控矩阵展示启用账号最近三十次检查结果。"""

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
        *[
            Column(str(index + 1), lambda row, index=index: row["_records"][index], width=_STATUS_WIDTH)
            for index in range(_STATUS_COUNT)
        ],
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.setMinimumWidth(1180)
        self.verticalHeader().setDefaultSectionSize(34)
        self.verticalHeader().setVisible(False)
        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        for column in range(6, self.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.setColumnWidth(column, _STATUS_WIDTH)

    def set_records(self, accounts: list[dict]) -> None:
        """渲染账号信息与按旧到新排列的三十列监控状态。"""
        self._render([self._prepare(account) for account in accounts])
        for row in range(self.rowCount()):
            for column in range(6, self.columnCount()):
                self._render_status_cell(row, column)

    @staticmethod
    def _prepare(account: dict) -> dict:
        """将单账号记录补齐为固定数量的状态单元格。"""
        records = account.get("records", [])[-_STATUS_COUNT:]
        padded_records = [None] * (_STATUS_COUNT - len(records)) + records
        latest = records[-1] if records else {}
        result = "-"
        result_color: QColor | None = None
        if latest:
            success = bool(latest.get("success"))
            result = "成功" if success else "失败"
            result_color = QColor(_SUCCESS_COLOR if success else _FAILURE_COLOR)
        prepared = dict(account)
        prepared["_latest"] = latest
        prepared["_records"] = padded_records
        prepared["_result"] = result
        prepared["_result_color"] = result_color
        return prepared

    def _render_status_cell(self, row: int, column: int) -> None:
        """设置一个固定大小的监控状态格及其悬停详情。"""
        record = self.rows[row]["_records"][column - 6]
        item = self.item(row, column)
        if item is None:
            return
        color = _EMPTY_COLOR
        tooltip = "暂无监控记录"
        if record is not None:
            success = bool(record.get("success"))
            color = _SUCCESS_COLOR if success else _FAILURE_COLOR
            details = [
                f"检查时间：{format_time(record.get('checked_at'))}",
                f"耗时：{format_duration_ms(record.get('duration_ms'))}",
                f"状态码：{record.get('status_code') or '-'}",
            ]
            if not success:
                details.append(
                    f"错误：{record.get('error_message') or record.get('error_code') or '-'}"
                )
            tooltip = "\n".join(details)
        item.setText("")
        item.setToolTip(tooltip)
        item.setBackground(QColor(color))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
