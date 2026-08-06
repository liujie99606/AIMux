from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QMessageBox, QPushButton, QVBoxLayout, QWidget

from app.ui.client import ApiClient
from app.ui.components.models.model_form import ModelForm
from app.ui.components.models.model_table import ModelTable


class ModelsView(QWidget):
    """模型目录的新增、查看、编辑和删除界面。"""

    def __init__(self, client: ApiClient, parent=None) -> None:
        super().__init__(parent)
        self.client = client
        self.models: dict[str, dict] = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)
        tools = QHBoxLayout()
        tools.setSpacing(8)
        add = QPushButton("新增模型")
        refresh = QPushButton("刷新")
        tools.addStretch()
        tools.addWidget(add)
        tools.addWidget(refresh)
        root.addLayout(tools)
        self.table = ModelTable()
        root.addWidget(self.table)
        add.clicked.connect(self.add)
        refresh.clicked.connect(self.refresh)
        self.table.edit_requested.connect(self.edit)
        self.table.delete_requested.connect(self.delete)
        self.table.default_requested.connect(self.make_default)
        self.refresh()

    def _error(self, exc: Exception) -> None:
        """显示模型维护操作失败原因。"""
        QMessageBox.warning(self, "操作失败", str(exc))

    def refresh(self) -> None:
        """重新读取模型目录并绘制表格。"""
        try:
            items = self.client.get("/api/models")["items"]
            self.models = {item["id"]: item for item in items}
            self.table.set_models(items)
        except Exception as exc:
            self._error(exc)

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
