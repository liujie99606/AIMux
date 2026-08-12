from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from app.ui.components.accounts.account_form import AccountForm
from app.ui.components.accounts.account_table import AccountTable
from app.ui.components.accounts.account_test_dialog import AccountTestDialog
from app.ui.components.accounts.batch_toolbar import BatchToolbar
from app.ui.components.statistics_cards import TokenStatisticsCards
from app.ui.components.account_token_statistics_table import AccountTokenStatisticsTable
from app.ui.components.usage.summary_card import SummaryCards
from app.ui.components.usage.usage_table import UsageTable
from app.ui.formatting import format_duration_ms, format_percentage, format_token_count


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
    priority_actions = table.cellWidget(0, 5)
    priority_buttons = priority_actions.findChildren(QPushButton)
    assert [button.text() for button in priority_buttons] == ["0", "3", "6", "9"]
    assert all(button.width() == button.height() == 26 for button in priority_buttons)
    priority_changes: list[tuple[str, int]] = []
    table.priority_changed.connect(
        lambda account_id, value: priority_changes.append((account_id, value))
    )
    priority_buttons[2].click()
    assert priority_changes == [("account-1", 6)]
    assert [button.isChecked() for button in priority_buttons] == [False, False, True, False]
    toggled: list[str] = []
    table.toggle_requested.connect(toggled.append)
    status = table.cellWidget(0, 3)
    assert status.text() == "启用"
    status.click()
    assert toggled == ["account-1"]
    actions = table.cellWidget(0, 7)
    assert [button.text() for button in actions.findChildren(QPushButton)] == ["测试", "编辑", "复制", "删除"]
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
    assert format_token_count(999) == "999"
    assert format_token_count(1_250) == "1.2K"
    assert format_token_count(2_000_000) == "2M"
    assert format_percentage(0.8) == "80.0%"
    assert format_percentage(None) == "-"

    application = QApplication.instance() or QApplication([])
    table = UsageTable()
    table.set_records([
        {"id": "failed", "success": False, "duration_ms": 1234, "first_token_ms": None, "attempts": 3},
        {"id": "success", "success": True, "duration_ms": 1234, "first_token_ms": None, "attempts": 1},
    ])
    assert table.horizontalHeaderItem(3).text() == "模型"
    assert table.horizontalHeaderItem(4).text() == "推理强度"
    assert table.horizontalHeaderItem(5).text() == "接口"
    result_column = 6
    assert table.item(0, result_column).text() == "失败"
    assert table.item(0, result_column).foreground().color().name().upper() == "#D95C5C"
    assert table.item(0, 8).text() == "1.2 s"
    assert table.horizontalHeaderItem(9).text() == "重试次数"
    assert table.item(0, 9).text() == "3"
    assert "缓存Token" not in [table.horizontalHeaderItem(index).text() for index in range(table.columnCount())]

    summary = SummaryCards()
    summary.set_summary({"average_duration_ms": 1234})
    assert len(summary._cards) == 3
    assert [card.title_label.text() for card in summary._cards] == ["请求数", "成功率", "平均耗时"]
    assert summary._cards[2].value_label.text() == "1.2 s"
    table.deleteLater(); summary.deleteLater(); application.processEvents()


def test_token_statistics_cards_format_today_and_yesterday_values():
    """数据统计卡片应显示两组紧凑格式的 Token 数。"""
    application = QApplication.instance() or QApplication([])
    cards = TokenStatisticsCards()
    cards.set_statistics({
        "today": {"total_tokens": 1_250, "input_tokens": 1_000_000, "output_tokens": 12, "cached_tokens": 800, "cache_rate": 0.8},
        "yesterday": {"total_tokens": 2_000_000, "input_tokens": 500, "output_tokens": 250, "cached_tokens": 0, "cache_rate": None},
    })
    assert cards._groups["today"]["total_tokens"].value_label.text() == "1.2K"
    assert cards._groups["today"]["input_tokens"].value_label.text() == "1M"
    assert cards._groups["today"]["cache_rate"].value_label.text() == "80.0%"
    assert cards._groups["yesterday"]["total_tokens"].value_label.text() == "2M"
    assert cards._groups["yesterday"]["cache_rate"].value_label.text() == "-"
    cards.deleteLater(); application.processEvents()


def test_account_token_statistics_table_formats_today_values():
    """启用账号今日统计表应复用 Token 和缓存率格式化规则。"""
    application = QApplication.instance() or QApplication([])
    table = AccountTokenStatisticsTable()
    table.set_statistics(
        [
            {
                "account_name": "账号一",
                "account_type": "openai",
                "priority": 9,
                "total_tokens": 1_250,
                "input_tokens": 1_000_000,
                "output_tokens": 12,
                "cached_tokens": 800,
                "cache_rate": 0.8,
            }
        ]
    )

    assert table.rowCount() == 1
    assert table.item(0, 0).text() == "账号一"
    assert table.item(0, 2).text() == "9"
    assert table.item(0, 3).text() == "1.2K"
    assert table.item(0, 4).text() == "1M"
    assert table.item(0, 7).text() == "80.0%"
    table.deleteLater(); application.processEvents()
