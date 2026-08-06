from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class _StatCard(QFrame):
    """单个统计指标卡片：标题在上、数值在下。"""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("statTitle")
        self.value_label = QLabel("-")
        self.value_label.setObjectName("statValue")
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value) -> None:
        self.value_label.setText(str(value))


class SummaryCards(QWidget):
    """使用记录顶部的一组统计卡片。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._titles = ["请求数", "成功率", "平均耗时", "Token"]
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(12)
        self._cards: list[_StatCard] = []
        for title in self._titles:
            card = _StatCard(title)
            self.layout.addWidget(card)
            self._cards.append(card)

    def set_summary(self, summary: dict) -> None:
        """按卡片顺序填充请求数、成功率、平均耗时与 Token 合计。"""
        values = [
            summary.get("request_count", 0),
            f"{summary.get('success_rate', 0):.1%}",
            f"{summary.get('average_duration_ms', 0)} ms",
            summary.get("total_tokens", 0),
        ]
        for card, value in zip(self._cards, values):
            card.set_value(value)
