from __future__ import annotations

import json
import re
import time
from pathlib import Path

from app.config import load_settings
from app.ui.client import local_api_base_url


def _wait_until(predicate, timeout_ms: int = 1000) -> None:
    """处理 Qt 事件直到异步断言条件成立或超时。"""
    from PySide6.QtTest import QTest

    deadline = time.monotonic() + timeout_ms / 1000
    while not predicate() and time.monotonic() < deadline:
        QTest.qWait(10)
    assert predicate()


def test_environment_overrides_config_and_uses_dynamic_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AIMUX_DATA_DIR", str(tmp_path / "user-data"))
    monkeypatch.setenv("AIMUX_PORT", "8899")
    monkeypatch.setenv("AIMUX_LAUNCH_AT_LOGIN", "true")
    monkeypatch.setenv("AIMUX_UPSTREAM_PROXY_ENABLED", "true")
    monkeypatch.setenv("AIMUX_UPSTREAM_PROXY_URL", "http://127.0.0.1:7891")
    settings = load_settings()
    assert settings.port == 8899
    assert settings.launch_at_login is True
    assert settings.upstream_proxy_enabled is True
    assert settings.upstream_proxy_url == "http://127.0.0.1:7891"
    assert (tmp_path / "user-data" / "config.json").exists()


def test_default_total_retry_attempts_is_ten(tmp_path, monkeypatch):
    """新配置默认将单个请求限制为 10 次总尝试。"""
    monkeypatch.setenv("AIMUX_DATA_DIR", str(tmp_path / "user-data"))
    assert load_settings().request_retry_attempts == 10
    assert load_settings().upstream_proxy_enabled is False
    assert load_settings().upstream_proxy_url == "http://127.0.0.1:7890"


def test_total_retry_attempts_clamps_legacy_zero_value(tmp_path, monkeypatch):
    """旧配置中的 0 应规范为至少尝试一次。"""
    data_dir = tmp_path / "user-data"
    data_dir.mkdir()
    (data_dir / "config.json").write_text(
        json.dumps({"request_retry_attempts": 0}), encoding="utf-8"
    )
    monkeypatch.setenv("AIMUX_DATA_DIR", str(data_dir))
    assert load_settings().request_retry_attempts == 1


def test_desktop_local_api_url_replaces_wildcard_listen_address():
    """桌面端不应将服务监听通配地址作为本机请求目标。"""
    assert local_api_base_url("0.0.0.0", 7788) == "http://127.0.0.1:7788"
    assert local_api_base_url("::", 7788) == "http://[::1]:7788"
    assert local_api_base_url("127.0.0.1", 7788) == "http://127.0.0.1:7788"


def test_github_link_shows_url_then_opens_default_browser(monkeypatch):
    """侧栏 GitHub 入口先提示地址，再交给系统默认浏览器。"""
    from app.ui import main_window

    messages: list[tuple[str, str]] = []
    opened: list[str] = []
    monkeypatch.setattr(
        main_window.QMessageBox,
        "information",
        lambda _, title, message: messages.append((title, message)),
    )
    monkeypatch.setattr(
        main_window.QDesktopServices,
        "openUrl",
        lambda url: opened.append(url.toString()) or True,
    )

    main_window.MainWindow.open_github(object())

    assert messages == [("打开 GitHub", "将使用默认浏览器打开：\nhttps://github.com/liujie99606/AIMux.git")]
    assert opened == ["https://github.com/liujie99606/AIMux.git"]


def test_main_window_constructs_github_link(monkeypatch):
    """主窗口应能构造侧栏 GitHub 按钮。"""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QWidget

    from app.config import Settings
    from app.ui import main_window

    class EmptyView(QWidget):
        """隔离主窗口布局测试，避免访问本地 API。"""

        def __init__(self, *_: object) -> None:
            super().__init__()

    for view_name in (
        "AccountsView",
        "UsageView",
        "StatisticsView",
        "ModelsView",
        "MonitorView",
        "SettingsView",
    ):
        monkeypatch.setattr(main_window, view_name, EmptyView)

    application = QApplication.instance() or QApplication([])
    window = main_window.MainWindow(Settings())
    assert window.github_button.text() == "GitHub"
    assert window.github_button.toolTip() == "https://github.com/liujie99606/AIMux.git"
    window.tray.hide()
    window.deleteLater()
    application.processEvents()


