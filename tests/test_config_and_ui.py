from __future__ import annotations

import json

from app.config import load_settings


def test_environment_overrides_config_and_uses_dynamic_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AIMUX_DATA_DIR", str(tmp_path / "user-data"))
    monkeypatch.setenv("AIMUX_PORT", "8899")
    monkeypatch.setenv("AIMUX_LAUNCH_AT_LOGIN", "true")
    settings = load_settings()
    assert settings.port == 8899
    assert settings.launch_at_login is True
    assert (tmp_path / "user-data" / "config.json").exists()


def test_default_total_retry_attempts_is_ten(tmp_path, monkeypatch):
    """新配置默认将单个请求限制为 10 次总尝试。"""
    monkeypatch.setenv("AIMUX_DATA_DIR", str(tmp_path / "user-data"))
    assert load_settings().request_retry_attempts == 10


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
