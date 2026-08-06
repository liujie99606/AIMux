from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem, QWidget


@dataclass(frozen=True)
class Column:
    """声明式表格的一列配置。

    - TextColumn：getter 返回字符串，自动创建 QTableWidgetItem。
    - WidgetColumn：getter 返回 QWidget，自动 setCellWidget。
    两种列共享同一个 Column，按 widget 字段区分渲染方式。
    """

    title: str
    getter: Callable[[dict], Any]
    widget: bool = False
    width: int | None = None
    stretch: bool = False


class DataTable(QTableWidget):
    """声明式表格基类：子类声明 COLUMNS 配置即可驱动渲染。

    用法：
        class MyTable(DataTable):
            COLUMNS = [Column("名称", lambda r: r["name"]), ...]
            some_signal = Signal(str)

            def set_data(self, rows): self._render(rows)

    复杂列（按钮、复选框等）用 widget=True，getter 返回 QWidget；
    该列的交互由子类在 getter 内部连接信号完成。
    """

    row_activated = Signal(int)

    def __init__(self, columns: list[Column] | None = None, parent=None) -> None:
        cols = columns if columns is not None else getattr(self, "COLUMNS", [])
        super().__init__(0, len(cols), parent)
        self._rows: list[dict] = []
        self._columns: list[Column] = list(cols)
        self.setHorizontalHeaderLabels([col.title for col in self._columns])
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        # 按列配置设置固定宽度或拉伸。
        for index, col in enumerate(self._columns):
            if col.width is not None:
                header.setSectionResizeMode(index, QHeaderView.ResizeMode.Interactive)
                self.setColumnWidth(index, col.width)
            elif col.stretch:
                header.setSectionResizeMode(index, QHeaderView.ResizeMode.Stretch)
        self.cellDoubleClicked.connect(self._on_double_click)

    def _render(self, rows: list[dict]) -> None:
        """按列配置通用渲染所有行，子类调此方法刷新数据。"""
        self._rows = list(rows)
        self.setRowCount(len(rows))
        for row, item in enumerate(rows):
            for col_index, column in enumerate(self._columns):
                value = column.getter(item)
                if column.widget:
                    if value is not None:
                        self.setCellWidget(row, col_index, value)
                else:
                    self.setItem(row, col_index, QTableWidgetItem(str(value)))

    @property
    def rows(self) -> list[dict]:
        """当前渲染的原始数据行列表。"""
        return self._rows

    def row_data(self, row: int) -> dict | None:
        """按行号取回原始数据，越界返回 None。"""
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return None

    def _on_double_click(self, row: int, _: int) -> None:
        self.row_activated.emit(row)
