from __future__ import annotations

import json

from app.config import load_settings


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


def test_desktop_components_are_constructible(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from app.ui.components.common.priority_editor import PriorityEditor
    from app.ui.components.accounts.status_badge import StatusBadge
    from app.ui.views.models_view import ModelsView
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
    pagination.set_total(41)
    assert pagination.total_pages == 3
    assert pagination.next_button.isEnabled()
    pagination.set_total(0)
    assert not pagination.next_button.isEnabled()
    priority.deleteLater(); badge.deleteLater(); filters.deleteLater(); pagination.deleteLater(); models_view.deleteLater()


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
