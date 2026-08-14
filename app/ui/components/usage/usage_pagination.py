from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class UsagePagination(QWidget):
    """使用记录列表的页码控制器。"""

    page_requested = Signal(int)

    def __init__(self, page_size: int = 20, parent=None) -> None:
        super().__init__(parent)
        self.page_size = page_size
        self._page = 0
        self._total = 0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addStretch()
        self.previous_button = QPushButton("上一页")
        self.previous_button.clicked.connect(self._previous)
        self.page_label = QLabel()
        self.page_label.setMinimumWidth(150)
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.next_button = QPushButton("下一页")
        self.next_button.clicked.connect(self._next)
        layout.addWidget(self.previous_button)
        layout.addWidget(self.page_label)
        layout.addWidget(self.next_button)

    @property
    def page(self) -> int:
        """返回当前页的零基索引。"""
        return self._page

    def set_total(self, total: int, page: int | None = None) -> None:
        """根据总记录数刷新页码状态，并修正越界页码。"""
        self._total = max(total, 0)
        total_pages = self.total_pages
        requested_page = self._page if page is None else max(page, 0)
        self._page = min(requested_page, total_pages - 1) if total_pages else 0
        self._update_controls()

    @property
    def total_pages(self) -> int:
        """返回总页数。"""
        return (self._total + self.page_size - 1) // self.page_size

    def _update_controls(self) -> None:
        total_pages = self.total_pages
        self.page_label.setText(f"第 {self._page + 1} / {max(total_pages, 1)} 页，共 {self._total} 条")
        self.previous_button.setEnabled(self._page > 0)
        self.next_button.setEnabled(self._page + 1 < total_pages)

    def _previous(self) -> None:
        if self._page > 0:
            self._page -= 1
            self._update_controls()
            self.page_requested.emit(self._page)

    def _next(self) -> None:
        if self._page + 1 < self.total_pages:
            self._page += 1
            self._update_controls()
            self.page_requested.emit(self._page)
