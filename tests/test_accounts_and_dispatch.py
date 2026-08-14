from __future__ import annotations

from decimal import Decimal

import httpx
import pytest

from app.dao import account_dao, usage_dao
from app.schemas import AccountCreate, AccountUpdate
from app.service import account_service
from app.service.model_mapping import resolve_upstream_model
from app.service.dispatch_service import forward_non_stream, forward_stream, pick


def add(
    session,
    *,
    name: str,
    priority: int,
    models: list[str] | None,
    multiplier: Decimal = Decimal("0.10"),
):
    return account_service.create_account(
        session,
        AccountCreate(
            name=name,
            base_url="https://upstream.example/v1",
            api_key="secret",
            priority=priority,
            multiplier=multiplier,
            supported_models=models,
        ),
    )


def test_pick_prefers_explicit_model_then_priority_and_returns_plaintext_key(session):
    wildcard = add(session, name="通用", priority=9, models=None)
    specific = add(session, name="指定", priority=3, models=["gpt-test"])
    assert pick(session, "gpt-test", "openai").id == specific.id
    assert pick(session, "other", "openai").id == wildcard.id
    view = account_service.to_view(specific)
    assert view["api_key"] == "secret"
    assert "api_key_encrypted" not in view


def test_pick_prefers_lower_multiplier_when_priority_is_equal(session):
    """模型匹配和优先级相同时，应优先调度倍率更低的账号。"""
    expensive = add(
        session,
        name="高倍率",
        priority=8,
        multiplier=Decimal("0.20"),
        models=["gpt-test"],
    )
    cheaper = add(
        session,
        name="低倍率",
        priority=8,
        multiplier=Decimal("0.05"),
        models=["gpt-test"],
    )

    selected = pick(session, "gpt-test", "openai")

    assert selected is not None
    assert selected.id == cheaper.id
    assert selected.id != expensive.id


def test_account_list_orders_active_then_priority_then_multiplier_then_name(session):
    """账号列表依次按状态、优先级、倍率和名称排序。"""
    add(session, name="启用低优先级", priority=1, models=None)
    add(session, name="启用高优先级", priority=9, multiplier=Decimal("0.10"), models=None)
    add(session, name="启用高优先级低倍率", priority=9, multiplier=Decimal("0.04"), models=None)
    disabled = add(session, name="停用高优先级", priority=9, models=None)
    account_service.update_account(session, disabled, AccountUpdate(status="disabled"))

    records, total = account_dao.list_accounts(session)

    assert total == 4
    assert [account.name for account in records] == [
        "启用高优先级低倍率",
        "启用高优先级",
        "启用低优先级",
        "停用高优先级",
    ]


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
async def test_retry_applies_current_account_model_mapping_without_mutating_client_body(session, settings, monkeypatch):
    """重试切换账号时应使用各自映射，且使用记录仍保留客户端模型。"""
    first = add(session, name="映射一", priority=9, models=["gpt-test"])
    second = add(
        session,
        name="映射二",
        priority=8,
        models=["gpt-test"],
        multiplier=Decimal("0.05"),
    )
    account_service.update_account(
        session, first, AccountUpdate(model_mappings={"gpt-test": "upstream-one"})
    )
    account_service.update_account(
        session, second, AccountUpdate(model_mappings={"gpt-test": "upstream-two"})
    )
    settings.request_retry_attempts = 2
    sent_models: list[tuple[str, str]] = []

    async def fake_post(account, endpoint, body, passed_settings):
        sent_models.append((account.id, body["model"]))
        if account.id == first.id:
            return httpx.Response(503, json={"error": {"message": "busy"}})
        return httpx.Response(200, json={"id": "ok"})

    monkeypatch.setattr("app.service.dispatch_service.forwarders.post", fake_post)
    client_body = {"model": "gpt-test"}
    response = await forward_non_stream(
        session, body=client_body, endpoint="/v1/chat/completions", account_type="openai",
        client_ip="127.0.0.1", settings=settings,
    )

    assert response.status_code == 200
    assert sent_models == [(first.id, "upstream-one"), (second.id, "upstream-two")]
    assert client_body == {"model": "gpt-test"}
    records, total = usage_dao.list_records(session)
    assert total == 2 and {record.model for record in records} == {"gpt-test"}


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
    assert (successful.input_tokens, successful.output_tokens, successful.total_tokens, successful.cached_tokens) == (2, 3, 5, None)
    assert {record.attempts for record in records} == {1, 2, 3, 4, 5}
    assert account_dao.get(session, first.id).priority == 5
    assert account_dao.get(session, second.id).priority == 7


@pytest.mark.asyncio
async def test_stream_uses_selected_account_model_mapping_without_mutating_client_body(
    session, settings, monkeypatch
):
    """流式请求按当前账号映射模型，且保留客户端请求模型。"""
    account = add(session, name="流式映射账号", priority=9, models=["gpt-test"])
    account_service.update_account(
        session, account, AccountUpdate(model_mappings={"gpt-test": "upstream-stream"})
    )
    sent_models: list[str] = []

    class FakeStream:
        def __init__(self) -> None:
            self.response = httpx.Response(200, headers={"content-type": "text/event-stream"})
            self._chunks = iter([b"data: [DONE]\n\n"])

        async def first_chunk(self):
            return next(self._chunks)

        async def chunks(self):
            for chunk in self._chunks:
                yield chunk

        async def close(self):
            return None

    async def fake_open_stream(account, endpoint, body, passed_settings):
        sent_models.append(body["model"])
        return FakeStream()

    monkeypatch.setattr("app.service.dispatch_service.forwarders.open_stream", fake_open_stream)
    client_body = {"model": "gpt-test", "stream": True}
    response = await forward_stream(
        session,
        body=client_body,
        endpoint="/v1/chat/completions",
        account_type="openai",
        client_ip="127.0.0.1",
        settings=settings,
    )
    _ = b"".join([chunk async for chunk in response.body_iterator])

    assert sent_models == ["upstream-stream"]
    assert client_body == {"model": "gpt-test", "stream": True}
    session.expire_all()
    records, total = usage_dao.list_records(session)
    assert total == 1
    assert records[0].model == "gpt-test"


