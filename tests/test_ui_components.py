from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.ui.components.accounts.account_form import AccountForm
from app.ui.components.accounts.account_table import AccountTable
from app.ui.components.accounts.account_test_dialog import AccountTestDialog
from app.ui.components.accounts.batch_toolbar import BatchToolbar
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
    assert table.horizontalHeaderItem(5).text() == "优先级快捷操作"
    table.set_all_selected(True)
    assert table.selected_ids() == ["account-1"]
    table.set_all_selected(False)
    assert table.selected_ids() == []
    application.processEvents()


def test_batch_toolbar_select_all_toggles_account_table():
    """批量工具栏的全选复选框应支持全选和取消全选。"""
    application = QApplication.instance() or QApplication([])
    table = AccountTable()
    toolbar = BatchToolbar()
    toolbar.select_all_changed.connect(table.set_all_selected)
    table.set_accounts([
        {"id": "account-1", "name": "账号一", "type": "openai", "status": "active", "priority": 5},
        {"id": "account-2", "name": "账号二", "type": "openai", "status": "active", "priority": 4},
    ])
    toolbar.select_all_checkbox.setChecked(True)
    assert table.selected_ids() == ["account-1", "account-2"]
    toolbar.select_all_checkbox.setChecked(False)
    assert table.selected_ids() == []
    table.deleteLater(); toolbar.deleteLater(); application.processEvents()


def test_account_test_dialog_supports_batch_accounts():
    """批量测试应逐个调用账号接口，并在首个失败后继续测试。"""
    application = QApplication.instance() or QApplication([])

    class FakeClient:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict]] = []

        def post(self, path: str, **kwargs: dict) -> dict:
            self.calls.append((path, kwargs))
            if path.endswith("account-1/test"):
                return {
                    "account_id": "account-1",
                    "success": False,
                    "status_code": 401,
                    "error_code": "test_failed",
                }
            return {"account_id": "account-2", "success": True, "status_code": 200}

    client = FakeClient()
    dialog = AccountTestDialog(
        client,
        [
            {"id": "account-1", "name": "账号一", "type": "openai"},
            {"id": "account-2", "name": "账号二", "type": "openai"},
        ],
        [{"name": "gpt-test", "type": "openai"}],
    )
    dialog._run_test()
    worker = dialog._worker
    assert worker is not None
    for _ in range(20):
        application.processEvents()
        if worker.isRunning():
            QTest.qWait(10)
    worker.wait()
    application.processEvents()
    assert client.calls == [
        ("/api/accounts/account-1/test", {"json": {"model": "gpt-test"}}),
        ("/api/accounts/account-2/test", {"json": {"model": "gpt-test"}}),
    ]
    assert "账号一" in dialog.log.toPlainText() and "账号二" in dialog.log.toPlainText()
    dialog.deleteLater(); application.processEvents()


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
    assert len(summary._cards) == 3
    assert [card.title_label.text() for card in summary._cards] == ["请求数", "成功率", "平均耗时"]
    assert summary._cards[2].value_label.text() == "1.2 s"
    table.deleteLater(); summary.deleteLater(); application.processEvents()
