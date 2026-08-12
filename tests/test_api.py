from __future__ import annotations

from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db import get_engine
from app.main import create_app
from app.models import UsageRecord
from app.service.usage_service import _local_day_range


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
    response = client.put("/api/settings", json={
        "launch_at_login": True,
        "request_retry_attempts": 8,
        "upstream_proxy_enabled": True,
        "upstream_proxy_url": "http://127.0.0.1:7890",
    })
    assert response.status_code == 200
    assert calls == [True]
    assert response.json()["launch_at_login"] is True
    assert response.json()["request_retry_attempts"] == 8
    assert response.json()["upstream_proxy_enabled"] is True
    assert response.json()["upstream_proxy_url"] == "http://127.0.0.1:7890"
    assert client.get("/api/settings").json()["request_retry_attempts"] == 8


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
    assert openai_ids == {"gpt-5.5", "gpt-5.5-pro", "gpt-5.6", "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"}
    assert anthropic_ids == {"claude-opus-4-8", "claude-sonnet-4-8", "claude-haiku-4-8"}


def test_usage_record_filters_summary_and_detail(settings):
    client = TestClient(create_app(settings))
    with Session(get_engine()) as session:
        session.add_all([
            UsageRecord(trace_id="a", started_at="2026-08-01T01:00:00Z", account_id="account-a", account_name="账号 A", account_type="openai", model="gpt-test", endpoint="/v1/chat/completions", success=True, duration_ms=120, total_tokens=12, cached_tokens=8, attempts=1),
            UsageRecord(trace_id="b", started_at="2026-08-02T01:00:00Z", account_id="account-b", account_name="账号 B", account_type="anthropic", model="claude-test", endpoint="/v1/messages", success=False, duration_ms=240, total_tokens=4, attempts=2),
        ])
        session.commit()
    response = client.get("/api/usage/records", params={"account_id": "account-a", "success": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["summary"] == {"request_count": 1, "success_rate": 1, "average_duration_ms": 120, "total_tokens": 12}
    assert payload["items"][0]["cached_tokens"] == 8
    assert client.get(f"/api/usage/records/{payload['items'][0]['id']}").json()["trace_id"] == "a"


def test_usage_records_default_page_size_and_offset(settings):
    """使用记录列表默认每页返回 20 条，并支持按 offset 查询后续页。"""
    client = TestClient(create_app(settings))
    with Session(get_engine()) as session:
        session.add_all([
            UsageRecord(
                trace_id=f"trace-{index}",
                started_at=f"2026-08-01T00:{index:02d}:00Z",
                account_id="account-a",
                account_name="账号 A",
                account_type="openai",
                model="gpt-test",
                endpoint="/v1/chat/completions",
                success=True,
            )
            for index in range(25)
        ])
        session.commit()

    first_page = client.get("/api/usage/records").json()
    second_page = client.get("/api/usage/records", params={"offset": 20, "limit": 20}).json()
    assert first_page["total"] == 25
    assert len(first_page["items"]) == 20
    assert len(second_page["items"]) == 5
    assert first_page["items"][0]["trace_id"] == "trace-24"
    assert second_page["items"][0]["trace_id"] == "trace-4"


def test_usage_record_cleanup_removes_only_records_older_than_three_days(settings, monkeypatch):
    """手动清理只删除严格早于三天阈值的使用记录。"""
    monkeypatch.setattr("app.service.usage_service._cleanup_cutoff", lambda: "2026-08-06T12:00:00Z")
    client = TestClient(create_app(settings))
    with Session(get_engine()) as session:
        session.add_all([
            UsageRecord(trace_id="expired", started_at="2026-08-06T11:59:59Z"),
            UsageRecord(trace_id="boundary", started_at="2026-08-06T12:00:00Z"),
            UsageRecord(trace_id="recent", started_at="2026-08-07T00:00:00Z"),
        ])
        session.commit()

    response = client.delete("/api/usage/records/expired")
    assert response.status_code == 200
    assert response.json() == {"deleted": 1, "started_before": "2026-08-06T12:00:00Z"}
    payload = client.get("/api/usage/records", params={"limit": 20}).json()
    assert payload["total"] == 2
    assert {record["trace_id"] for record in payload["items"]} == {"boundary", "recent"}


def test_usage_statistics_returns_today_and_yesterday_token_totals(settings):
    """数据统计应按本地日期汇总四类 Token。"""
    client = TestClient(create_app(settings))
    yesterday_start, _ = _local_day_range(1)
    today_start, _ = _local_day_range(0)
    with Session(get_engine()) as session:
        session.add_all([
            UsageRecord(
                trace_id="yesterday", started_at=yesterday_start, input_tokens=1000,
                output_tokens=200, cached_tokens=800, total_tokens=1200,
            ),
            UsageRecord(
                trace_id="today", started_at=today_start, input_tokens=2500,
                output_tokens=300, cached_tokens=2000, total_tokens=2800,
            ),
        ])
        session.commit()

    payload = client.get("/api/usage/statistics").json()
    assert payload["yesterday"] == {
        "input_tokens": 1000, "output_tokens": 200, "cached_tokens": 800, "total_tokens": 1200,
        "cache_rate": 0.8,
    }
    assert payload["today"] == {
        "input_tokens": 2500, "output_tokens": 300, "cached_tokens": 2000, "total_tokens": 2800,
        "cache_rate": 0.8,
    }


def test_usage_statistics_groups_today_tokens_for_active_accounts(settings):
    """账号今日统计只展示启用账号，并为无记录账号补零。"""
    client = TestClient(create_app(settings))
    high = client.post(
        "/api/accounts",
        json={
            "name": "高优先级",
            "base_url": "https://high.example/v1",
            "api_key": "key",
            "priority": 9,
        },
    ).json()
    idle = client.post(
        "/api/accounts",
        json={
            "name": "无用量",
            "type": "anthropic",
            "base_url": "https://idle.example",
            "api_key": "key",
            "priority": 6,
        },
    ).json()
    disabled = client.post(
        "/api/accounts",
        json={
            "name": "已禁用",
            "base_url": "https://disabled.example/v1",
            "api_key": "key",
            "status": "disabled",
        },
    ).json()
    today_start, _ = _local_day_range(0)
    with Session(get_engine()) as session:
        session.add_all(
            [
                UsageRecord(
                    trace_id="high-1",
                    started_at=today_start,
                    account_id=high["id"],
                    input_tokens=1000,
                    output_tokens=200,
                    cached_tokens=800,
                    total_tokens=1200,
                ),
                UsageRecord(
                    trace_id="high-2",
                    started_at=today_start,
                    account_id=high["id"],
                    input_tokens=500,
                    output_tokens=100,
                    cached_tokens=200,
                    total_tokens=600,
                ),
                UsageRecord(
                    trace_id="disabled",
                    started_at=today_start,
                    account_id=disabled["id"],
                    input_tokens=999,
                    total_tokens=999,
                ),
            ]
        )
        session.commit()

    accounts = client.get("/api/usage/statistics").json()["accounts_today"]
    assert [item["account_id"] for item in accounts] == [high["id"], idle["id"]]
    assert accounts[0] == {
        "account_id": high["id"],
        "account_name": "高优先级",
        "account_type": "openai",
        "priority": 9,
        "input_tokens": 1500,
        "output_tokens": 300,
        "cached_tokens": 1000,
        "total_tokens": 1800,
        "cache_rate": 1000 / 1500,
    }
    assert accounts[1] == {
        "account_id": idle["id"],
        "account_name": "无用量",
        "account_type": "anthropic",
        "priority": 6,
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_tokens": 0,
        "total_tokens": 0,
        "cache_rate": None,
    }


def test_reasoning_effort_recorded_from_request_body(settings, monkeypatch):
    """推理强度应原样记录下游请求体中的值，缺失时为空。"""
    import httpx

    client = TestClient(create_app(settings))
    client.post("/api/accounts", json={
        "name": "openai", "base_url": "https://api.example/v1", "api_key": "key", "supported_models": ["gpt-test"],
    })

    async def fake_post(account, endpoint, body, settings, **kwargs):
        return httpx.Response(200, json={"usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}})

    monkeypatch.setattr("app.service.dispatch_service.forwarders.post", fake_post)
    client.post("/v1/chat/completions", json={"model": "gpt-test", "reasoning_effort": "high"})
    client.post("/v1/responses", json={"model": "gpt-test", "reasoning": {"effort": "low"}})
    client.post("/v1/completions", json={"model": "gpt-test"})
    items = client.get("/api/usage/records", params={"limit": 200}).json()["items"]
    efforts = {item["endpoint"]: item["reasoning_effort"] for item in items}
    assert efforts["/v1/chat/completions"] == "high"
    assert efforts["/v1/responses"] == "low"
    assert efforts["/v1/completions"] is None
