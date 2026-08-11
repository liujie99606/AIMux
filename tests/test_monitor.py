from __future__ import annotations

import asyncio
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.dao import account_dao, monitor_dao
from app.db import get_engine
from app.main import create_app
from app.models import MonitorRecord
from app.schemas import AccountCreate, AccountUpdate
from app.service import account_service
from app.service.monitor_scheduler import MonitorScheduler
from app.service.monitor_service import MonitorResult, ping_account, save_result


def add_account(session: Session, *, name: str = "监控账号", account_type: str = "openai"):
    return account_service.create_account(
        session,
        AccountCreate(
            name=name,
            type=account_type,
            base_url="https://upstream.example/v1",
            api_key="secret",
            priority=7,
        ),
    )


@pytest.mark.asyncio
async def test_ping_uses_protocol_specific_minimal_request_without_mutating_account(session, settings, monkeypatch):
    """监控 ping 按协议构造请求，并不修改账号状态、优先级或真实统计。"""
    openai = add_account(session, name="OpenAI")
    anthropic = add_account(session, name="Anthropic", account_type="anthropic")
    calls: list[tuple[str, str, dict]] = []

    async def fake_post(account, endpoint, body, passed_settings, **kwargs):
        calls.append((account.type, endpoint, body))
        return httpx.Response(200, json={"id": "ok"})

    monkeypatch.setattr("app.service.monitor_service.forwarders.post", fake_post)
    assert (await ping_account(openai, "gpt-test", settings)).success
    assert (await ping_account(anthropic, "claude-test", settings)).success

    assert calls[0] == (
        "openai",
        "/v1/chat/completions",
        {"model": "gpt-test", "max_tokens": 1, "reasoning_effort": "low", "messages": [{"role": "user", "content": "ping"}]},
    )
    assert calls[1] == (
        "anthropic",
        "/v1/messages",
        {"model": "claude-test", "max_tokens": 1, "messages": [{"role": "user", "content": "ping"}]},
    )
    refreshed = account_dao.get(session, openai.id)
    assert refreshed is not None
    assert (refreshed.priority, refreshed.status, refreshed.total_requests, refreshed.total_tokens) == (7, "active", 0, 0)


@pytest.mark.asyncio
async def test_monitor_scheduler_round_writes_success_and_adjusts_active_account_priority(session, settings, monkeypatch):
    """一轮监控只检查启用账号，成功记录会将优先级封顶调整为 6。"""
    account = add_account(session)
    disabled = add_account(session, name="停用")
    account_service.update_account(session, disabled, AccountUpdate(status="disabled"))
    settings.monitoring_enabled = True
    scheduler = MonitorScheduler(settings)
    calls: list[str] = []

    async def fake_ping(current, model, passed_settings):
        calls.append(current.id)
        return type("Result", (), {"model": model, "duration_ms": 12, "success": True, "status_code": 200, "error_code": None, "error_message": None})()

    monkeypatch.setattr("app.service.monitor_scheduler.monitor_service.ping_account", fake_ping)
    await scheduler.run_round()
    records, total = monitor_dao.list_grouped(session, [account.id, disabled.id], 30), 0

    assert calls == [account.id]
    active_records = records.get(account.id, [])
    assert len(active_records) == 1 and active_records[0].success
    assert records.get(disabled.id, []) == []
    refreshed = account_dao.get(session, account.id)
    assert refreshed is not None and (refreshed.priority, refreshed.total_requests) == (6, 0)


def test_save_monitor_result_adjusts_priority_with_monitor_limits_only(session):
    """监控成功最高为 6、失败最低为 0，且不改账号其他运行状态。"""
    account = add_account(session)
    account.last_error_code = "existing_error"
    account.last_error_message = "保留的错误"
    account_dao.save(session, account)

    save_result(session, account, MonitorResult("gpt-test", 12, True, 200))
    refreshed = account_dao.get(session, account.id)
    assert refreshed is not None
    assert (
        refreshed.priority,
        refreshed.status,
        refreshed.last_error_code,
        refreshed.last_error_message,
        refreshed.total_requests,
        refreshed.total_tokens,
    ) == (6, "active", "existing_error", "保留的错误", 0, 0)

    for _ in range(7):
        save_result(session, refreshed, MonitorResult("gpt-test", 12, False, 502))
        refreshed = account_dao.get(session, account.id)
        assert refreshed is not None
    assert refreshed.priority == 0


