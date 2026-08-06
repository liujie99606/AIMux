from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget

from app.ui.client import ApiClient
from app.ui.components.account_form import AccountForm
from app.ui.components.account_table import AccountTable
from app.ui.components.batch_toolbar import BatchToolbar


class AccountsView(QWidget):
    def __init__(self, client: ApiClient, parent=None) -> None:
        super().__init__(parent); self.client = client; self.accounts: dict[str, dict] = {}
        root = QVBoxLayout(self)
        tools = QHBoxLayout(); self.type_filter = QComboBox(); self.type_filter.addItems(["全部类型", "openai", "anthropic"])
        self.status_filter = QComboBox(); self.status_filter.addItems(["全部状态", "active", "disabled"])
        refresh = QPushButton("刷新"); add = QPushButton("新增账号"); self.batch_toolbar = BatchToolbar()
        tools.addWidget(QLabel("类型")); tools.addWidget(self.type_filter); tools.addWidget(QLabel("状态")); tools.addWidget(self.status_filter); tools.addStretch(); tools.addWidget(self.batch_toolbar); tools.addWidget(add); tools.addWidget(refresh)
        root.addLayout(tools); self.table = AccountTable(); root.addWidget(self.table)
        refresh.clicked.connect(self.refresh); add.clicked.connect(self.add); self.batch_toolbar.test_requested.connect(self.batch_test)
        self.type_filter.currentIndexChanged.connect(self.refresh); self.status_filter.currentIndexChanged.connect(self.refresh)
        self.table.edit_requested.connect(self.edit); self.table.delete_requested.connect(self.delete); self.table.test_requested.connect(self.test); self.table.toggle_requested.connect(self.toggle); self.table.super_requested.connect(self.make_super); self.table.priority_changed.connect(self.change_priority)
        self.refresh()

    def _error(self, exc: Exception) -> None: QMessageBox.warning(self, "操作失败", str(exc))
    def refresh(self) -> None:
        try:
            params = {"limit": 200}; typ = self.type_filter.currentText(); status = self.status_filter.currentText()
            if typ != "全部类型": params["type"] = typ
            if status != "全部状态": params["status"] = status
            data = self.client.get("/api/accounts", params=params); self.accounts = {item["id"]: item for item in data["items"]}; self.table.set_accounts(data["items"])
        except Exception as exc: self._error(exc)

    def add(self) -> None:
        form = AccountForm(parent=self)
        if form.exec():
            try: self.client.post("/api/accounts", json=form.payload(True)); self.refresh()
            except Exception as exc: self._error(exc)

    def edit(self, account_id: str) -> None:
        form = AccountForm(self.accounts[account_id], self)
        if form.exec():
            try: self.client.put(f"/api/accounts/{account_id}", json=form.payload(False)); self.refresh()
            except Exception as exc: self._error(exc)

    def delete(self, account_id: str) -> None:
        if QMessageBox.question(self, "删除账号", "确定删除该账号？") == QMessageBox.StandardButton.Yes:
            try: self.client.delete(f"/api/accounts/{account_id}"); self.refresh()
            except Exception as exc: self._error(exc)

    def test(self, account_id: str) -> None:
        try:
            result = self.client.post(f"/api/accounts/{account_id}/test", json={})
            QMessageBox.information(self, "测试结果", "测试通过" if result["success"] else f"测试失败: {result.get('error_message')}"); self.refresh()
        except Exception as exc: self._error(exc)

    def batch_test(self) -> None:
        ids = self.table.selected_ids()
        if not ids: return QMessageBox.information(self, "批量测试", "请先勾选账号")
        try:
            result = self.client.post("/api/accounts/batch-test", json={"ids": ids})
            succeeded = sum(item["success"] for item in result["items"]); QMessageBox.information(self, "批量测试", f"完成: {succeeded}/{len(ids)} 通过"); self.refresh()
        except Exception as exc: self._error(exc)

    def toggle(self, account_id: str) -> None:
        try: self.client.post(f"/api/accounts/{account_id}/toggle-status"); self.refresh()
        except Exception as exc: self._error(exc)

    def make_super(self, account_id: str) -> None:
        try: self.client.post(f"/api/accounts/{account_id}/super-priority"); self.refresh()
        except Exception as exc: self._error(exc)

    def change_priority(self, account_id: str, priority: int) -> None:
        if account_id in self.accounts and self.accounts[account_id]["priority"] != priority:
            try: self.client.put(f"/api/accounts/{account_id}", json={"priority": priority}); self.accounts[account_id]["priority"] = priority
            except Exception as exc: self._error(exc)