def test_main_window_lazily_creates_only_selected_page(monkeypatch):
    """主窗口启动时只创建当前页面，切换菜单后才创建目标页面。"""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QWidget
    from PySide6.QtTest import QTest

    from app.config import Settings
    from app.ui import main_window

    created: list[str] = []

    def factory(name: str):
        class EmptyView(QWidget):
            """记录创建次数的页面占位。"""

            def __init__(self, *_args: object) -> None:
                super().__init__()
                created.append(name)

        return EmptyView

    for view_name in (
        "AccountsView",
        "UsageView",
        "StatisticsView",
        "ModelsView",
        "MonitorView",
        "SettingsView",
    ):
        monkeypatch.setattr(main_window, view_name, factory(view_name))

    application = QApplication.instance() or QApplication([])
    window = main_window.MainWindow(Settings())
    assert created == []
    assert window._page_widgets == [None] * 6

    window.load_current_page()
    QTest.qWait(70)
    application.processEvents()
    assert created == ["AccountsView"]
    assert window._page_widgets[0] is not None

    window.navigation.setCurrentRow(3)
    assert created == ["AccountsView", "ModelsView"]
    assert window._page_widgets[3] is not None
    window.tray.hide()
    window.deleteLater()
    application.processEvents()


def test_main_window_reload_rebuilds_selected_page_once(monkeypatch):
    """非首页热重载应稳定清空内容栈，并只创建一次当前页面。"""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QWidget

    from app.config import Settings
    from app.ui import main_window

    events: list[str] = []

    class View(QWidget):
        def __init__(self, *_args: object) -> None:
            super().__init__()
            events.append("create")

        def refresh(self) -> None:
            events.append("refresh")

    view_names = (
        "AccountsView",
        "UsageView",
        "StatisticsView",
        "ModelsView",
        "MonitorView",
        "SettingsView",
    )
    for name in view_names:
        monkeypatch.setattr(main_window, name, View)

    application = QApplication.instance() or QApplication([])
    window = main_window.MainWindow(Settings())
    window._server_ready = True
    window.navigation.setCurrentRow(3)
    events.clear()

    window._reload_views()

    assert window.navigation.currentRow() == 3
    assert events == ["create"]
    assert window.content.count() == 6
    window.tray.hide()
    window.deleteLater()
    application.processEvents()


def test_account_background_refresh_does_not_block_qt_event_loop(monkeypatch):
    """慢账号查询应在线程池运行，不能阻塞窗口事件循环。"""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from app.ui.views.accounts_view import AccountsView

    class SlowClient:
        def get(self, path: str, **_kwargs: object) -> dict[str, list[dict]]:
            assert path == "/api/accounts"
            time.sleep(0.3)
            return {"items": []}

    application = QApplication.instance() or QApplication([])
    heartbeat: list[bool] = []
    started = time.perf_counter()
    view = AccountsView(SlowClient())
    elapsed = time.perf_counter() - started
    QTimer.singleShot(10, lambda: heartbeat.append(True))

    _wait_until(lambda: bool(heartbeat), 100)

    assert elapsed < 0.15
    view.deleteLater()
    application.processEvents()


def test_background_loader_discards_stale_query_result(monkeypatch):
    """连续查询乱序完成时只允许最新结果更新页面。"""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from app.ui.components.common.background_loader import BackgroundLoader

    application = QApplication.instance() or QApplication([])
    loader = BackgroundLoader()
    results: list[str] = []
    loader.loaded.connect(results.append)

    def slow_old_query() -> str:
        time.sleep(0.15)
        return "old"

    loader.load(slow_old_query)
    loader.load(lambda: "new")
    _wait_until(lambda: results == ["new"])
    time.sleep(0.2)
    application.processEvents()

    assert results == ["new"]
    loader.deleteLater()
    application.processEvents()


