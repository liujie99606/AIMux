from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi.responses import JSONResponse, Response, StreamingResponse
from sqlmodel import Session

from app.config import Settings
from app.dao import account_dao
from app.models import Account, UsageRecord, utc_now
from app.service import account_service, usage_service
from app.utils import forwarders
from app.utils.sse import SseUsageParser
from app.utils.tokens import extract_reasoning_effort, extract_usage


@dataclass
class FailedAttempt:
    status_code: int | None
    code: str
    message: str


def pick(
    session: Session,
    model: str | None,
    account_type: str | None = None,
    exclude_ids: set[str] | None = None,
) -> Account | None:
    """每次从数据库现查一个符合协议、模型和排除条件的账号。"""
    return account_dao.pick_one(session, model, account_type, exclude_ids or set())


def _error(account_type: str, status: int, code: str, message: str) -> JSONResponse:
    """按客户端协议返回 OpenAI 或 Anthropic 兼容错误格式。"""
    if account_type == "anthropic":
        return JSONResponse(status_code=status, content={"type": "error", "error": {"type": code, "message": message}})
    return JSONResponse(status_code=status, content={"error": {"message": message, "type": code}})


def _upstream_error(response: httpx.Response) -> FailedAttempt:
    """从有限长度的上游错误响应中提取可记录、可返回的信息。"""
    content = response.content[:4096].decode("utf-8", errors="replace")
    try:
        parsed = json.loads(content)
        error = parsed.get("error", parsed)
        if isinstance(error, dict):
            return FailedAttempt(response.status_code, str(error.get("code") or error.get("type") or "upstream_error"), str(error.get("message") or content))
    except ValueError:
        pass
    return FailedAttempt(response.status_code, "upstream_error", content or response.reason_phrase)


def _exception_error(exc: Exception) -> FailedAttempt:
    """将连接、超时等 Python 异常归一为网关错误。"""
    if isinstance(exc, httpx.TimeoutException):
        return FailedAttempt(504, "upstream_timeout", str(exc) or "上游请求超时")
    if isinstance(exc, httpx.HTTPError):
        return FailedAttempt(502, "upstream_connection_error", str(exc) or "无法连接上游")
    return FailedAttempt(502, "upstream_error", str(exc) or "上游请求失败")


def _write_usage(
    session: Session,
    *,
    trace_id: str,
    started_at: str,
    started_monotonic: float,
    account: Account | None,
    model: str | None,
    endpoint: str,
    stream: bool,
    client_ip: str | None,
    attempts: int,
    success: bool,
    status_code: int | None,
    error: FailedAttempt | None = None,
    first_token_ms: int | None = None,
    reasoning_effort: str | None = None,
    tokens: tuple[int | None, int | None, int | None] = (None, None, None),
) -> None:
    """落库一次客户端请求，并同步累计命中账号的 token 统计。"""
    input_tokens, output_tokens, total_tokens = tokens
    usage_service.create_record(
        session,
        UsageRecord(
            trace_id=trace_id,
            started_at=started_at,
            ended_at=utc_now(),
            duration_ms=round((time.perf_counter() - started_monotonic) * 1000),
            first_token_ms=first_token_ms,
            account_id=account.id if account else None,
            account_name=account.name if account else None,
            account_type=account.type if account else None,
            model=model,
            reasoning_effort=reasoning_effort,
            endpoint=endpoint,
            stream=stream,
            success=success,
            status_code=status_code,
            error_code=error.code if error else None,
            error_message=error.message if error else None,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            client_ip=client_ip,
            attempts=attempts,
        ),
    )
    if account:
        account_dao.add_tokens(session, account, total_tokens)


async def forward_non_stream(
    session: Session,
    *,
    body: dict[str, Any],
    endpoint: str,
    account_type: str,
    client_ip: str | None,
    settings: Settings,
    upstream_headers: dict[str, str] | None = None,
) -> Response:
    """转发非流式请求；某个账号失败后排除它并继续现查下一个账号。"""
    model = body.get("model")
    reasoning_effort = extract_reasoning_effort(body)
    excluded: set[str] = set()
    attempts = 0
    started_monotonic = time.perf_counter()
    started_at = utc_now()
    trace_id = str(uuid.uuid4())
    last_error: FailedAttempt | None = None
    last_account: Account | None = None
    while True:
        account = pick(session, model, account_type, excluded)
        if account is None:
            break
        attempts += 1
        excluded.add(account.id)
        last_account = account
        account_dao.mark_used(session, account)
        try:
            kwargs = {"extra_headers": upstream_headers} if upstream_headers else {}
            response = await forwarders.post(account, endpoint, body, settings, **kwargs)
        except Exception as exc:
            last_error = _exception_error(exc)
            account_service.record_request_failure(session, account, last_error.code, last_error.message)
            continue
        if not 200 <= response.status_code < 300:
            last_error = _upstream_error(response)
            account_service.record_request_failure(session, account, last_error.code, last_error.message)
            continue
        try:
            payload = response.json()
        except ValueError:
            payload = None
        tokens = extract_usage(payload)
        _write_usage(
            session, trace_id=trace_id, started_at=started_at, started_monotonic=started_monotonic, account=account, model=model, endpoint=endpoint,
            stream=False, client_ip=client_ip, attempts=attempts, success=True,
            status_code=response.status_code, tokens=tokens, reasoning_effort=reasoning_effort,
        )
        content_type = response.headers.get("content-type", "application/json")
        return Response(content=response.content, status_code=response.status_code, media_type=content_type)
    final = last_error or FailedAttempt(503, "no_available_account", "没有可用账号")
    _write_usage(
        session, trace_id=trace_id, started_at=started_at, started_monotonic=started_monotonic, account=last_account, model=model, endpoint=endpoint,
        stream=False, client_ip=client_ip, attempts=attempts, success=False,
        status_code=final.status_code, error=final, reasoning_effort=reasoning_effort,
    )
    return _error(account_type, final.status_code or 502, final.code, final.message)


