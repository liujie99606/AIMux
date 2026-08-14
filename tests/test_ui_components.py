from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QDialog, QPushButton

from app.ui.components.accounts.account_form import AccountForm
from app.ui.components.accounts.account_table import AccountTable
from app.ui.components.accounts.account_test_dialog import AccountTestDialog
from app.ui.components.accounts.batch_toolbar import BatchToolbar
from app.ui.components.monitor_table import MonitorTable
from app.ui.components.monitor_status_grid import MonitorStatusGrid
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
            "multiplier": 0.08,
            "priority": 5,
            "supported_models": ["gpt-test"],
            "last_used_at": None,
        }
    ])
    assert table.rowCount() == 1
    assert table.selected_ids() == []
    assert table.horizontalHeaderItem(2).text() == "倍率"
    assert table.item(0, 2).text() == "0.08"
    assert table.item(0, 1).text() == "测试账号"
    assert "优先级快捷操作" not in [
        table.horizontalHeaderItem(index).text() for index in range(table.columnCount())
    ]
    priority_changes: list[tuple[str, int]] = []
    table.priority_changed.connect(
        lambda account_id, value: priority_changes.append((account_id, value))
    )
    priority_editor = table.cellWidget(0, 5)
    priority_editor.setValue(6)
    assert priority_changes == [("account-1", 6)]
    toggled: list[str] = []
    table.toggle_requested.connect(toggled.append)
    status = table.cellWidget(0, 4)
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
    assert form.multiplier.value() == 0.10
    assert form.test_default_model.count() == 1
    assert form.test_default_model.currentData() is None
    form.name.setText("测试")
    form.base_url.setText("https://example.com")
    form.api_key.setText("key")
    form.multiplier.setValue(0.07)
    form.models.item(0).setCheckState(Qt.CheckState.Checked)
    form.test_default_model.setCurrentIndex(1)
    assert form.payload(True)["multiplier"] == 0.07
    assert form.payload(True)["test_default_model"] == "gpt-5.5"
    form.models.item(0).setCheckState(Qt.CheckState.Unchecked)
    assert form.test_default_model.currentData() is None
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


def test_account_form_keeps_dialog_open_until_all_required_fields_are_valid():
    """保存时缺少任一必填字段应在当前表单提示，不能关闭弹窗。"""
    application = QApplication.instance() or QApplication([])
    form = AccountForm([{"name": "gpt-5.5", "type": "openai"}])

    form.accept()

    assert form.result() == QDialog.DialogCode.Rejected
    assert not form.validation_message.isHidden()
    assert "名称" in form.validation_message.text()
    assert "测试默认模型" in form.validation_message.text()

    form.name.setText("测试")
    form.base_url.setText("https://example.com")
    form.api_key.setText("key")
    form.models.item(0).setCheckState(Qt.CheckState.Checked)
    form.test_default_model.setCurrentIndex(1)
    form.accept()

    assert form.result() == QDialog.DialogCode.Accepted
    form.deleteLater(); application.processEvents()


def test_account_form_edits_and_validates_model_mappings():
    """模型映射可回显、删除，且重复客户端模型保存时不能关闭表单。"""
    application = QApplication.instance() or QApplication([])
    form = AccountForm(
        [{"name": "gpt-5.5", "type": "openai"}],
        {
            "type": "openai",
            "name": "测试",
            "base_url": "https://example.com",
            "api_key": "key",
            "supported_models": ["gpt-5.5"],
            "test_default_model": "gpt-5.5",
            "model_mappings": {"gpt-5.5": "grok4.6"},
        },
    )
    assert form.model_mappings() == {"gpt-5.5": "grok4.6"}

    form._add_mapping_row("gpt-5.5", "another-model")
    form.accept()

    assert form.result() == QDialog.DialogCode.Rejected
    assert "重复" in form.validation_message.text()
    form.deleteLater(); application.processEvents()


def test_account_form_model_mapping_uses_supported_and_catalog_dropdowns():
    """模型映射客户端端只取支持模型，上游端取当前协议模型目录。"""
    application = QApplication.instance() or QApplication([])
    form = AccountForm(
        [
            {"name": "gpt-5.5", "type": "openai"},
            {"name": "grok4.6", "type": "openai"},
            {"name": "claude-sonnet-4-8", "type": "anthropic"},
        ],
        {
            "type": "openai",
            "supported_models": ["gpt-5.5"],
            "model_mappings": {"gpt-5.5": "grok4.6"},
        },
    )
    source = form.model_mappings_table.cellWidget(0, 0)
    target = form.model_mappings_table.cellWidget(0, 1)
    assert isinstance(source, QComboBox)
    assert isinstance(target, QComboBox)
    assert [source.itemData(index) for index in range(source.count())] == [None, "gpt-5.5"]
    assert [target.itemData(index) for index in range(target.count())] == [None, "gpt-5.5", "grok4.6"]
    assert form.model_mappings_table.minimumWidth() == 700
    assert form.model_mappings_table.minimumHeight() >= 120
    assert [form.model_mappings_table.columnWidth(index) for index in range(3)] == [300, 300, 80]
    assert form.model_mappings_table.verticalHeader().defaultSectionSize() == 38
    form.deleteLater(); application.processEvents()