@pytest.mark.asyncio
async def test_scheduler_setting_update_wakes_disabled_scheduler(monkeypatch, settings):
    """关闭状态下更新为开启会立即唤醒调度器，而不是等待两分钟。"""
    scheduler = MonitorScheduler(settings)
    calls: list[str] = []

    async def fake_round():
        calls.append("round")
        scheduler._stop.set()

    monkeypatch.setattr(scheduler, "run_round", fake_round)
    settings.monitoring_enabled = False
    await scheduler.start()
    await asyncio.sleep(0)
    settings.monitoring_enabled = True
    scheduler.update_settings(settings)
    await asyncio.wait_for(scheduler._task, timeout=1)
    assert calls == ["round"]
    await scheduler.stop()


def test_monitor_api_filters_disabled_accounts_and_limits_each_account(settings):
    """监控 API 只返回启用账号，每个账号最多返回 30 条且按旧到新。"""
    client = TestClient(create_app(settings))
    with Session(get_engine()) as session:
        active = add_account(session, name="启用")
        disabled = add_account(session, name="停用")
        account_service.update_account(session, disabled, AccountUpdate(status="disabled"))
        for index in range(35):
            monitor_dao.create(
                session,
                MonitorRecord(
                    account_id=active.id,
                    account_name=active.name,
                    account_type=active.type,
                    model="gpt-test",
                    checked_at=f"2026-08-01T00:{index:02d}:00Z",
                    success=index % 2 == 0,
                    duration_ms=index,
                ),
            )
            monitor_dao.create(
                session,
                MonitorRecord(
                    account_id=disabled.id,
                    account_name=disabled.name,
                    account_type=disabled.type,
                    checked_at=f"2026-08-01T00:{index:02d}:00Z",
                    success=True,
                ),
            )
    response = client.get("/api/monitor/records", params={"limit": 99})
    assert response.status_code == 200
    payload = response.json()
    assert [item["account_name"] for item in payload["items"]] == ["启用"]
    records = payload["items"][0]["records"]
    assert len(records) == 30
    assert records[0]["checked_at"] == "2026-08-01T00:05:00Z"
    assert records[-1]["checked_at"] == "2026-08-01T00:34:00Z"


def test_monitor_settings_default_and_environment_override(tmp_path, monkeypatch):
    """监控开关默认为开启，并支持环境变量覆盖。"""
    monkeypatch.setenv("AIMUX_DATA_DIR", str(tmp_path / "data"))
    assert create_app().state.settings.monitoring_enabled is True
    monkeypatch.setenv("AIMUX_MONITORING_ENABLED", "false")
    assert create_app().state.settings.monitoring_enabled is False


def test_monitor_setting_update_is_applied_to_scheduler_immediately(settings, monkeypatch):
    """设置 API 保存监控开关后，当前调度器和查询接口立即使用新值。"""
    monkeypatch.setattr("app.controller.settings_api.autostart.is_enabled", lambda: False)
    client = TestClient(create_app(settings))
    response = client.put("/api/settings", json={"monitoring_enabled": False})
    assert response.status_code == 200
    assert response.json()["monitoring_enabled"] is False
    assert client.app.state.monitor_scheduler.settings.monitoring_enabled is False
    assert client.get("/api/monitor/records").json()["monitoring_enabled"] is False


def test_monitor_app_lifespan_stops_scheduler(settings):
    """应用退出后监控任务应被清理。"""
    app = create_app(settings)
    with TestClient(app):
        assert app.state.monitor_scheduler._task is not None
    assert app.state.monitor_scheduler._task is None
