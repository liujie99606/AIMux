from __future__ import annotations

from collections import defaultdict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QSpinBox,
    QLabel,
)


class AccountForm(QDialog):
    """账号新增/编辑表单，模型选项由模型目录按协议类型过滤。"""

    def __init__(
        self,
        model_catalog: list[dict],
        account: dict | None = None,
        parent=None,
        copy: bool = False,
    ) -> None:
        super().__init__(parent)
        # copy=True 时以现有账号数据预填表单，但作为新增账号处理（标题与提交均按新增）。
        self.setWindowTitle("编辑账号" if account and not copy else "新增账号")
        self.setMinimumWidth(920)
        self._selected_by_type: dict[str, set[str]] = defaultdict(set)
        self._test_default_by_type: dict[str, str] = {}
        if account:
            self._selected_by_type[account["type"]] = set(account.get("supported_models") or [])
            if account.get("test_default_model"):
                self._test_default_by_type[account["type"]] = account["test_default_model"]
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
        self.api_key = QLineEdit(account.get("api_key", "") if account else "")
        self.api_key.setPlaceholderText("必填")
        self.priority = QSpinBox()
        self.priority.setRange(0, 9)
        self.priority.setValue(account.get("priority", 5) if account else 5)
        self.multiplier = QDoubleSpinBox()
        self.multiplier.setRange(0.01, 0.30)
        self.multiplier.setDecimals(2)
        self.multiplier.setSingleStep(0.01)
        self.multiplier.setValue(
            float(account.get("multiplier", 0.10)) if account else 0.10
        )
        self.models = QListWidget()
        self.models.setMaximumHeight(130)
        self.models.setToolTip("可多选；不选择表示该账号支持全部模型")
        self.test_default_model = QComboBox()
        self.test_default_model.setToolTip("仅可从已勾选的支持模型中选择")
        self.tags = QLineEdit(", ".join(account.get("tags") or []) if account else "")
        self.notes = QPlainTextEdit((account.get("notes") or "") if account else "")
        form.addRow(self._required_label("名称"), self.name)
        form.addRow("类型", self.type)
        form.addRow(self._required_label("上游地址"), self.base_url)
        form.addRow(self._required_label("API 密钥"), self.api_key)
        form.addRow("优先级", self.priority)
        form.addRow("倍率", self.multiplier)
        form.addRow("支持模型", self.models)
        form.addRow("测试默认模型", self.test_default_model)
        form.addRow("标签", self.tags)
        form.addRow("备注", self.notes)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        self.type.currentTextChanged.connect(self._load_models_for_type)
        self.models.itemChanged.connect(self._refresh_test_default_models)
        self._load_models_for_type(self.type.currentText())

    @staticmethod
    def _required_label(text: str) -> QLabel:
        """创建仅将必填星号标为红色的字段标签。"""
        label = QLabel(f'{text}<span style="color: red">*</span>')
        label.setTextFormat(Qt.TextFormat.RichText)
        return label

    def _load_models_for_type(self, account_type: str) -> None:
        """刷新当前协议的模型清单，并保留原先已选的同类型模型。"""
        if self._loaded_type is not None:
            self._selected_by_type[self._loaded_type] = set(self.selected_models())
            self._test_default_by_type[self._loaded_type] = self.test_default_model.currentData() or ""
        self.models.clear()
        names = list(self._models_by_type[account_type])
        selected = self._selected_by_type[account_type]
        test_default = self._test_default_by_type.get(account_type, "")
        if test_default:
            selected.add(test_default)
        # 已保存但后来从目录删除的模型仍可见，编辑时不会意外丢失配置。
        names.extend(name for name in (*selected, test_default) if name and name not in names)
        for name in sorted(names):
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if name in selected else Qt.CheckState.Unchecked)
            self.models.addItem(item)
        self._refresh_test_default_models(test_default)
        self._loaded_type = account_type

    def _refresh_test_default_models(self, preferred: str | None = None) -> None:
        """让测试默认模型仅保留当前已勾选的支持模型。"""
        current = preferred if isinstance(preferred, str) else self.test_default_model.currentData()
        selected = sorted(self.selected_models())
        self.test_default_model.blockSignals(True)
        self.test_default_model.clear()
        self.test_default_model.addItem("使用模型维护默认值", None)
        for name in selected:
            self.test_default_model.addItem(name, name)
        index = self.test_default_model.findData(current)
        self.test_default_model.setCurrentIndex(index if index >= 0 else 0)
        self.test_default_model.blockSignals(False)
        if self._loaded_type is not None:
            self._test_default_by_type[self._loaded_type] = self.test_default_model.currentData() or ""

    def selected_models(self) -> list[str]:
        """返回用户勾选的模型；空列表表示不限模型。"""
        return [
            self.models.item(index).text()
            for index in range(self.models.count())
            if self.models.item(index).checkState() == Qt.CheckState.Checked
        ]

    def payload(self, creating: bool) -> dict:
        """校验输入并构造账号管理 API 所需的 JSON。"""
        split = lambda value: [part.strip() for part in value.split(",") if part.strip()] or None
        result = {
            "name": self.name.text().strip(),
            "type": self.type.currentText(),
            "base_url": self.base_url.text().strip(),
            "api_key": self.api_key.text().strip(),
            "priority": self.priority.value(),
            "multiplier": self.multiplier.value(),
            "test_default_model": self.test_default_model.currentData(),
            "supported_models": self.selected_models() or None,
            "tags": split(self.tags.text()),
            "notes": self.notes.toPlainText().strip() or None,
        }
        if not result["api_key"]:
            raise ValueError("请输入 API 密钥")
        if not result["name"] or not result["base_url"]:
            raise ValueError("名称和上游地址不能为空")
        return result
