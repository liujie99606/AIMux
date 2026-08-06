from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class SummaryCards(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent); self.layout = QHBoxLayout(self); self.labels = []
        for title in ["请求数", "成功率", "平均耗时", "Token"]:
            label = QLabel(f"{title}: -"); self.layout.addWidget(label); self.labels.append(label)

    def set_summary(self, summary: dict) -> None:
        values = [summary.get("request_count", 0), f"{summary.get('success_rate', 0):.1%}", f"{summary.get('average_duration_ms', 0)} ms", summary.get("total_tokens", 0)]
        for label, value in zip(self.labels, values): label.setText(f"{label.text().split(':')[0]}: {value}")
