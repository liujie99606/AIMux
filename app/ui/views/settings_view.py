from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QFormLayout, QLineEdit, QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget

from app.ui.client import ApiClient


class SettingsView(QWidget):
    def __init__(self, client: ApiClient, parent=None) -> None:
        super().__init__(parent); self.client = client; root = QVBoxLayout(self); root.setContentsMargins(20, 18, 20, 18); root.setSpacing(14); form = QFormLayout(); form.setSpacing(10); root.addLayout(form)
        self.host = QLineEdit(); self.port = QSpinBox(); self.port.setRange(1, 65535); self.db_path = QLineEdit(); self.timeout = QSpinBox(); self.timeout.setRange(1, 3600); self.first_timeout = QSpinBox(); self.first_timeout.setRange(1, 3600); self.retries = QSpinBox(); self.retries.setRange(1, 20); self.token = QLineEdit(); self.token.setEchoMode(QLineEdit.EchoMode.Password); self.launch_at_login = QCheckBox("开机后自动启动 AIMux")
        for label, field in [("监听地址", self.host), ("端口", self.port), ("数据库路径", self.db_path), ("上游超时（秒）", self.timeout), ("首字超时（秒）", self.first_timeout), ("总尝试次数", self.retries), ("本地令牌", self.token), ("开机自启", self.launch_at_login)]: form.addRow(label, field)
        save = QPushButton("保存设置"); root.addWidget(save); root.addStretch(); save.clicked.connect(self.save); self.load()

    def load(self) -> None:
        try:
            data = self.client.get("/api/settings"); self.host.setText(data["host"]); self.port.setValue(data["port"]); self.db_path.setText(data["db_path"]); self.timeout.setValue(data["upstream_timeout_seconds"]); self.first_timeout.setValue(data["first_token_timeout_seconds"]); self.retries.setValue(data["request_retry_attempts"]); self.token.setText(data["local_token"]); self.launch_at_login.setChecked(data["launch_at_login"])
        except Exception as exc: QMessageBox.warning(self, "读取失败", str(exc))

    def save(self) -> None:
        payload = {"host": self.host.text().strip(), "port": self.port.value(), "db_path": self.db_path.text().strip(), "upstream_timeout_seconds": self.timeout.value(), "first_token_timeout_seconds": self.first_timeout.value(), "request_retry_attempts": self.retries.value(), "local_token": self.token.text(), "launch_at_login": self.launch_at_login.isChecked()}
        try: self.client.put("/api/settings", json=payload); self.client.token = payload["local_token"]; QMessageBox.information(self, "设置", "设置已保存，监听地址、端口和数据库路径将在下次启动时生效。")
        except Exception as exc: QMessageBox.warning(self, "保存失败", str(exc))
