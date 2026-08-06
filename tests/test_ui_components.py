from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.components.accounts.account_form import AccountForm
from app.ui.components.accounts.account_table import AccountTable
from app.ui.components.usage.summary_card import SummaryCards
from app.ui.components.usage.usage_table import UsageTable
from app.ui.formatting import format_duration_ms


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


def test_usage_formatting_and_failed_result_color():
    """使用记录时长统一显示秒数，失败结果使用深色红字。"""
    assert format_duration_ms(1234) == "1.2 s"
    assert format_duration_ms(None) == "-"

    application = QApplication.instance() or QApplication([])
    table = UsageTable()
    table.set_records([
        {"id": "failed", "success": False, "duration_ms": 1234, "first_token_ms": None, "attempts": 3},
        {"id": "success", "success": True, "duration_ms": 1234, "first_token_ms": None, "attempts": 1},
    ])
    result_column = 5
    assert table.item(0, result_column).text() == "失败"
    assert table.item(0, result_column).foreground().color().name().upper() == "#D95C5C"
    assert table.item(0, 7).text() == "1.2 s"
    assert table.horizontalHeaderItem(9).text() == "重试次数"
    assert table.item(0, 9).text() == "3"

    summary = SummaryCards()
    summary.set_summary({"average_duration_ms": 1234})
    assert summary._cards[2].value_label.text() == "1.2 s"
    table.deleteLater(); summary.deleteLater(); application.processEvents()
