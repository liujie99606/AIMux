from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget


class UsageFilter(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        self.account = QLineEdit(); self.account.setPlaceholderText("账号 ID")
        self.model = QLineEdit(); self.model.setPlaceholderText("模型")
        self.type = QComboBox(); self.type.addItems(["全部类型", "openai", "anthropic"])
        self.success = QComboBox(); self.success.addItems(["全部结果", "成功", "失败"])
        self.started_after = QLineEdit(); self.started_after.setPlaceholderText("开始时间 ISO")
        self.started_before = QLineEdit(); self.started_before.setPlaceholderText("结束时间 ISO")
        self.refresh_button = QPushButton("查询")
        for control in [QLabel("筛选"), self.account, self.model, self.type, self.success, self.started_after, self.started_before, self.refresh_button]:
            layout.addWidget(control)

    def parameters(self, *, offset: int = 0, limit: int = 20) -> dict[str, str | bool | int]:
        """组装筛选条件和当前页的分页参数。"""
        params: dict[str, str | bool | int] = {"offset": max(offset, 0), "limit": limit}
        if self.account.text().strip(): params["account_id"] = self.account.text().strip()
        if self.model.text().strip(): params["model"] = self.model.text().strip()
        if self.type.currentText() != "全部类型": params["type"] = self.type.currentText()
        if self.success.currentIndex() > 0: params["success"] = self.success.currentIndex() == 1
        if self.started_after.text().strip(): params["started_after"] = self.started_after.text().strip()
        if self.started_before.text().strip(): params["started_before"] = self.started_before.text().strip()
        return params
