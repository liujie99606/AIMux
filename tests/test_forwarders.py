from __future__ import annotations

from app.config import Settings
from app.models import Account
from app.service import account_service
from app.schemas import AccountCreate
from app.utils.forwarders import _client, _headers, upstream_url


def test_protocol_headers_and_urls_follow_account_type(session):
    openai = account_service.create_account(session, AccountCreate(name="o", base_url="https://openai.example/v1", api_key="openai-key"))
    anthropic = account_service.create_account(session, AccountCreate(name="a", type="anthropic", base_url="https://anthropic.example", api_key="anthropic-key"))
    assert _headers(openai, {})["Authorization"] == "Bearer openai-key"
    headers = _headers(anthropic, {})
    assert headers["x-api-key"] == "anthropic-key"
    assert headers["anthropic-version"] == "2023-06-01"
    assert upstream_url(openai, "/v1/responses") == "https://openai.example/v1/responses"
    assert upstream_url(anthropic, "/v1/messages") == "https://anthropic.example/v1/messages"


def test_upstream_proxy_setting_is_explicit_and_can_be_disabled(monkeypatch):
    """上游 HTTP 客户端只使用 AIMux 设置中的代理开关和地址。"""
    calls: list[dict] = []

    class FakeClient:
        def __init__(self, **kwargs) -> None:
            calls.append(kwargs)

    monkeypatch.setattr("app.utils.forwarders.httpx.AsyncClient", FakeClient)

    _client(Settings(upstream_proxy_enabled=True, upstream_proxy_url="http://127.0.0.1:7890"))
    _client(Settings(upstream_proxy_enabled=False))

    assert calls[0]["proxy"] == "http://127.0.0.1:7890"
    assert calls[1]["proxy"] is None
    assert all(call["trust_env"] is False for call in calls)
