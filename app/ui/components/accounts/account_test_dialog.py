from __future__ import annotations

import json

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from app.ui.client import ApiClient


class AccountTestWorker(QThread):
    """在后台逐个执行账号测试，避免网络请求阻塞 Qt 主线程。"""

    result_received = Signal(str, str, dict)
    request_failed = Signal(str, str, str)
    progress_changed = Signal(int, int, str)

    def __init__(self, client: ApiClient, accounts: list[dict], model: str | None) -> None:
        super().__init__()
        self.client = client
        self.accounts = accounts
        self.model = model

    def run(self) -> None:
        """逐个发起请求，单个账号异常时继续测试剩余账号。"""
        total = len(self.accounts)
        for index, account in enumerate(self.accounts, start=1):
            account_id = account["id"]
            account_name = account.get("name", account_id)
            self.progress_changed.emit(index, total, account_name)
            try:
                result = self.client.post(
                    f"/api/accounts/{account_id}/test",
                    json={"model": self.model},
                )
                self.result_received.emit(account_id, account_name, result)
            except Exception as exc:
                self.request_failed.emit(account_id, account_name, str(exc))


class AccountTestDialog(QDialog):
    """账号连接测试弹窗：选择模型并展示请求与响应详情。"""

    def __init__(self, client: ApiClient, account: dict | list[dict], models: list[dict], parent=None) -> None:
        super().__init__(parent)
        self.client = client
        self.accounts = account if isinstance(account, list) else [account]
        self.account = self.accounts[0]
        self._worker: AccountTestWorker | None = None
        title = "批量测试账号" if len(self.accounts) > 1 else f"测试账号 · {self.account.get('name', '')}"
        self.setWindowTitle(title)
        self.setMinimumSize(900, 700)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        selector = QHBoxLayout()
        selector.setSpacing(10)
        selector.addWidget(QLabel("选择测试模型"))
        self.model = QComboBox()
        self.model.setMinimumWidth(240)
        configured_defaults = {
            str(item["test_default_model"])
            for item in self.accounts
            if item.get("test_default_model")
        }
        if configured_defaults:
            self.model.addItem("使用账号默认模型", None)
            for item in models:
                self.model.addItem(item["name"], item["name"])
            self.model.setCurrentIndex(0)
        else:
            for item in models:
                self.model.addItem(item["name"], item["name"])
            if self.model.count():
                self.model.setCurrentIndex(0)
        selector.addWidget(self.model)
        selector.addWidget(QLabel("测试请求形态"))
        self.request_type = QLabel(self._detect_request_type())
        selector.addWidget(self.request_type)
        selector.addStretch()
        self.test_btn = QPushButton("开始测试")
        self.test_btn.clicked.connect(self._run_test)
        selector.addWidget(self.test_btn)
        layout.addLayout(selector)

        self.progress = QProgressBar()
        self.progress.setRange(0, len(self.accounts))
        self.progress.setValue(0)
        self.progress.setFormat("等待测试")
        layout.addWidget(self.progress)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        # 深色背景等宽字体，便于阅读请求/响应文本。
        self.log.setStyleSheet(
            "QTextEdit { background-color: #1e1e1e; color: #d4d4d4;"
            " border: 1px solid #414854; border-radius: 5px;"
            " font-family: Consolas, 'Courier New', monospace; font-size: 12px; }"
        )
        layout.addWidget(self.log)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        self.close_button = buttons.button(QDialogButtonBox.StandardButton.Close)
        layout.addWidget(buttons)

        self._endpoint = (
            "/v1/messages" if self.account["type"] == "anthropic" else "/v1/chat/completions"
        )

    def _detect_request_type(self) -> str:
        """根据账号类型显示对应的请求形态名称。"""
        return "Messages" if self.account["type"] == "anthropic" else "Chat Completions"

    def _request_body(self, model: str | None) -> dict:
        """构造与后端 _test_one 一致的最小测试请求体。"""
        body = {"max_tokens": 1, "messages": [{"role": "user", "content": "ping"}]}
        if model:
            body["model"] = model
        return body

    def _append_html(self, html: str) -> None:
        """追加一行 HTML 到日志区。"""
        self.log.append(html)

    def _append_block(self, text: str) -> None:
        """追加一段普通文本，对 HTML 特殊字符转义并保留换行。"""
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        self._append_html(escaped)

    def _run_test(self) -> None:
        model_name = self.model.currentData()
        body = self._request_body(model_name)
        self.log.clear()
        self.test_btn.setEnabled(False)
        self.model.setEnabled(False)
        self.close_button.setEnabled(False)
        self.progress.setValue(0)
        self.progress.setFormat("准备测试")
        if len(self.accounts) > 1:
            self._append_html(f'<span style="color:#9cdcfe">开始批量测试:</span> {len(self.accounts)} 个账号')
        else:
            self._append_html(f'<span style="color:#9cdcfe">开始测试账号:</span> {self.account.get("name", "")}')
        self._append_html(f'<span style="color:#9cdcfe">账号类型:</span> {self.account.get("type", "")}')
        self._append_html(f'<span style="color:#9cdcfe">端点:</span> POST {self._endpoint}')
        self._append_html('<span style="color:#9cdcfe">请求体:</span>')
        self._append_block(json.dumps(body, ensure_ascii=False, indent=2))
        self._append_html('<span style="color:#569cd6">正在发送请求...</span>')

        self._worker = AccountTestWorker(self.client, self.accounts, model_name)
        self._worker.progress_changed.connect(self._on_progress)
        self._worker.result_received.connect(self._on_result)
        self._worker.request_failed.connect(self._on_request_failed)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, index: int, total: int, account_name: str) -> None:
        """展示当前正在测试的账号和批量进度。"""
        self.progress.setValue(index - 1)
        self.progress.setFormat(f"正在测试 {index}/{total}: {account_name}")
        if len(self.accounts) > 1:
            self._append_html(
                f'<span style="color:#9cdcfe">账号 {index}/{total}:</span> {account_name}'
            )

    def _on_result(self, account_id: str, account_name: str, result: dict) -> None:
        """在主线程渲染单个账号返回结果。"""
        if len(self.accounts) > 1:
            self._append_html(f'<span style="color:#9cdcfe">账号:</span> {account_name}')
        self._render_result(result)

    def _on_request_failed(self, account_id: str, account_name: str, error: str) -> None:
        """记录单个请求异常，不中断剩余账号测试。"""
        self._append_html(
            f'<span style="color:#f48771">✗ {account_name} 请求出错:</span> {error}'
        )

    def _on_finished(self) -> None:
        """恢复弹窗操作并标记测试完成。"""
        self.progress.setValue(len(self.accounts))
        self.progress.setFormat("测试完成")
        self.test_btn.setEnabled(True)
        self.model.setEnabled(True)
        self.close_button.setEnabled(True)
        self._worker = None

    def reject(self) -> None:
        """测试进行中禁止关闭，避免后台线程回调已销毁的弹窗。"""
        if self._worker is not None and self._worker.isRunning():
            return
        super().reject()

    def _render_result(self, result: dict) -> None:
        """根据测试结果渲染响应状态、响应内容与成功/失败提示。"""
        success = result.get("success", False)
        status = result.get("status_code")
        if status is not None:
            color = "#4ec9b0" if success else "#f48771"
            self._append_html(f'<span style="color:{color}">响应状态:</span> {status}')

        body = result.get("response_body") or result.get("error_message")
        if body:
            self._append_html('<span style="color:#9cdcfe">响应内容:</span>')
            try:
                pretty = json.dumps(json.loads(body), ensure_ascii=False, indent=2)
            except (json.JSONDecodeError, TypeError):
                pretty = body
            self._append_block(pretty)

        if success:
            self._append_html('<span style="color:#4ec9b0">✓ 测试通过</span>')
        else:
            code = result.get("error_code") or ""
            self._append_html(f'<span style="color:#f48771">✗ 测试失败 ({code})</span>')
