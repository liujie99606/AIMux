from __future__ import annotations

from collections import defaultdict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QLabel,
    QTableWidget,
    QVBoxLayout,
    QWidget,
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
        self.setMinimumSize(920, 720)
        self.resize(960, 760)
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
        form.setContentsMargins(24, 20, 24, 20)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(6)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
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
        self.models.setMinimumHeight(78)
        self.models.setMaximumHeight(104)
        self.models.setToolTip("可多选；不选择表示该账号支持全部模型")
        self.test_default_model = QComboBox()
        self.test_default_model.setToolTip("仅可从已勾选的支持模型中选择")
        self.model_mappings_table = QTableWidget(0, 3)
        self.model_mappings_table.setHorizontalHeaderLabels(["客户端模型", "上游模型", "操作"])
        self.model_mappings_table.setMinimumWidth(700)
        self.model_mappings_table.setMinimumHeight(124)
        self.model_mappings_table.setMaximumHeight(180)
        header = self.model_mappings_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.model_mappings_table.setColumnWidth(2, 80)
        self.model_mappings_table.verticalHeader().setVisible(False)
        self.model_mappings_table.verticalHeader().setDefaultSectionSize(38)
        self.model_mappings_table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        mapping_tools = QWidget()
        mapping_tools_layout = QHBoxLayout(mapping_tools)
        mapping_tools_layout.setContentsMargins(0, 0, 0, 0)
        add_mapping = QPushButton("新增映射")
        add_mapping.clicked.connect(lambda: self._add_mapping_row())
        mapping_tools_layout.addWidget(add_mapping)
        mapping_tools_layout.addStretch()
        self.tags = QLineEdit(", ".join(account.get("tags") or []) if account else "")
        self.notes = QPlainTextEdit((account.get("notes") or "") if account else "")
        for field in (
            self.name,
            self.type,
            self.base_url,
            self.api_key,
            self.test_default_model,
            self.tags,
        ):
            self._configure_field(field, width=560)
        for field in (self.priority, self.multiplier):
            self._configure_field(field, width=150, expand=False)
        self.models.setMinimumWidth(560)
        self.models.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.notes.setMinimumSize(560, 90)
        self.notes.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        form.addRow(self._required_label("名称"), self.name)
        form.addRow(self._required_label("类型"), self.type)
        form.addRow(self._required_label("上游地址"), self.base_url)
        form.addRow(self._required_label("API密钥"), self.api_key)
        form.addRow(self._required_label("优先级"), self.priority)
        form.addRow(self._required_label("倍率"), self.multiplier)
        form.addRow(self._required_label("支持模型"), self.models)
        form.addRow(self._required_label("测试默认模型"), self.test_default_model)
        mapping_section = QWidget()
        mapping_layout = QVBoxLayout(mapping_section)
        mapping_layout.setContentsMargins(0, 0, 0, 0)
        mapping_layout.setSpacing(6)
        mapping_layout.addWidget(self.model_mappings_table)
        mapping_layout.addWidget(mapping_tools)
        form.addRow("模型映射", mapping_section)
        form.addRow("标签", self.tags)
        form.addRow("备注", self.notes)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        self.validation_message = QLabel()
        self.validation_message.setStyleSheet("color: #f48771;")
        self.validation_message.setWordWrap(True)
        self.validation_message.hide()
        form.addRow(self.validation_message)
        self.type.currentTextChanged.connect(self._load_models_for_type)
        self.models.itemChanged.connect(self._refresh_test_default_models)
        self._load_models_for_type(self.type.currentText())
        for source, target in (account.get("model_mappings") or {}).items() if account else []:
            self._add_mapping_row(source, target)

    @staticmethod
    def _required_label(text: str) -> QLabel:
        """创建仅将必填星号标为红色的字段标签。"""
        label = QLabel(f'{text}<span style="color: red">*</span>')
        label.setTextFormat(Qt.TextFormat.RichText)
        return label

    @staticmethod
    def _configure_field(field: QWidget, *, width: int, expand: bool = True) -> None:
        """统一表单字段的最小尺寸和横向扩展策略。"""
        field.setMinimumWidth(width)
        field.setMinimumHeight(28)
        horizontal_policy = (
            QSizePolicy.Policy.Expanding if expand else QSizePolicy.Policy.Fixed
        )
        field.setSizePolicy(horizontal_policy, QSizePolicy.Policy.Fixed)

    def accept(self) -> None:
        """校验必填项，未通过时保留表单并显示当前缺失字段。"""
        missing, first_field = self._missing_required_fields()
        if missing:
            self.validation_message.setText(f"请填写或选择：{'、'.join(missing)}")
            self.validation_message.show()
            first_field.setFocus()
            return
        try:
            self.model_mappings()
        except ValueError as exc:
            self.validation_message.setText(str(exc))
            self.validation_message.show()
            return
        self.validation_message.hide()
        super().accept()

    def _missing_required_fields(self) -> tuple[list[str], QWidget]:
        """返回缺失必填字段及首个应获取焦点的输入控件。"""
        checks: list[tuple[str, bool, QWidget]] = [
            ("名称", bool(self.name.text().strip()), self.name),
            ("类型", bool(self.type.currentText()), self.type),
            ("上游地址", bool(self.base_url.text().strip()), self.base_url),
            ("API密钥", bool(self.api_key.text().strip()), self.api_key),
            ("优先级", self.priority.minimum() <= self.priority.value() <= self.priority.maximum(), self.priority),
            ("倍率", self.multiplier.minimum() <= self.multiplier.value() <= self.multiplier.maximum(), self.multiplier),
            ("支持模型", bool(self.selected_models()), self.models),
            ("测试默认模型", self.test_default_model.currentData() is not None, self.test_default_model),
        ]
        missing = [(name, field) for name, valid, field in checks if not valid]
        return [name for name, _ in missing], missing[0][1] if missing else self.name

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
        self._refresh_mapping_combos()
        if self._loaded_type is not None:
            self._test_default_by_type[self._loaded_type] = self.test_default_model.currentData() or ""

    def selected_models(self) -> list[str]:
        """返回用户勾选的模型；空列表表示不限模型。"""
        return [
            self.models.item(index).text()
            for index in range(self.models.count())
            if self.models.item(index).checkState() == Qt.CheckState.Checked
        ]

    def _add_mapping_row(self, source: str = "", target: str = "") -> None:
        """新增一行客户端模型到上游模型的映射。"""
        row = self.model_mappings_table.rowCount()
        self.model_mappings_table.insertRow(row)
        source_editor = self._mapping_combo(
            self._selected_models_for_mapping(), source, "选择客户端模型"
        )
        target_editor = self._mapping_combo(
            self._models_by_type[self.type.currentText()], target, "选择上游模型"
        )
        remove = QPushButton("删除")
        remove.clicked.connect(self._remove_mapping_row)
        self.model_mappings_table.setCellWidget(row, 0, source_editor)
        self.model_mappings_table.setCellWidget(row, 1, target_editor)
        self.model_mappings_table.setCellWidget(row, 2, remove)

    @staticmethod
    def _mapping_combo(options: list[str], current: str, placeholder: str) -> QComboBox:
        """创建模型映射下拉框，并保留不在目录中的历史值。"""
        combo = QComboBox()
        combo.addItem(placeholder, None)
        values = list(dict.fromkeys(options))
        preserve_unlisted = bool(current and current not in values)
        if current and current not in values:
            values.append(current)
        for value in sorted(values):
            combo.addItem(value, value)
        combo.setProperty("preserve_unlisted", preserve_unlisted)
        if current:
            index = combo.findData(current)
            combo.setCurrentIndex(index if index >= 0 else 0)
        return combo

    def _selected_models_for_mapping(self) -> list[str]:
        """返回当前已勾选的客户端模型候选。"""
        return sorted(self.selected_models())

    def _refresh_mapping_combos(self) -> None:
        """按当前支持模型和协议类型刷新所有映射下拉候选。"""
        if not hasattr(self, "model_mappings_table"):
            return
        source_options = self._selected_models_for_mapping()
        target_options = sorted(self._models_by_type[self.type.currentText()])
        for row in range(self.model_mappings_table.rowCount()):
            source_combo = self.model_mappings_table.cellWidget(row, 0)
            target_combo = self.model_mappings_table.cellWidget(row, 1)
            if isinstance(source_combo, QComboBox):
                current = source_combo.currentData() or source_combo.currentText()
                self._replace_mapping_combo_options(
                    source_combo, source_options, current, "选择客户端模型", preserve_unlisted=False
                )
            if isinstance(target_combo, QComboBox):
                current = target_combo.currentData() or target_combo.currentText()
                self._replace_mapping_combo_options(
                    target_combo, target_options, current, "选择上游模型", preserve_unlisted=True
                )

    @staticmethod
    def _replace_mapping_combo_options(
        combo: QComboBox,
        options: list[str],
        current: str,
        placeholder: str,
        *,
        preserve_unlisted: bool,
    ) -> None:
        """替换映射候选并尽量恢复当前值。"""
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(placeholder, None)
        values = list(dict.fromkeys(options))
        keep_unlisted = preserve_unlisted and bool(combo.property("preserve_unlisted"))
        if current and current not in values and keep_unlisted:
            values.append(current)
        for value in sorted(values):
            combo.addItem(value, value)
        index = combo.findData(current) if current else -1
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.setProperty("preserve_unlisted", keep_unlisted and current not in options)
        combo.blockSignals(False)

    def _remove_mapping_row(self) -> None:
        """删除点击按钮所在的模型映射行。"""
        button = self.sender()
        for row in range(self.model_mappings_table.rowCount()):
            if self.model_mappings_table.cellWidget(row, 2) is button:
                self.model_mappings_table.removeRow(row)
                return

    def model_mappings(self) -> dict[str, str] | None:
        """读取并校验表单中的模型映射行。"""
        mappings: dict[str, str] = {}
        for row in range(self.model_mappings_table.rowCount()):
            source_editor = self.model_mappings_table.cellWidget(row, 0)
            target_editor = self.model_mappings_table.cellWidget(row, 1)
            source = source_editor.currentData() if isinstance(source_editor, QComboBox) else ""
            target = target_editor.currentData() if isinstance(target_editor, QComboBox) else ""
            source = source.strip() if isinstance(source, str) else ""
            target = target.strip() if isinstance(target, str) else ""
            if not source or not target:
                raise ValueError(f"模型映射第 {row + 1} 行的客户端模型和上游模型不能为空")
            if source in mappings:
                raise ValueError(f"模型映射中客户端模型重复：{source}")
            if source == target:
                raise ValueError(f"模型映射第 {row + 1} 行的两个模型不能相同")
            mappings[source] = target
        return mappings or None

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
            "model_mappings": self.model_mappings(),
            "supported_models": self.selected_models() or None,
            "tags": split(self.tags.text()),
            "notes": self.notes.toPlainText().strip() or None,
        }
        if not result["api_key"]:
            raise ValueError("请输入 API 密钥")
        if not result["name"] or not result["base_url"]:
            raise ValueError("名称和上游地址不能为空")
        return result