@pytest.mark.asyncio
async def test_stream_records_usage_from_responses_completed_event(session, settings, monkeypatch):
    """Responses API 的 response.completed 事件应写入嵌套的 usage。"""
    account = add(session, name="Responses 账号", priority=9, models=None)

    class FakeStream:
        def __init__(self) -> None:
            self.response = httpx.Response(200, headers={"content-type": "text/event-stream"})
            self._chunks = iter([
                b'event: response.created\n',
                b'data: {"type":"response.created"}\n\n',
                b'event: response.completed\n',
                b'data: {"type":"response.completed","response":{"usage":{"input_tokens":4387,',
                b'"output_tokens":5,"total_tokens":4392}}}\n\n',
            ])

        async def first_chunk(self):
            return next(self._chunks)

        async def chunks(self):
            for chunk in self._chunks:
                yield chunk

        async def close(self):
            return None

    async def fake_open_stream(*args, **kwargs):
        return FakeStream()

    monkeypatch.setattr("app.service.dispatch_service.forwarders.open_stream", fake_open_stream)
    response = await forward_stream(
        session, body={"model": "gpt-test", "stream": True}, endpoint="/v1/responses",
        account_type="openai", client_ip="127.0.0.1", settings=settings,
    )
    _ = b"".join([chunk async for chunk in response.body_iterator])
    session.expire_all()
    records, total = usage_dao.list_records(session)

    assert total == 1
    assert records[0].account_id == account.id
    assert (records[0].input_tokens, records[0].output_tokens, records[0].total_tokens, records[0].cached_tokens) == (4387, 5, 4392, None)


@pytest.mark.asyncio
async def test_stream_merges_anthropic_usage_events(session, settings, monkeypatch):
    """Anthropic 分别返回输入与输出 token 时，应在同一记录中合并。"""
    account = account_service.create_account(
        session,
        AccountCreate(
            name="Anthropic 账号", type="anthropic", base_url="https://upstream.example",
            api_key="secret", priority=9,
        ),
    )

    class FakeStream:
        def __init__(self) -> None:
            self.response = httpx.Response(200, headers={"content-type": "text/event-stream"})
            self._chunks = iter([
                b'data: {"type":"message_start","message":{"usage":{"input_tokens":12}}}\n\n',
                b'data: {"type":"message_delta","usage":{"output_tokens":8}}\n\n',
            ])

        async def first_chunk(self):
            return next(self._chunks)

        async def chunks(self):
            for chunk in self._chunks:
                yield chunk

        async def close(self):
            return None

    async def fake_open_stream(*args, **kwargs):
        return FakeStream()

    monkeypatch.setattr("app.service.dispatch_service.forwarders.open_stream", fake_open_stream)
    response = await forward_stream(
        session, body={"model": "claude-test", "stream": True}, endpoint="/v1/messages",
        account_type="anthropic", client_ip="127.0.0.1", settings=settings,
    )
    _ = b"".join([chunk async for chunk in response.body_iterator])
    session.expire_all()
    records, total = usage_dao.list_records(session)

    assert total == 1
    assert records[0].account_id == account.id
    assert (records[0].input_tokens, records[0].output_tokens, records[0].total_tokens, records[0].cached_tokens) == (12, 8, 20, None)


@pytest.mark.asyncio
async def test_non_stream_records_cached_tokens(session, settings, monkeypatch):
    """非流式响应中的 prompt_tokens_details.cached_tokens 应写入使用记录。"""
    account = add(session, name="缓存账号", priority=9, models=None)

    async def fake_post(account, endpoint, body, passed_settings):
        return httpx.Response(200, json={
            "usage": {
                "prompt_tokens": 4683,
                "completion_tokens": 5,
                "total_tokens": 4688,
                "prompt_tokens_details": {"cached_tokens": 3840},
            }
        })

    monkeypatch.setattr("app.service.dispatch_service.forwarders.post", fake_post)
    response = await forward_non_stream(
        session, body={"model": "gpt-test"}, endpoint="/v1/chat/completions", account_type="openai",
        client_ip="127.0.0.1", settings=settings,
    )
    assert response.status_code == 200
    records, total = usage_dao.list_records(session)
    assert total == 1
    assert records[0].cached_tokens == 3840


def test_request_success_priority_is_capped_and_clears_error(session):
    """真实请求成功优先级只加 1，且不会超过 9。"""
    account = add(session, name="成功账号", priority=9, models=None)
    account_service.record_request_failure(session, account, "busy", "暂时不可用")
    assert account.priority == 8
    account_service.record_request_success(session, account)
    assert account.priority == 9
    assert account.last_error_code is None
    assert account.last_error_message is None


def test_model_mapping_resolves_exact_match_and_falls_back(session):
    """模型映射只做精确匹配，未命中时保持客户端模型。"""
    account = add(session, name="映射账号", priority=9, models=["gpt-test"])
    account_service.update_account(
        session, account, AccountUpdate(model_mappings={"gpt-test": "grok4.6"})
    )
    refreshed = account_dao.get(session, account.id)
    assert refreshed is not None
    assert resolve_upstream_model(refreshed, "gpt-test") == "grok4.6"
    assert resolve_upstream_model(refreshed, "other-model") == "other-model"
    assert resolve_upstream_model(refreshed, None) is None
