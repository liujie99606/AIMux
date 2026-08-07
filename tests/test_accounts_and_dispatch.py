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


def test_account_list_orders_active_then_priority_then_name(session):
    """账号列表先展示启用账号，再按优先级和名称排序。"""
    add(session, name="启用低优先级", priority=1, models=None)
    add(session, name="启用高优先级", priority=9, models=None)
    disabled = add(session, name="停用高优先级", priority=9, models=None)
    account_service.update_account(session, disabled, AccountUpdate(status="disabled"))

    records, total = account_dao.list_accounts(session)

    assert total == 3
    assert [account.name for account in records] == ["启用高优先级", "启用低优先级", "停用高优先级"]


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
async def test_failed_request_retries_by_current_priority(session, settings, monkeypatch):
    """失败账号降级后，下一次尝试重新按实时优先级选择账号。"""
    first = add(session, name="第一", priority=9, models=None)
    second = add(session, name="第二", priority=6, models=None)
    settings.request_retry_attempts = 5
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
    assert calls == [first.id, first.id, first.id, first.id, second.id]
    assert account_dao.get(session, first.id).priority == 5
    assert account_dao.get(session, second.id).priority == 7
    records, total = usage_dao.list_records(session)
    assert total == 5
    assert sum(record.success for record in records) == 1
    ordered = sorted(records, key=lambda record: record.attempts)
    assert [record.attempts for record in ordered] == [1, 2, 3, 4, 5]
    successful = next(record for record in records if record.success)
    assert successful.account_id == second.id and successful.total_tokens == 5
    assert all(record.trace_id == successful.trace_id for record in records)


@pytest.mark.asyncio
async def test_retry_stops_after_total_attempt_limit(session, settings, monkeypatch):
    """总尝试次数达到上限时停止，即使仍有可用账号。"""
    first = add(session, name="第一", priority=9, models=None)
    second = add(session, name="第二", priority=6, models=None)
    settings.request_retry_attempts = 4
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
    assert calls == [first.id, first.id, first.id, first.id]
    records, total = usage_dao.list_records(session)
    assert total == 4 and all(not record.success for record in records)
    assert {record.attempts for record in records} == {1, 2, 3, 4}
    assert all(record.account_id == first.id for record in records)
    assert account_dao.get(session, first.id).status == "active"
    assert account_dao.get(session, second.id).status == "active"


@pytest.mark.asyncio
async def test_stream_retries_before_first_chunk_and_parses_split_sse_usage(session, settings, monkeypatch):
    first = add(session, name="第一", priority=9, models=None)
    second = add(session, name="第二", priority=6, models=None)
    settings.request_retry_attempts = 5
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
    assert calls == [first.id, first.id, first.id, first.id, second.id]
    session.expire_all()
    records, total = usage_dao.list_records(session)
    assert total == 5 and sum(record.success for record in records) == 1
    successful = next(record for record in records if record.success)
    assert successful.account_id == second.id and successful.attempts == 5
    assert successful.first_token_ms is not None
    assert (successful.input_tokens, successful.output_tokens, successful.total_tokens) == (2, 3, 5)
    assert {record.attempts for record in records} == {1, 2, 3, 4, 5}
    assert account_dao.get(session, first.id).priority == 5
    assert account_dao.get(session, second.id).priority == 7


def test_request_success_priority_is_capped_and_clears_error(session):
    """真实请求成功优先级只加 1，且不会超过 9。"""
    account = add(session, name="成功账号", priority=9, models=None)
    account_service.record_request_failure(session, account, "busy", "暂时不可用")
    assert account.priority == 8
    account_service.record_request_success(session, account)
    assert account.priority == 9
    assert account.last_error_code is None
    assert account.last_error_message is None
