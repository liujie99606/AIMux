from __future__ import annotations

import json
import time
from dataclasses import dataclass

import httpx
from sqlmodel import Session

from app.config import Settings
from app.dao import monitor_dao
from app.dao import model_dao
from app.models import Account, MonitorRecord, utc_now
from app.service import account_service
from app.service.model_mapping import resolve_upstream_model
from app.utils import forwarders

_MAX_ERROR_LENGTH = 4096


@dataclass(frozen=True)
class MonitorResult:
    """一次监控请求的内存结果，不包含响应正文。"""

    model: str | None
    duration_ms: int
    success: bool
    status_code: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    checked_at: str | None = None


def default_model(session: Session, account_type: str) -> str | None:
    """读取协议类型的测试默认模型。"""
    models = [item for item in model_dao.list_models(session, account_type) if item.is_default == 1]
    return models[0].name if models else None


def test_model(session: Session, account: Account, requested_model: str | None = None) -> str | None:
    """按手动指定、账号默认、协议默认的顺序确定测试或监控模型。"""
    return requested_model or account.test_default_model or default_model(session, account.type)


def _error_message(response: httpx.Response) -> str:
    """截断上游错误正文，避免监控记录保存完整响应。"""
    return response.content[:_MAX_ERROR_LENGTH].decode("utf-8", errors="replace")


def _parse_error(response: httpx.Response) -> tuple[str, str]:
    """将非 2xx 响应转换为错误码和有限长度消息。"""
    content = _error_message(response)
    try:
        payload = json.loads(content)
    except ValueError:
        return "monitor_upstream_error", content or response.reason_phrase
    error = payload.get("error", payload) if isinstance(payload, dict) else payload
    if isinstance(error, dict):
        code = str(error.get("code") or error.get("type") or "monitor_upstream_error")
        message = str(error.get("message") or content)
        return code, message[:_MAX_ERROR_LENGTH]
    return "monitor_upstream_error", content or response.reason_phrase


async def ping_account(account: Account, model: str, settings: Settings) -> MonitorResult:
    """发送一次最小协议请求，不修改账号统计、优先级或错误状态。"""
    checked_at = utc_now()
    started = time.perf_counter()
    try:
        response = await send_ping(account, model, settings)
    except httpx.TimeoutException as exc:
        return MonitorResult(model, round((time.perf_counter() - started) * 1000), False, 504, "monitor_timeout", str(exc) or "上游请求超时", checked_at)
    except httpx.HTTPError as exc:
        return MonitorResult(model, round((time.perf_counter() - started) * 1000), False, 502, "monitor_connection_error", str(exc) or "无法连接上游", checked_at)
    except Exception as exc:
        return MonitorResult(model, round((time.perf_counter() - started) * 1000), False, 502, "monitor_error", str(exc) or "监控请求失败", checked_at)
    duration = round((time.perf_counter() - started) * 1000)
    if not 200 <= response.status_code < 300:
        code, message = _parse_error(response)
        return MonitorResult(model, duration, False, response.status_code, code, message, checked_at)
    try:
        payload = response.json()
    except ValueError:
        return MonitorResult(model, duration, False, response.status_code, "monitor_invalid_response", "上游响应不是有效 JSON", checked_at)
    if not isinstance(payload, dict):
        return MonitorResult(model, duration, False, response.status_code, "monitor_invalid_response", "上游响应格式无效", checked_at)
    return MonitorResult(model, duration, True, response.status_code, checked_at=checked_at)


def build_ping_request(account: Account, model: str) -> tuple[str, dict]:
    """构造账号测试和后台监控共用的最小协议请求。"""
    if account.type == "anthropic":
        return "/v1/messages", {
            "model": model,
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "ping"}],
        }
    return "/v1/chat/completions", {
        "model": model,
        "max_tokens": 1,
        "reasoning_effort": "low",
        "messages": [{"role": "user", "content": "ping"}],
    }


async def send_ping(account: Account, model: str, settings: Settings) -> httpx.Response:
    """发送账号测试和监控共用的最小请求。"""
    upstream_model = resolve_upstream_model(account, model)
    endpoint, body = build_ping_request(account, upstream_model or model)
    return await forwarders.post(account, endpoint, body, settings)


def save_result(session: Session, account: Account, result: MonitorResult) -> MonitorRecord:
    """保存监控结果，并按监控专用规则调整账号优先级。"""
    account_service.record_monitor_result(session, account, result.success)
    return monitor_dao.create(
        session,
        MonitorRecord(
            account_id=account.id,
            account_name=account.name,
            account_type=account.type,
            model=result.model,
            checked_at=getattr(result, "checked_at", None) or utc_now(),
            duration_ms=result.duration_ms,
            success=result.success,
            status_code=result.status_code,
            error_code=result.error_code,
            error_message=result.error_message,
        ),
    )


def to_view(record: MonitorRecord) -> dict:
    """将监控记录映射为查询 API 的安全字段。"""
    return {
        "checked_at": record.checked_at,
        "model": record.model,
        "success": record.success,
        "duration_ms": record.duration_ms,
        "status_code": record.status_code,
        "error_code": record.error_code,
        "error_message": record.error_message,
    }
