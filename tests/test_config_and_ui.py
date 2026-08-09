from __future__ import annotations

import json
import re

from app.config import load_settings
from app.ui.client import local_api_base_url


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
    assert fake_client.calls[-1] == ("/api/models", {"params": {"type": "anthropic"}})
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
    priority.deleteLater(); badge.deleteLater(); filters.deleteLater(); pagination.deleteLater(); clock.deleteLater(); monitor_grid.deleteLater(); models_view.deleteLater()


def test_settings_view_saves_explicit_upstream_proxy(monkeypatch):
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
    application = QApplication.instance() or QApplication([])
    client = FakeClient()
    view = SettingsView(client)

    assert not view.proxy_enabled.isChecked()
    assert not view.proxy_url.isEnabled()
    view.proxy_enabled.setChecked(True)
    assert view.proxy_url.isEnabled()
    view.save()
    assert client.payload is not None
    assert client.payload["upstream_proxy_enabled"] is True
    assert client.payload["upstream_proxy_url"] == "http://127.0.0.1:7890"

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
    assert view.status.text() == "监控已关闭"
    assert view.rows.count() == 1
    row = view.rows.itemAt(0).layout()
    assert row is not None and row.itemAt(0).widget().text() == "账号 A"
    view.deleteLater()
    application.processEvents()