async def forward_stream(
    session: Session,
    *,
    body: dict[str, Any],
    endpoint: str,
    account_type: str,
    client_ip: str | None,
    settings: Settings,
    upstream_headers: dict[str, str] | None = None,
) -> Response:
    """转发 SSE 流；首块前失败可切号，首块输出后仅记录结果不重放。"""
    model = body.get("model")
    reasoning_effort = extract_reasoning_effort(body)
    excluded: set[str] = set()
    attempts = 0
    started_monotonic = time.perf_counter()
    started_at = utc_now()
    trace_id = str(uuid.uuid4())
    last_error: FailedAttempt | None = None
    last_account: Account | None = None
    selected: Account | None = None
    prepared: forwarders.PreparedStream | None = None
    first_chunk: bytes | None = None
    while True:
        account = pick(session, model, account_type, excluded)
        if account is None:
            break
        attempts += 1
        excluded.add(account.id)
        last_account = account
        account_dao.mark_used(session, account)
        try:
            kwargs = {"extra_headers": upstream_headers} if upstream_headers else {}
            candidate = await forwarders.open_stream(account, endpoint, body, settings, **kwargs)
        except Exception as exc:
            last_error = _exception_error(exc)
            account_service.record_request_failure(session, account, last_error.code, last_error.message)
            continue
        if not 200 <= candidate.response.status_code < 300:
            await candidate.response.aread()
            last_error = _upstream_error(candidate.response)
            await candidate.close()
            account_service.record_request_failure(session, account, last_error.code, last_error.message)
            continue
        try:
            initial_chunk = await asyncio.wait_for(
                candidate.first_chunk(), timeout=settings.first_token_timeout_seconds
            )
        except Exception as exc:
            last_error = _exception_error(exc)
            await candidate.close()
            account_service.record_request_failure(session, account, last_error.code, last_error.message)
            continue
        selected, prepared, first_chunk = account, candidate, initial_chunk
        break
    if not selected or not prepared:
        final = last_error or FailedAttempt(503, "no_available_account", "没有可用账号")
        _write_usage(
            session, trace_id=trace_id, started_at=started_at, started_monotonic=started_monotonic, account=last_account, model=model, endpoint=endpoint,
            stream=True, client_ip=client_ip, attempts=attempts, success=False,
            status_code=final.status_code, error=final, reasoning_effort=reasoning_effort,
        )
        return _error(account_type, final.status_code or 502, final.code, final.message)

    async def relay() -> AsyncIterator[bytes]:
        first_token_ms: int | None = None
        parser = SseUsageParser()
        stream_error: FailedAttempt | None = None
        try:
            if first_chunk is not None:
                if first_chunk:
                    first_token_ms = round((time.perf_counter() - started_monotonic) * 1000)
                    parser.feed(first_chunk)
                yield first_chunk
            async for chunk in prepared.chunks():
                if chunk and first_token_ms is None:
                    first_token_ms = round((time.perf_counter() - started_monotonic) * 1000)
                parser.feed(chunk)
                yield chunk
        except Exception as exc:
            stream_error = _exception_error(exc)
        finally:
            await prepared.close()
            parser.finish()
            # The request dependency session has closed by this point, so persist with a fresh one.
            from app.db import get_engine

            with Session(get_engine()) as record_session:
                record_account = account_dao.get(record_session, selected.id)
                _write_usage(
                    record_session, trace_id=trace_id, started_at=started_at, started_monotonic=started_monotonic, account=record_account, model=model,
                    endpoint=endpoint, stream=True, client_ip=client_ip, attempts=attempts,
                    success=stream_error is None, status_code=prepared.response.status_code,
                    error=stream_error, first_token_ms=first_token_ms, tokens=parser.usage,
                    reasoning_effort=reasoning_effort,
                )

    media_type = prepared.response.headers.get("content-type", "text/event-stream")
    return StreamingResponse(relay(), status_code=prepared.response.status_code, media_type=media_type)
