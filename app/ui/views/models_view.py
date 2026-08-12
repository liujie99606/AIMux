from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from app.ui.client import ApiClient
from app.ui.components.common.background_loader import BackgroundLoader
from app.ui.components.models.model_form import ModelForm
from app.ui.components.models.model_table import ModelTable


class ModelsView(QWidget):
    """模型目录的新增、查看、编辑和删除界面。"""

    def __init__(self, client: ApiClient, parent=None) -> None:
        super().__init__(parent)
        self.client = client
        self.models: dict[str, dict] = {}
        self.loader = BackgroundLoader(self)
        self.loader.loaded.connect(self._apply_models)
        self.loader.failed.connect(self._error)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)
        tools = QHBoxLayout()
        tools.setSpacing(8)
        self.type_filter = QComboBox()
        self.type_filter.addItems(["全部类型", "openai", "anthropic"])
        add = QPushButton("新增模型")
        refresh = QPushButton("刷新")
        tools.addWidget(QLabel("类型"))
        tools.addWidget(self.type_filter)
        tools.addStretch()
        tools.addWidget(add)
        tools.addWidget(refresh)
        root.addLayout(tools)
        self.table = ModelTable()
        root.addWidget(self.table)
        add.clicked.connect(self.add)
        refresh.clicked.connect(self.refresh)
        self.type_filter.currentIndexChanged.connect(self.refresh)
        self.table.edit_requested.connect(self.edit)
        self.table.delete_requested.connect(self.delete)
        self.table.default_requested.connect(self.make_default)
        self.refresh()

    def _error(self, exc: Exception) -> None:
        """显示模型维护操作失败原因。"""
        QMessageBox.warning(self, "操作失败", str(exc))

    def refresh(self) -> None:
        """重新读取模型目录并绘制表格。"""
        params: dict[str, str] = {}
        model_type = self.type_filter.currentText()
        if model_type != "全部类型":
            params["type"] = model_type
        self.loader.load(lambda: self.client.get("/api/models", params=params))

    def _apply_models(self, data: object) -> None:
        """在主线程渲染后台查询返回的模型目录。"""
        payload = data if isinstance(data, dict) else {}
        items = payload.get("items", [])
        self.models = {item["id"]: item for item in items}
        self.table.set_models(items)

    def add(self) -> None:
        """新增模型后立即刷新目录。"""
        form = ModelForm(parent=self)
        if form.exec():
            try:
                self.client.post("/api/models", json=form.payload())
                self.refresh()
            except Exception as exc:
                self._error(exc)

    def edit(self, model_id: str) -> None:
        """编辑已有模型的名称或类型。"""
        form = ModelForm(self.models[model_id], self)
        if form.exec():
            try:
                self.client.put(f"/api/models/{model_id}", json=form.payload())
                self.refresh()
            except Exception as exc:
                self._error(exc)

    def delete(self, model_id: str) -> None:
        """确认后从模型目录删除一项。"""
        model = self.models[model_id]
        if QMessageBox.question(self, "删除模型", f"确定删除模型 {model['name']}？") == QMessageBox.StandardButton.Yes:
            try:
                self.client.delete(f"/api/models/{model_id}")
                self.refresh()
            except Exception as exc:
                self._error(exc)

    def make_default(self, model_id: str) -> None:
        """将指定模型设为其协议类型的测试默认。"""
        try:
            self.client.post(f"/api/models/{model_id}/set-default")
            self.refresh()
        except Exception as exc:
            self._error(exc)
