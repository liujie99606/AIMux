from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QMessageBox, QPushButton, QVBoxLayout, QWidget

from app.ui.client import ApiClient
from app.ui.components.data_table import Column, DataTable
from app.ui.components.model_form import ModelForm
from app.ui.formatting import format_time


class ModelTable(DataTable):
    """模型目录表格，编辑/删除通过信号交由视图处理。"""

    edit_requested = Signal(str)
    delete_requested = Signal(str)

    COLUMNS = [
        Column("名称", lambda r: r["name"]),
        Column("类型", lambda r: r["type"]),
        Column("更新时间", lambda r: format_time(r.get("updated_at"))),
        Column("操作", lambda r: r["_actions"], widget=True, stretch=True),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)

    def set_models(self, models: list[dict]) -> None:
        """渲染模型列表，操作按钮在预处理中连接信号。"""
        self._render([self._prepare(model) for model in models])

    def _prepare(self, model: dict) -> dict:
        """为单行生成操作按钮并连接编辑/删除信号。"""
        actions = QWidget()
        layout = QHBoxLayout(actions)
        layout.setContentsMargins(0, 0, 0, 0)
        edit = QPushButton("编辑")
        remove = QPushButton("删除")
        edit.clicked.connect(lambda _, model_id=model["id"]: self.edit_requested.emit(model_id))
        remove.clicked.connect(lambda _, model_id=model["id"]: self.delete_requested.emit(model_id))
        layout.addWidget(edit)
        layout.addWidget(remove)
        prepared = dict(model)
        prepared["_actions"] = actions
        return prepared


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
