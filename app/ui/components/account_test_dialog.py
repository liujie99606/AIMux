from __future__ import annotations

import json

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from app.ui.client import ApiClient


class AccountTestDialog(QDialog):
    """账号连接测试弹窗：选择模型并展示请求与响应详情。"""

    def __init__(self, client: ApiClient, account: dict, models: list[dict], parent=None) -> None:
        super().__init__(parent)
        self.client = client
        self.account = account
        self.setWindowTitle(f"测试账号 · {account.get('name', '')}")
        self.setMinimumSize(900, 700)

        layout = QVBoxLayout(self)

        selector = QHBoxLayout()
        selector.addWidget(QLabel("选择测试模型"))
        self.model = QComboBox()
        self.model.addItems([item["name"] for item in models])
        selector.addWidget(self.model)
        selector.addSpacing(16)
        selector.addWidget(QLabel("测试请求形态"))
        self.request_type = QLabel(self._detect_request_type())
        selector.addWidget(self.request_type)
        selector.addStretch()
        self.test_btn = QPushButton("开始测试")
        self.test_btn.clicked.connect(self._run_test)
        selector.addWidget(self.test_btn)
        layout.addLayout(selector)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        # 深色背景等宽字体，便于阅读请求/响应文本。
        self.log.setStyleSheet(
            "QTextEdit { background-color: #1e1e1e; color: #d4d4d4;"
            " font-family: Consolas, 'Courier New', monospace; font-size: 12px; }"
        )
        layout.addWidget(self.log)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._endpoint = "/v1/messages" if account["type"] == "anthropic" else "/v1/chat/completions"

    def _detect_request_type(self) -> str:
        """根据账号类型显示对应的请求形态名称。"""
        return "Messages" if self.account["type"] == "anthropic" else "Chat Completions"

    def _request_body(self, model: str) -> dict:
        """构造与后端 _test_one 一致的最小测试请求体。"""
        return {"model": model, "max_tokens": 1, "messages": [{"role": "user", "content": "ping"}]}

    def _append_html(self, html: str) -> None:
        """追加一行 HTML 到日志区。"""
        self.log.append(html)

    def _append_block(self, text: str) -> None:
        """追加一段普通文本，对 HTML 特殊字符转义并保留换行。"""
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        self._append_html(escaped)

    def _run_test(self) -> None:
        model_name = self.model.currentText()
        body = self._request_body(model_name)
        self.log.clear()
        self.test_btn.setEnabled(False)
        try:
            self._append_html(f'<span style="color:#9cdcfe">开始测试账号:</span> {self.account.get("name", "")}')
            self._append_html(f'<span style="color:#9cdcfe">账号类型:</span> {self.account.get("type", "")}')
            self._append_html(f'<span style="color:#9cdcfe">端点:</span> POST {self._endpoint}')
            self._append_html('<span style="color:#9cdcfe">请求体:</span>')
            self._append_block(json.dumps(body, ensure_ascii=False, indent=2))
            self._append_html('<span style="color:#569cd6">正在发送请求...</span>')
            result = self.client.post(
                f"/api/accounts/{self.account['id']}/test",
                json={"model": model_name},
            )
            self._render_result(result)
        except Exception as exc:
            self._append_html(f'<span style="color:#f48771">✗ 请求出错: {exc}</span>')
        finally:
            self.test_btn.setEnabled(True)

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