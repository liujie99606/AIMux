from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit


class ModelForm(QDialog):
    """创建或编辑模型目录记录的简洁表单。"""

    def __init__(self, model: dict | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("编辑模型" if model else "新增模型")
        self.setMinimumSize(520, 240)
        form = QFormLayout(self)
        form.setContentsMargins(24, 20, 24, 20)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        form.setLabelAlignment(self._label_alignment())
        self.name = QLineEdit(model.get("name", "") if model else "")
        self.name.setMinimumWidth(320)
        self.type = QComboBox()
        self.type.setMinimumWidth(320)
        self.type.addItems(["openai", "anthropic"])
        if model:
            self.type.setCurrentText(model["type"])
        form.addRow("模型名称", self.name)
        form.addRow("类型", self.type)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    @staticmethod
    def _label_alignment() -> Qt.AlignmentFlag:
        return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

    def payload(self) -> dict:
        """返回经过基本校验的模型维护请求。"""
        name = self.name.text().strip()
        if not name:
            raise ValueError("请输入模型名称")
        return {"name": name, "type": self.type.currentText()}
