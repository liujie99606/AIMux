from __future__ import annotations

from app.config import load_settings


def test_environment_overrides_config_and_uses_dynamic_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AIMUX_DATA_DIR", str(tmp_path / "user-data"))
    monkeypatch.setenv("AIMUX_PORT", "8899")
    monkeypatch.setenv("AIMUX_LAUNCH_AT_LOGIN", "true")
    settings = load_settings()
    assert settings.port == 8899
    assert settings.launch_at_login is True
    assert (tmp_path / "user-data" / "config.json").exists()


def test_desktop_components_are_constructible(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from app.ui.components.common.priority_editor import PriorityEditor
    from app.ui.components.accounts.status_badge import StatusBadge
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
    pagination = UsagePagination()
    pagination.set_total(41)
    assert pagination.total_pages == 3
    assert pagination.next_button.isEnabled()
    pagination.set_total(0)
    assert not pagination.next_button.isEnabled()
    priority.deleteLater(); badge.deleteLater(); filters.deleteLater(); pagination.deleteLater()
