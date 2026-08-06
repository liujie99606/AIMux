from __future__ import annotations

import httpx
import pytest

from app.dao import account_dao, usage_dao
from app.schemas import AccountCreate, AccountUpdate
from app.service import account_service
from app.service.dispatch_service import forward_non_stream, forward_stream, pick


def add(session, *, name: str, priority: int, models: list[str] | None):
    return account_service.create_account(
        session,
        AccountCreate(name=name, base_url="https://upstream.example/v1", api_key="secret", priority=priority, supported_models=models),
    )


def test_pick_prefers_explicit_model_then_priority_and_keeps_key_secret(session):
    wildcard = add(session, name="通用", priority=9, models=None)
    specific = add(session, name="指定", priority=3, models=["gpt-test"])
    assert pick(session, "gpt-test", "openai").id == specific.id
    assert pick(session, "other", "openai").id == wildcard.id
    view = account_service.to_view(specific)
    assert "api_key" not in view and "api_key_encrypted" not in view


def test_test_priority_linkage_never_changes_manual_status(session):
    account = add(session, name="手动停用", priority=5, models=None)
    account.status = "disabled"
    account_service.update_account(session, account, AccountUpdate(status="disabled"))
    account_service.record_test_success(session, account, "gpt-test")
    assert account.priority == 8 and account.status == "disabled"
    account_service.record_test_failure(session, account, "test_failed", "bad key")
    assert account.priority == 7 and account.status == "disabled"
    account_service.set_super_priority(session, account)
    assert account.priority == 9


@pytest.mark.asyncio
async def test_failed_request_lowers_priority_and_retries_another_account(session, settings, monkeypatch):
    first = add(session, name="第一", priority=8, models=None)
    second = add(session, name="第二", priority=5, models=None)
    calls: list[str] = []

    async def fake_post(account, endpoint, body, passed_settings):
        calls.append(account.id)
        if account.id == first.id:
            return httpx.Response(503, json={"error": {"message": "busy"}})
        return httpx.Response(200, json={"id": "ok", "usage": {"prompt_tokens": 2, "completion_tokens": 3}})

    monkeypatch.setattr("app.service.dispatch_service.forwarders.post", fake_post)
    response = await forward_non_stream(
        session, body={"model": "gpt-test"}, endpoint="/v1/chat/completions", account_type="openai",
        client_ip="127.0.0.1", settings=settings,
    )
    assert response.status_code == 200
    assert calls == [first.id, second.id]
    assert account_dao.get(session, first.id).priority == 7
    assert account_dao.get(session, second.id).priority == 6
    records, total = usage_dao.list_records(session)
    assert total == 1 and records[0].account_id == second.id and records[0].attempts == 2
    assert records[0].total_tokens == 5
    assert records[0].started_at.startswith("20")


@pytest.mark.asyncio
async def test_retry_exhausts_candidates_and_keeps_last_failed_account(session, settings, monkeypatch):
    first = add(session, name="第一", priority=8, models=None)
    second = add(session, name="第二", priority=5, models=None)
    settings.request_retry_attempts = 0
    calls: list[str] = []

    async def fake_post(account, endpoint, body, passed_settings):
        calls.append(account.id)
        return httpx.Response(503, json={"error": {"message": account.name}})

    monkeypatch.setattr("app.service.dispatch_service.forwarders.post", fake_post)
    response = await forward_non_stream(
        session, body={"model": "gpt-test"}, endpoint="/v1/chat/completions", account_type="openai",
        client_ip="127.0.0.1", settings=settings,
    )
    assert response.status_code == 503
    assert calls == [first.id, second.id]
    records, total = usage_dao.list_records(session)
    assert total == 1 and records[0].account_id == second.id and records[0].attempts == 2
    assert not records[0].success
    assert account_dao.get(session, first.id).status == "active"
    assert account_dao.get(session, second.id).status == "active"


@pytest.mark.asyncio
async def test_stream_retries_before_first_chunk_and_parses_split_sse_usage(session, settings, monkeypatch):
    first = add(session, name="第一", priority=8, models=None)
    second = add(session, name="第二", priority=5, models=None)
    calls: list[str] = []

    class FakeStream:
        def __init__(self, *, fail_first: bool, chunks: list[bytes]):
            self.fail_first = fail_first
            self._chunks = iter(chunks)
            self.response = httpx.Response(200, headers={"content-type": "text/event-stream"})

        async def first_chunk(self):
            if self.fail_first:
                raise httpx.ReadError("upstream closed")
            try:
                return next(self._chunks)
            except StopIteration:
                return None

        async def chunks(self):
            for chunk in self._chunks:
                yield chunk

        async def close(self):
            return None

    async def fake_open_stream(account, endpoint, body, passed_settings):
        calls.append(account.id)
        if account.id == first.id:
            return FakeStream(fail_first=True, chunks=[])
        return FakeStream(
            fail_first=False,
            chunks=[
                b'data: {"usage":{"prompt_tokens":2,',
                b'"completion_tokens":3}}\n\ndata: [DONE]\n\n',
            ],
        )

    monkeypatch.setattr("app.service.dispatch_service.forwarders.open_stream", fake_open_stream)
    response = await forward_stream(
        session, body={"model": "gpt-test", "stream": True}, endpoint="/v1/chat/completions",
        account_type="openai", client_ip="127.0.0.1", settings=settings,
    )
    output = b"".join([chunk async for chunk in response.body_iterator])
    assert output.endswith(b"data: [DONE]\n\n")
    assert calls == [first.id, second.id]
    session.expire_all()
    records, total = usage_dao.list_records(session)
    assert total == 1 and records[0].success and records[0].account_id == second.id
    assert records[0].attempts == 2 and records[0].first_token_ms is not None
    assert (records[0].input_tokens, records[0].output_tokens, records[0].total_tokens) == (2, 3, 5)
    assert records[0].started_at.startswith("20")
    assert account_dao.get(session, first.id).priority == 7
    assert account_dao.get(session, second.id).priority == 6


def test_request_success_priority_is_capped_and_clears_error(session):
    """真实请求成功优先级只加 1，且不会超过 9。"""
    account = add(session, name="成功账号", priority=9, models=None)
    account_service.record_request_failure(session, account, "busy", "暂时不可用")
    assert account.priority == 8
    account_service.record_request_success(session, account)
    assert account.priority == 9
    assert account.last_error_code is None
    assert account.last_error_message is None
