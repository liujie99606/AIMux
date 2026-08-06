from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout


class ModelTestDialog(QDialog):
    """在执行连接测试前要求从当前协议模型目录选择一个模型。"""

    def __init__(self, models: list[dict], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("选择测试模型")
        form = QFormLayout(self)
        self.model = QComboBox()
        self.model.addItems([item["name"] for item in models])
        form.addRow("测试模型", self.model)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def selected_model(self) -> str:
        """返回用户明确选择的模型名称。"""
        return self.model.currentText()
