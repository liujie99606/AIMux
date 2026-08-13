from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from app.ui.formatting import format_duration_ms, format_time

_CELL_COUNT = 30
_CELL_WIDTH = 25
_CELL_HEIGHT = 25
_CELL_SPACING = 0
_GRID_MIN_WIDTH = _CELL_COUNT * _CELL_WIDTH + (_CELL_COUNT - 1) * _CELL_SPACING


class MonitorStatusGrid(QWidget):
    """固定三十格的账号监控状态条。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(_GRID_MIN_WIDTH)
        self.setFixedHeight(_CELL_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(_CELL_SPACING)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._cells: list[QLabel] = []
        for _ in range(_CELL_COUNT):
            cell = QLabel()
            cell.setFixedSize(_CELL_WIDTH, _CELL_HEIGHT)
            cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell.setStyleSheet("background: #59606b;")
            # 固定状态格左对齐，避免父表格列变宽时把剩余空间分摊到格子之间。
            self._layout.addWidget(cell)
            self._cells.append(cell)

    def set_records(self, records: list[dict]) -> None:
        """按旧到新顺序渲染最近监控结果，缺失记录使用灰色。"""
        records = records[-_CELL_COUNT:]
        offset = _CELL_COUNT - len(records)
        for index, cell in enumerate(self._cells):
            record = records[index - offset] if index >= offset else None
            if record is None:
                cell.setStyleSheet("background: #59606b;")
                cell.setToolTip("暂无监控记录")
                continue
            success = bool(record.get("success"))
            color = "#2e9f63" if success else "#c43d4b"
            cell.setStyleSheet(f"background: {color};")
            details = [
                f"检查时间：{format_time(record.get('checked_at'))}",
                f"耗时：{format_duration_ms(record.get('duration_ms'))}",
                f"状态码：{record.get('status_code') or '-'}",
            ]
            if not success:
                details.append(f"错误：{record.get('error_message') or record.get('error_code') or '-'}")
            cell.setToolTip("\n".join(details))
