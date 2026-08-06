from __future__ import annotations

from app.models import Account
from app.service import account_service
from app.schemas import AccountCreate
from app.utils.forwarders import _headers, upstream_url


def test_protocol_headers_and_urls_follow_account_type(session):
    openai = account_service.create_account(session, AccountCreate(name="o", base_url="https://openai.example/v1", api_key="openai-key"))
    anthropic = account_service.create_account(session, AccountCreate(name="a", type="anthropic", base_url="https://anthropic.example", api_key="anthropic-key"))
    assert _headers(openai, {})["Authorization"] == "Bearer openai-key"
    headers = _headers(anthropic, {})
    assert headers["x-api-key"] == "anthropic-key"
    assert headers["anthropic-version"] == "2023-06-01"
    assert upstream_url(openai, "/v1/responses") == "https://openai.example/v1/responses"
    assert upstream_url(anthropic, "/v1/messages") == "https://anthropic.example/v1/messages"
