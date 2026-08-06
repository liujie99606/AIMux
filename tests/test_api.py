from __future__ import annotations

from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db import get_engine
from app.main import create_app
from app.models import UsageRecord


def test_account_management_api_and_local_token(settings):
    settings.local_token = "local-secret"
    client = TestClient(create_app(settings))
    assert client.get("/api/accounts").status_code == 401
    headers = {"Authorization": "Bearer local-secret"}
    created = client.post("/api/accounts", headers=headers, json={
        "name": "OpenAI", "type": "openai", "base_url": "https://api.example/v1/", "api_key": "sk-test", "supported_models": ["gpt-test"],
    })
    assert created.status_code == 200
    account = created.json()
    assert account["base_url"] == "https://api.example/v1"
    assert "api_key" not in account
    assert client.post(f"/api/accounts/{account['id']}/super-priority", headers=headers).json()["priority"] == 9
    assert client.post(f"/api/accounts/{account['id']}/toggle-status", headers=headers).json()["status"] == "disabled"
    assert client.get("/api/accounts", headers=headers, params={"status": "disabled"}).json()["total"] == 1
    assert client.get(f"/api/accounts/{account['id']}", headers=headers).json()["id"] == account["id"]
    assert client.delete(f"/api/accounts/{account['id']}", headers=headers).status_code == 204
    assert client.get("/api/accounts", headers=headers).json()["total"] == 0


def test_settings_persists_launch_at_login_without_external_side_effects(settings, monkeypatch):
    calls: list[bool] = []
    monkeypatch.setattr("app.controller.settings_api.autostart.is_enabled", lambda: False)
    monkeypatch.setattr("app.controller.settings_api.autostart.set_enabled", calls.append)
    client = TestClient(create_app(settings))
    response = client.put("/api/settings", json={"launch_at_login": True})
    assert response.status_code == 200
    assert calls == [True]
    assert response.json()["launch_at_login"] is True


def test_compatibility_routes_select_protocol_and_models(settings, monkeypatch):
    calls: list[dict] = []

    async def fake_forward(**kwargs):
        calls.append(kwargs)
        return JSONResponse({"ok": True})

    monkeypatch.setattr("app.controller.openai_api.forward_non_stream", fake_forward)
    monkeypatch.setattr("app.controller.anthropic_api.forward_non_stream", fake_forward)
    client = TestClient(create_app(settings))
    openai = client.post("/api/accounts", json={"name": "openai", "base_url": "https://api.example/v1", "api_key": "key", "supported_models": ["gpt-test"]})
    anthropic = client.post("/api/accounts", json={"name": "anthropic", "type": "anthropic", "base_url": "https://api.anthropic.com", "api_key": "key", "supported_models": ["claude-test"]})
    assert openai.status_code == 200 and anthropic.status_code == 200
    assert client.post("/v1/chat/completions", json={"model": "gpt-test"}).status_code == 200
    assert client.post("/v1/responses", json={"model": "gpt-test"}).status_code == 200
    assert client.post("/v1/messages", json={"model": "claude-test"}).status_code == 200
    assert [item["account_type"] for item in calls] == ["openai", "openai", "anthropic"]
    openai_ids = {item["id"] for item in client.get("/v1/models").json()["data"]}
    anthropic_ids = {item["id"] for item in client.get("/v1/anthropic/models").json()["data"]}
    assert openai_ids == {"gpt-5.5", "gpt-5.5-mini", "gpt-5.5-nano"}
    assert anthropic_ids == {"claude-opus-4-8", "claude-sonnet-4-8", "claude-haiku-4-8"}


def test_usage_record_filters_summary_and_detail(settings):
    client = TestClient(create_app(settings))
    with Session(get_engine()) as session:
        session.add_all([
            UsageRecord(trace_id="a", started_at="2026-08-01T01:00:00Z", account_id="account-a", account_name="账号 A", account_type="openai", model="gpt-test", endpoint="/v1/chat/completions", success=True, duration_ms=120, total_tokens=12, attempts=1),
            UsageRecord(trace_id="b", started_at="2026-08-02T01:00:00Z", account_id="account-b", account_name="账号 B", account_type="anthropic", model="claude-test", endpoint="/v1/messages", success=False, duration_ms=240, total_tokens=4, attempts=2),
        ])
        session.commit()
    response = client.get("/api/usage/records", params={"account_id": "account-a", "success": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["summary"] == {"request_count": 1, "success_rate": 1, "average_duration_ms": 120, "total_tokens": 12}
    assert client.get(f"/api/usage/records/{payload['items'][0]['id']}").json()["trace_id"] == "a"
