from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QPlainTextEdit, QSpinBox


class AccountForm(QDialog):
    def __init__(self, account: dict | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("编辑账号" if account else "新增账号")
        self.setMinimumWidth(460)
        form = QFormLayout(self)
        self.name = QLineEdit(account.get("name", "") if account else "")
        self.type = QComboBox(); self.type.addItems(["openai", "anthropic"])
        if account: self.type.setCurrentText(account["type"])
        self.base_url = QLineEdit(account.get("base_url", "") if account else "")
        self.api_key = QLineEdit(); self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("新增时必填；编辑时留空保持不变")
        self.priority = QSpinBox(); self.priority.setRange(0, 9); self.priority.setValue(account.get("priority", 5) if account else 5)
        self.models = QLineEdit(", ".join(account.get("supported_models") or []) if account else "")
        self.tags = QLineEdit(", ".join(account.get("tags") or []) if account else "")
        self.notes = QPlainTextEdit((account.get("notes") or "") if account else "")
        form.addRow("名称", self.name); form.addRow("类型", self.type); form.addRow("上游地址", self.base_url)
        form.addRow("API 密钥", self.api_key); form.addRow("优先级", self.priority); form.addRow("支持模型", self.models)
        form.addRow("标签", self.tags); form.addRow("备注", self.notes)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); form.addRow(buttons)

    def payload(self, creating: bool) -> dict:
        split = lambda value: [part.strip() for part in value.split(",") if part.strip()] or None
        result = {"name": self.name.text().strip(), "type": self.type.currentText(), "base_url": self.base_url.text().strip(), "priority": self.priority.value(), "supported_models": split(self.models.text()), "tags": split(self.tags.text()), "notes": self.notes.toPlainText().strip() or None}
        if self.api_key.text(): result["api_key"] = self.api_key.text()
        if creating and not result.get("api_key"): raise ValueError("请输入 API 密钥")
        if not result["name"] or not result["base_url"]: raise ValueError("名称和上游地址不能为空")
        return result
