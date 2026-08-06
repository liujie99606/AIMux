from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from app.ui.client import ApiClient
from app.ui.components.account_form import AccountForm
from app.ui.components.account_table import AccountTable
from app.ui.components.account_test_dialog import AccountTestDialog
from app.ui.components.batch_toolbar import BatchToolbar
from app.ui.components.model_test_dialog import ModelTestDialog


class AccountsView(QWidget):
    """账号列表、按模型目录新增账号以及连接测试的桌面入口。"""

    def __init__(self, client: ApiClient, parent=None) -> None:
        super().__init__(parent)
        self.client = client
        self.accounts: dict[str, dict] = {}
        root = QVBoxLayout(self)
        tools = QHBoxLayout()
        self.type_filter = QComboBox()
        self.type_filter.addItems(["全部类型", "openai", "anthropic"])
        self.status_filter = QComboBox()
        self.status_filter.addItems(["全部状态", "active", "disabled"])
        refresh = QPushButton("刷新")
        add = QPushButton("新增账号")
        self.batch_toolbar = BatchToolbar()
        for widget in (QLabel("类型"), self.type_filter, QLabel("状态"), self.status_filter):
            tools.addWidget(widget)
        tools.addStretch()
        for widget in (self.batch_toolbar, add, refresh):
            tools.addWidget(widget)
        root.addLayout(tools)
        self.table = AccountTable()
        root.addWidget(self.table)
        refresh.clicked.connect(self.refresh)
        add.clicked.connect(self.add)
        self.batch_toolbar.test_requested.connect(self.batch_test)
        self.type_filter.currentIndexChanged.connect(self.refresh)
        self.status_filter.currentIndexChanged.connect(self.refresh)
        self.table.edit_requested.connect(self.edit)
        self.table.copy_requested.connect(self.copy)
        self.table.delete_requested.connect(self.delete)
        self.table.test_requested.connect(self.test)
        self.table.toggle_requested.connect(self.toggle)
        self.table.super_requested.connect(self.make_super)
        self.table.priority_changed.connect(self.change_priority)
        self.refresh()

    def _error(self, exc: Exception) -> None:
        """将 API 或表单异常转换为统一桌面错误提示。"""
        QMessageBox.warning(self, "操作失败", str(exc))

    def _models(self, account_type: str | None = None) -> list[dict]:
        """从模型目录读取指定类型的最新模型，避免界面使用陈旧缓存。"""
        params = {"type": account_type} if account_type else None
        return self.client.get("/api/models", params=params)["items"]

    def _pick_test_model(self, account_type: str) -> str | None:
        """弹出当前协议的模型列表；取消选择时不发送测试请求。"""
        models = self._models(account_type)
        if not models:
            QMessageBox.information(self, "测试账号", "该类型尚未维护模型，请先在模型维护页新增")
            return None
        dialog = ModelTestDialog(models, self)
        return dialog.selected_model() if dialog.exec() else None

    def refresh(self) -> None:
        """按筛选条件刷新账号表格。"""
        try:
            params = {"limit": 200}
            account_type = self.type_filter.currentText()
            status = self.status_filter.currentText()
            if account_type != "全部类型":
                params["type"] = account_type
            if status != "全部状态":
                params["status"] = status
            data = self.client.get("/api/accounts", params=params)
            self.accounts = {item["id"]: item for item in data["items"]}
            self.table.set_accounts(data["items"])
        except Exception as exc:
            self._error(exc)

    def add(self) -> None:
        """打开带协议模型列表的账号创建表单。"""
        try:
            form = AccountForm(self._models(), parent=self)
            if form.exec():
                self.client.post("/api/accounts", json=form.payload(True))
                self.refresh()
        except Exception as exc:
            self._error(exc)

    def edit(self, account_id: str) -> None:
        """编辑账号时保留其原有模型选择。"""
        try:
            form = AccountForm(self._models(), self.accounts[account_id], self)
            if form.exec():
                self.client.put(f"/api/accounts/{account_id}", json=form.payload(False))
                self.refresh()
        except Exception as exc:
            self._error(exc)

    def copy(self, account_id: str) -> None:
        """以现有账号数据填充新增账号表单，密钥需重新填写。"""
        try:
            form = AccountForm(self._models(), self.accounts[account_id], self, copy=True)
            if form.exec():
                self.client.post("/api/accounts", json=form.payload(True))
                self.refresh()
        except Exception as exc:
            self._error(exc)

    def delete(self, account_id: str) -> None:
        """在用户确认后删除指定账号。"""
        if QMessageBox.question(self, "删除账号", "确定删除该账号？") == QMessageBox.StandardButton.Yes:
            try:
                self.client.delete(f"/api/accounts/{account_id}")
                self.refresh()
            except Exception as exc:
                self._error(exc)

    def test(self, account_id: str) -> None:
        """在集成弹窗中选择模型、显示测试请求与响应详情。"""
        try:
            models = self._models(self.accounts[account_id]["type"])
            if not models:
                QMessageBox.information(self, "测试账号", "该类型尚未维护模型，请先在模型维护页新增")
                return
            dialog = AccountTestDialog(self.client, self.accounts[account_id], models, self)
            dialog.exec()
            self.refresh()
        except Exception as exc:
            self._error(exc)

    def batch_test(self) -> None:
        """同类型账号可批量选择一个模型测试，混合类型会明确提示拆分测试。"""
        ids = self.table.selected_ids()
        if not ids:
            QMessageBox.information(self, "批量测试", "请先勾选账号")
            return
        account_types = {self.accounts[account_id]["type"] for account_id in ids}
        if len(account_types) != 1:
            QMessageBox.information(self, "批量测试", "请按 OpenAI 或 Anthropic 分开选择账号")
            return
        try:
            model = self._pick_test_model(account_types.pop())
            if model is None:
                return
            result = self.client.post("/api/accounts/batch-test", json={"ids": ids, "model": model})
            succeeded = sum(item["success"] for item in result["items"])
            QMessageBox.information(self, "批量测试", f"完成: {succeeded}/{len(ids)} 通过")
            self.refresh()
        except Exception as exc:
            self._error(exc)

    def toggle(self, account_id: str) -> None:
        """切换账号启用状态。"""
        try:
            self.client.post(f"/api/accounts/{account_id}/toggle-status")
            self.refresh()
        except Exception as exc:
            self._error(exc)

    def make_super(self, account_id: str) -> None:
        """将账号置顶到最高人工优先级。"""
        try:
            self.client.post(f"/api/accounts/{account_id}/super-priority")
            self.refresh()
        except Exception as exc:
            self._error(exc)

    def change_priority(self, account_id: str, priority: int) -> None:
        """只在数值确实变化时保存表格内的优先级编辑。"""
        if account_id in self.accounts and self.accounts[account_id]["priority"] != priority:
            try:
                self.client.put(f"/api/accounts/{account_id}", json={"priority": priority})
                self.accounts[account_id]["priority"] = priority
            except Exception as exc:
                self._error(exc)
