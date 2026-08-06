from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.components.account_form import AccountForm
from app.ui.components.account_table import AccountTable


def test_account_table_builds_checkbox_cell_without_alignment_type_error():
    """账号表格应能在当前 PySide6 版本中创建并居中选择框。"""
    application = QApplication.instance() or QApplication([])
    table = AccountTable()
    table.set_accounts([
        {
            "id": "account-1",
            "name": "测试账号",
            "type": "openai",
            "status": "active",
            "priority": 5,
            "supported_models": ["gpt-test"],
            "last_used_at": None,
        }
    ])
    assert table.rowCount() == 1
    assert table.selected_ids() == []
    application.processEvents()


def test_account_form_filters_checkable_models_when_type_changes():
    """账号表单应只展示当前 OpenAI 或 Anthropic 类型的模型列表。"""
    application = QApplication.instance() or QApplication([])
    form = AccountForm([
        {"name": "gpt-5.5", "type": "openai"},
        {"name": "claude-sonnet-4-8", "type": "anthropic"},
    ])
    assert [form.models.item(index).text() for index in range(form.models.count())] == ["gpt-5.5"]
    form.type.setCurrentText("anthropic")
    assert [form.models.item(index).text() for index in range(form.models.count())] == ["claude-sonnet-4-8"]
    application.processEvents()


def test_account_form_does_not_carry_selected_models_to_another_type():
    """切换协议类型时不能把旧类型的模型提交给新类型账号。"""
    application = QApplication.instance() or QApplication([])
    form = AccountForm(
        [
            {"name": "gpt-5.5", "type": "openai"},
            {"name": "claude-sonnet-4-8", "type": "anthropic"},
        ],
        {"type": "openai", "supported_models": ["gpt-5.5"]},
    )
    form.type.setCurrentText("anthropic")
    assert form.selected_models() == []
    assert [form.models.item(index).text() for index in range(form.models.count())] == ["claude-sonnet-4-8"]
    application.processEvents()