def test_account_form_preserves_configured_test_model_when_catalog_no_longer_has_it():
    """编辑账号时，已保存的测试默认模型不能因目录删除而被意外清空。"""
    application = QApplication.instance() or QApplication([])
    form = AccountForm(
        [{"name": "gpt-current", "type": "openai"}],
        {"type": "openai", "test_default_model": "gpt-removed", "api_key": "key", "name": "账号", "base_url": "https://example.com"},
    )
    assert form.selected_models() == ["gpt-removed"]
    assert form.test_default_model.currentData() == "gpt-removed"
    assert form.payload(True)["test_default_model"] == "gpt-removed"
    form.deleteLater(); application.processEvents()


def test_monitor_table_displays_account_multiplier():
    """监控表格应在类型后展示账号倍率。"""
    application = QApplication.instance() or QApplication([])
    table = MonitorTable()
    table.set_records([
        {
            "account_name": "账号一",
            "account_type": "openai",
            "multiplier": 0.08,
            "records": [],
        }
    ])

    assert table.horizontalHeaderItem(2).text() == "倍率"
    assert table.item(0, 2).text() == "0.08"
    table.deleteLater(); application.processEvents()


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
        {"id": "first-slow", "success": True, "duration_ms": 20_000, "first_token_ms": 10_001, "attempts": 1},
        {"id": "duration-slow", "success": True, "duration_ms": 20_001, "first_token_ms": 10_000, "attempts": 1},
    ])
    assert table.horizontalHeaderItem(3).text() == "模型"
    assert table.horizontalHeaderItem(4).text() == "推理强度"
    assert table.horizontalHeaderItem(5).text() == "接口"
    result_column = 6
    assert table.item(0, result_column).text() == "失败"
    assert table.item(0, result_column).foreground().color().name().upper() == "#D95C5C"
    assert table.item(0, 8).text() == "1.2 s"
    assert table.item(1, 7).foreground().color().name().upper() == "#E0A800"
    assert table.item(1, 8).foreground().color().name().upper() != "#E0A800"
    assert table.item(2, 7).foreground().color().name().upper() != "#E0A800"
    assert table.item(2, 8).foreground().color().name().upper() == "#E0A800"
    assert table.horizontalHeaderItem(9).text() == "重试次数"
    assert table.item(0, 9).text() == "3"
    assert "缓存Token" not in [table.horizontalHeaderItem(index).text() for index in range(table.columnCount())]

    summary = SummaryCards()
    summary.set_summary({"average_duration_ms": 1234})
    assert len(summary._cards) == 3
    assert [card.title_label.text() for card in summary._cards] == ["请求数", "成功率", "平均耗时"]
    assert summary._cards[2].value_label.text() == "1.2 s"
    table.deleteLater(); summary.deleteLater(); application.processEvents()


def test_monitor_slow_duration_uses_yellow_warning_color():
    """监控平均耗时和成功但过慢的状态格应使用黄色，失败始终红色。"""
    application = QApplication.instance() or QApplication([])
    table = MonitorTable()
    table.set_records([
        {
            "account_name": "账号一",
            "account_type": "openai",
            "records": [
                {"success": True, "duration_ms": 20_001, "checked_at": "2026-08-01T00:00:00Z"},
                {"success": False, "duration_ms": 30_000, "checked_at": "2026-08-01T00:02:00Z"},
            ],
        }
    ])

    assert table.item(0, 5).foreground().color().name().upper() == "#E0A800"
    grid = table.cellWidget(0, 7)
    assert grid is not None
    assert "#e0a800" in grid.layout().itemAt(28).widget().styleSheet()
    assert "#c43d4b" in grid.layout().itemAt(29).widget().styleSheet()
    assert "color: #1f2937" in grid.styleSheet()

    boundary_grid = MonitorStatusGrid()
    boundary_grid.set_records([{"success": True, "duration_ms": 20_000}])
    assert "#2e9f63" in boundary_grid.layout().itemAt(29).widget().styleSheet()
    table.deleteLater(); boundary_grid.deleteLater(); application.processEvents()


def test_token_statistics_cards_format_total_today_and_yesterday_values():
    """数据统计卡片应按总计、昨日、今日显示紧凑格式的 Token 数。"""
    application = QApplication.instance() or QApplication([])
    cards = TokenStatisticsCards()
    cards.set_statistics({
        "total": {"total_tokens": 3_000_000, "input_tokens": 1_500, "output_tokens": 25, "cached_tokens": 900, "cache_rate": 0.6},
        "today": {"total_tokens": 1_250, "input_tokens": 1_000_000, "output_tokens": 12, "cached_tokens": 800, "cache_rate": 0.8},
        "yesterday": {"total_tokens": 2_000_000, "input_tokens": 500, "output_tokens": 250, "cached_tokens": 0, "cache_rate": None},
    })
    assert list(cards._groups) == ["total", "yesterday", "today"]
    assert cards._groups["total"]["total_tokens"].value_label.text() == "3M"
    assert cards._groups["total"]["cache_rate"].value_label.text() == "60.0%"
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
