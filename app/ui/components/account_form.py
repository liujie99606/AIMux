from __future__ import annotations

from collections import defaultdict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit, QSpinBox


class AccountForm(QDialog):
    """账号新增/编辑表单，模型选项由模型目录按协议类型过滤。"""

    def __init__(self, model_catalog: list[dict], account: dict | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("编辑账号" if account else "新增账号")
        self.setMinimumWidth(460)
        self._selected_by_type: dict[str, set[str]] = defaultdict(set)
        if account:
            self._selected_by_type[account["type"]] = set(account.get("supported_models") or [])
        self._loaded_type: str | None = None
        self._models_by_type: dict[str, list[str]] = defaultdict(list)
        for model in model_catalog:
            self._models_by_type[model["type"]].append(model["name"])

        form = QFormLayout(self)
        self.name = QLineEdit(account.get("name", "") if account else "")
        self.type = QComboBox()
        self.type.addItems(["openai", "anthropic"])
        if account:
            self.type.setCurrentText(account["type"])
        self.base_url = QLineEdit(account.get("base_url", "") if account else "")
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("新增时必填；编辑时留空保持不变")
        self.priority = QSpinBox()
        self.priority.setRange(0, 9)
        self.priority.setValue(account.get("priority", 5) if account else 5)
        self.models = QListWidget()
        self.models.setMaximumHeight(130)
        self.models.setToolTip("可多选；不选择表示该账号支持全部模型")
        self.tags = QLineEdit(", ".join(account.get("tags") or []) if account else "")
        self.notes = QPlainTextEdit((account.get("notes") or "") if account else "")
        form.addRow("名称", self.name)
        form.addRow("类型", self.type)
        form.addRow("上游地址", self.base_url)
        form.addRow("API 密钥", self.api_key)
        form.addRow("优先级", self.priority)
        form.addRow("支持模型", self.models)
        form.addRow("标签", self.tags)
        form.addRow("备注", self.notes)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        self.type.currentTextChanged.connect(self._load_models_for_type)
        self._load_models_for_type(self.type.currentText())

    def _load_models_for_type(self, account_type: str) -> None:
        """刷新当前协议的模型清单，并保留原先已选的同类型模型。"""
        if self._loaded_type is not None:
            self._selected_by_type[self._loaded_type] = set(self.selected_models())
        self.models.clear()
        names = list(self._models_by_type[account_type])
        selected = self._selected_by_type[account_type]
        # 已保存但后来从目录删除的模型仍可见，编辑时不会意外丢失配置。
        names.extend(name for name in selected if name not in names)
        for name in sorted(names):
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if name in selected else Qt.CheckState.Unchecked)
            self.models.addItem(item)
        self._loaded_type = account_type

    def selected_models(self) -> list[str]:
        """返回用户勾选的模型；空列表表示不限模型。"""
        return [self.models.item(index).text() for index in range(self.models.count()) if self.models.item(index).checkState() == Qt.CheckState.Checked]

    def payload(self, creating: bool) -> dict:
        """校验输入并构造账号管理 API 所需的 JSON。"""
        split = lambda value: [part.strip() for part in value.split(",") if part.strip()] or None
        result = {"name": self.name.text().strip(), "type": self.type.currentText(), "base_url": self.base_url.text().strip(), "priority": self.priority.value(), "supported_models": self.selected_models() or None, "tags": split(self.tags.text()), "notes": self.notes.toPlainText().strip() or None}
        if self.api_key.text():
            result["api_key"] = self.api_key.text()
        if creating and not result.get("api_key"):
            raise ValueError("请输入 API 密钥")
        if not result["name"] or not result["base_url"]:
            raise ValueError("名称和上游地址不能为空")
        return result