def test_background_task_survives_page_loader_deletion(monkeypatch):
    """页面销毁时运行中的查询应安全结束，不能访问已释放的信号对象。"""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QThreadPool
    from PySide6.QtWidgets import QApplication

    from app.ui.components.common.background_loader import BackgroundLoader, _ACTIVE_TASKS

    application = QApplication.instance() or QApplication([])
    loader = BackgroundLoader()
    loader.load(lambda: time.sleep(0.1))
    loader.deleteLater()
    application.processEvents()

    assert QThreadPool.globalInstance().waitForDone(1000)
    application.processEvents()
    assert not _ACTIVE_TASKS


def test_account_priority_change_refreshes_account_list(monkeypatch):
    """账号优先级保存后应重新查询列表，以应用最新排序。"""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from app.ui.views.accounts_view import AccountsView

    class FakeClient:
        """提供账号视图构造与优先级保存所需的最小 API 响应。"""

        def __init__(self) -> None:
            self.put_calls: list[tuple[str, dict]] = []

        def get(self, path: str, **_: object) -> dict[str, list[dict]]:
            assert path == "/api/accounts"
            return {"items": []}

        def put(self, path: str, *, json: dict) -> None:
            self.put_calls.append((path, json))

    application = QApplication.instance() or QApplication([])
    client = FakeClient()
    view = AccountsView(client)
    view.accounts = {"account-1": {"priority": 5}}
    refreshes: list[bool] = []
    monkeypatch.setattr(view, "refresh", lambda: refreshes.append(True))

    view.change_priority("account-1", 6)

    assert client.put_calls == [("/api/accounts/account-1", {"priority": 6})]
    assert refreshes == [True]
    view.deleteLater()
    application.processEvents()


def test_desktop_components_are_constructible(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from app.ui.components.common.priority_editor import PriorityEditor
    from app.ui.components.common.current_time_label import CurrentTimeLabel
    from app.ui.components.accounts.status_badge import StatusBadge
    from app.ui.components.monitor_status_grid import MonitorStatusGrid
    from app.ui.views.models_view import ModelsView
    from app.ui.views.monitor_view import MonitorView
    from app.ui.components.usage.usage_filter import UsageFilter
    from app.ui.components.usage.usage_pagination import UsagePagination
    from app.ui.views.statistics_view import StatisticsView

    application = QApplication.instance() or QApplication([])
    priority = PriorityEditor(5)
    badge = StatusBadge("active")
    filters = UsageFilter()
    filters.model.setText("gpt-test")
    assert priority.value() == 5
    assert badge.text() == "启用"
    assert filters.parameters()["model"] == "gpt-test"
    assert filters.parameters()["limit"] == 20
    assert filters.parameters(offset=20)["offset"] == 20
    filters.account.setText("account-a")
    filters.type.setCurrentText("openai")
    filters.success.setCurrentText("失败")
    filters.started_after.setText("2026-08-01T00:00:00Z")
    filters.reset_button.click()
    assert filters.parameters() == {"offset": 0, "limit": 20}
    cleanup_requests: list[bool] = []
    filters.cleanup_requested.connect(lambda: cleanup_requests.append(True))
    filters.cleanup_button.click()
    assert cleanup_requests == [True]
    class FakeClient:
        calls: list[tuple[str, dict[str, dict[str, str]]]]

        def __init__(self):
            self.calls = []

        def get(self, path: str, **kwargs: dict[str, str]) -> dict[str, list[dict]]:
            self.calls.append((path, kwargs))
            return {"items": []}

    fake_client = FakeClient()
    models_view = ModelsView(fake_client)
    models_view.type_filter.setCurrentText("anthropic")
    _wait_until(
        lambda: bool(fake_client.calls)
        and fake_client.calls[-1] == ("/api/models", {"params": {"type": "anthropic"}})
    )
    assert fake_client.calls[-1] == ("/api/models", {"params": {"type": "anthropic"}})
    statistics_view = StatisticsView(fake_client)
    _wait_until(
        lambda: bool(fake_client.calls)
        and fake_client.calls[-1] == ("/api/usage/statistics", {})
    )
    assert fake_client.calls[-1] == ("/api/usage/statistics", {})
    pagination = UsagePagination()
    clock = CurrentTimeLabel()
    monitor_grid = MonitorStatusGrid()
    monitor_grid.set_records([
        {"checked_at": "2026-08-01T00:00:00Z", "success": True, "duration_ms": 200, "status_code": 200},
        {"checked_at": "2026-08-01T00:02:00Z", "success": False, "duration_ms": 400, "status_code": 503, "error_message": "busy"},
    ])
    pagination.set_total(41)
    assert pagination.total_pages == 3
    assert pagination.next_button.isEnabled()
    pagination.set_total(0)
    assert not pagination.next_button.isEnabled()
    assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", clock.text())
    assert clock.timer.isActive()
    assert monitor_grid.layout().count() == 30
    assert "busy" in monitor_grid.layout().itemAt(29).widget().toolTip()
    priority.deleteLater(); badge.deleteLater(); filters.deleteLater(); pagination.deleteLater(); clock.deleteLater(); monitor_grid.deleteLater(); models_view.deleteLater(); statistics_view.deleteLater()


def test_settings_view_saves_explicit_upstream_proxy(tmp_path, monkeypatch):
    """设置页应加载并保存上游代理开关和地址。"""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QMessageBox

    from app.ui.views.settings_view import SettingsView

    class FakeClient:
        def __init__(self) -> None:
            self.token = ""
            self.payload: dict | None = None

        def get(self, path: str) -> dict:
            assert path == "/api/settings"
            return {
                "host": "127.0.0.1",
                "port": 7788,
                "db_path": "",
                "upstream_timeout_seconds": 300,
                "first_token_timeout_seconds": 60,
                "request_retry_attempts": 10,
                "upstream_proxy_enabled": False,
                "upstream_proxy_url": "http://127.0.0.1:7890",
                "monitoring_enabled": True,
                "local_token": "",
                "launch_at_login": False,
            }

        def put(self, path: str, *, json: dict) -> dict:
            assert path == "/api/settings"
            self.payload = json
            return json

    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)
    opened: list[str] = []
    monkeypatch.setattr("app.ui.views.settings_view.data_dir", lambda: tmp_path / "aimux-data")
    monkeypatch.setattr(
        "app.ui.views.settings_view.QDesktopServices.openUrl",
        lambda url: opened.append(url.toLocalFile()) or True,
    )
    application = QApplication.instance() or QApplication([])
    client = FakeClient()
    view = SettingsView(client)

    _wait_until(lambda: view.proxy_url.text() == "http://127.0.0.1:7890")
    assert not view.proxy_enabled.isChecked()
    assert not view.proxy_url.isEnabled()
    view.proxy_enabled.setChecked(True)
    assert view.proxy_url.isEnabled()
    view.save()
    assert client.payload is not None
    assert client.payload["upstream_proxy_enabled"] is True
    assert client.payload["upstream_proxy_url"] == "http://127.0.0.1:7890"
    view.open_data_button.click()
    assert [Path(path) for path in opened] == [tmp_path / "aimux-data"]

    view.deleteLater()
    application.processEvents()


