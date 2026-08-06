from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from app.ui.components.common.data_table import Column, DataTable
from app.ui.formatting import format_time


class ModelTable(DataTable):
    """模型目录表格，编辑/删除/设为默认通过信号交由视图处理。"""

    edit_requested = Signal(str)
    delete_requested = Signal(str)
    default_requested = Signal(str)

    COLUMNS = [
        Column("名称", lambda r: r["name"], width=150),
        Column("类型", lambda r: r["type"]),
        Column("测试默认", lambda r: "是" if r.get("is_default") else ""),
        Column("更新时间", lambda r: format_time(r.get("updated_at")), width=150),
        Column("操作", lambda r: r["_actions"], widget=True, stretch=True),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)

    def set_models(self, models: list[dict]) -> None:
        """渲染模型列表，操作按钮在预处理中连接信号。"""
        self._render([self._prepare(model) for model in models])

    def _prepare(self, model: dict) -> dict:
        """为单行生成操作按钮并连接编辑/删除/设为默认信号。"""
        actions = QWidget()
        layout = QHBoxLayout(actions)
        layout.setContentsMargins(0, 0, 0, 0)
        edit = QPushButton("编辑")
        remove = QPushButton("删除")
        set_default = QPushButton("设为默认")
        # 当前已是默认时禁用按钮，避免重复操作。
        set_default.setEnabled(not model.get("is_default"))
        edit.clicked.connect(lambda _, model_id=model["id"]: self.edit_requested.emit(model_id))
        remove.clicked.connect(lambda _, model_id=model["id"]: self.delete_requested.emit(model_id))
        set_default.clicked.connect(lambda _, model_id=model["id"]: self.default_requested.emit(model_id))
        layout.addWidget(edit)
        layout.addWidget(remove)
        layout.addWidget(set_default)
        prepared = dict(model)
        prepared["_actions"] = actions
        return prepared
