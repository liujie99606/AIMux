from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.ui.formatting import format_time


def _text(value) -> str:
    """把任意字段值规整为展示文本，空值统一显示为“-”。"""
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "是" if value else "否"
    return str(value)


class UsageDetailDialog(QDialog):
    """使用记录详情弹窗，尽可能展示数据库中的全部字段。"""

    def __init__(self, record: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("使用记录详情")
        self.setMinimumSize(920, 560)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setLabelAlignment(self._label_alignment())
        get = record.get

        # 基本信息与时间
        form.addRow("记录 ID", QLabel(_text(get("id"))))
        form.addRow("Trace ID", QLabel(_text(get("trace_id"))))
        form.addRow("开始时间", QLabel(format_time(get("started_at"))))
        form.addRow("结束时间", QLabel(format_time(get("ended_at"))))
        form.addRow("总耗时", QLabel(self._ms(get("duration_ms"))))
        form.addRow("首 Token 用时", QLabel(self._ms(get("first_token_ms"))))
        form.addRow("尝试次数", QLabel(_text(get("attempts"))))

        # 账号、模型与请求参数
        form.addRow("账号名称", QLabel(_text(get("account_name"))))
        form.addRow("账号 ID", QLabel(_text(get("account_id"))))
        form.addRow("账号类型", QLabel(_text(get("account_type"))))
        form.addRow("模型", QLabel(_text(get("model"))))
        form.addRow("推理强度", QLabel(_text(get("reasoning_effort"))))
        form.addRow("接口", QLabel(_text(get("endpoint"))))
        form.addRow("流式", QLabel(_text(get("stream"))))
        form.addRow("客户端 IP", QLabel(_text(get("client_ip"))))

        # 结果与状态
        form.addRow("结果", QLabel(_text(get("success"))))
        form.addRow("状态码", QLabel(_text(get("status_code"))))
        form.addRow("错误码", QLabel(_text(get("error_code"))))

        layout.addLayout(form)

        # Token 用量
        token_line = (
            f"输入 {_text(get('input_tokens'))} / 输出 {_text(get('output_tokens'))} / 合计 {_text(get('total_tokens'))}"
        )
        layout.addWidget(QLabel(f"Token 用量：{token_line}"))

        # 错误信息单独用只读等宽区域，便于查看较长内容
        error_message = get("error_message")
        layout.addWidget(QLabel("错误信息："))
        error_view = QTextEdit()
        error_view.setReadOnly(True)
        error_view.setPlainText(_text(error_message))
        error_view.setStyleSheet("QTextEdit { background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas, monospace; }")
        error_view.setFixedHeight(140)
        layout.addWidget(error_view)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _ms(value) -> str:
        """毫秒数值统一带单位展示，空值显示“-”。"""
        if value is None:
            return "-"
        return f"{value} ms"

    @staticmethod
    def _label_alignment():
        from PySide6.QtCore import Qt

        return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