def test_monitor_view_renders_accounts_and_refreshes_status(monkeypatch):
    """监控页面按 API 数据渲染账号行、状态条和开关状态。"""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from app.ui.views.monitor_view import MonitorView

    class FakeClient:
        def get(self, path: str, **kwargs):
            assert path == "/api/monitor/records"
            return {
                "monitoring_enabled": False,
                "items": [{
                    "account_name": "账号 A",
                    "account_type": "openai",
                    "records": [{
                        "checked_at": "2026-08-01T00:00:00Z",
                        "model": "gpt-test",
                        "success": True,
                        "duration_ms": 250,
                        "status_code": 200,
                    }],
                }],
            }

    application = QApplication.instance() or QApplication([])
    view = MonitorView(FakeClient())
    _wait_until(lambda: view.table.rowCount() == 1)
    assert view.status.text() == "监控已关闭"
    assert view.table.item(0, 0).text() == "账号 A"
    assert view.table.item(0, 2).text() == "0.10"
    assert view.table.item(0, 3).text() == "gpt-test"
    assert view.table.item(0, 5).text() == "0.2 s"
    assert view.table.item(0, 6).text() == "成功"
    assert view.table.columnCount() == 8
    status_grid = view.table.cellWidget(0, 7)
    assert status_grid is not None and status_grid.minimumWidth() == 750
    assert status_grid.layout().itemAt(29).widget().toolTip().startswith("检查时间：")
    view.deleteLater()
    application.processEvents()
