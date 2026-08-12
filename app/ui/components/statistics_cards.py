from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.ui.formatting import format_percentage, format_token_count


class _StatisticCard(QFrame):
    """展示单项数据统计值。"""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setObjectName("statTitle")
        self.value_label = QLabel("0")
        self.value_label.setObjectName("statValue")
        layout.addWidget(title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value: int | float | None) -> None:
        """按统一规则格式化并显示 Token 数。"""
        self.value_label.setText(format_token_count(value))

    def set_percentage(self, value: float | None) -> None:
        """按统一规则格式化并显示百分比。"""
        self.value_label.setText(format_percentage(value))


class TokenStatisticsCards(QWidget):
    """按今日和昨日分组展示 Token 汇总和缓存率。"""

    _metrics = (
        ("总Token", "total_tokens"),
        ("总输入", "input_tokens"),
        ("总输出", "output_tokens"),
        ("总缓存", "cached_tokens"),
        ("缓存率", "cache_rate"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        self._groups: dict[str, dict[str, _StatisticCard]] = {}
        for key, title in (("yesterday", "昨日"), ("today", "今日")):
            group, cards = self._create_group(title)
            layout.addWidget(group)
            self._groups[key] = cards

    def _create_group(self, title: str) -> tuple[QWidget, dict[str, _StatisticCard]]:
        """创建包含四项指标的日期分组。"""
        group = QWidget(self)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        heading = QLabel(title)
        heading.setObjectName("statisticsGroupTitle")
        layout.addWidget(heading)
        cards_layout = QHBoxLayout()
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(12)
        cards: dict[str, _StatisticCard] = {}
        for metric_title, metric_key in self._metrics:
            card = _StatisticCard(metric_title, group)
            cards_layout.addWidget(card)
            cards[metric_key] = card
        layout.addLayout(cards_layout)
        return group, cards

    def set_statistics(self, statistics: dict) -> None:
        """按接口返回的今日和昨日数据刷新卡片。"""
        for group_key, cards in self._groups.items():
            values = statistics.get(group_key, {})
            for metric_key, card in cards.items():
                if metric_key == "cache_rate":
                    card.set_percentage(values.get(metric_key))
                else:
                    card.set_value(values.get(metric_key, 0))
