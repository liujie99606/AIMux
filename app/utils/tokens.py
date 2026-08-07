from __future__ import annotations

from typing import Any


TokenUsage = tuple[int | None, int | None, int | None]


def _as_token_count(value: Any) -> int | None:
    """将上游返回的 token 数值规范为非负整数。"""
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def _usage_object(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """提取 OpenAI 与 Anthropic 常见响应结构中的 usage 对象。"""
    if not isinstance(payload, dict):
        return None
    usage = payload.get("usage")
    if isinstance(usage, dict):
        return usage
    for key in ("response", "message"):
        nested = payload.get(key)
        if isinstance(nested, dict) and isinstance(nested.get("usage"), dict):
            return nested["usage"]
    return None


def extract_usage_fields(payload: dict[str, Any] | None) -> TokenUsage:
    """读取 usage 原始字段；未提供 total_tokens 时不在此处估算。"""
    usage = _usage_object(payload)
    if usage is None:
        return None, None, None
    input_tokens = _as_token_count(usage.get("input_tokens", usage.get("prompt_tokens")))
    output_tokens = _as_token_count(usage.get("output_tokens", usage.get("completion_tokens")))
    total_tokens = _as_token_count(usage.get("total_tokens"))
    return input_tokens, output_tokens, total_tokens


def extract_usage(payload: dict[str, Any] | None) -> TokenUsage:
    """提取完整响应 token 用量；上游未给总量时按输入和输出估算。"""
    input_tokens, output_tokens, total_tokens = extract_usage_fields(payload)
    if total_tokens is None and (input_tokens is not None or output_tokens is not None):
        total_tokens = (input_tokens or 0) + (output_tokens or 0)
    return input_tokens, output_tokens, total_tokens


def extract_reasoning_effort(body: dict[str, Any] | None) -> str | None:
    """从下游请求体中提取推理强度，原样记录客户端传入的值。"""
    if not isinstance(body, dict):
        return None
    effort = body.get("reasoning_effort")
    if effort is None:
        reasoning = body.get("reasoning")
        if isinstance(reasoning, dict):
            effort = reasoning.get("effort")
    if effort is None:
        return None
    return str(effort)


def extract_usage_from_sse_line(line: bytes) -> TokenUsage:
    """解析一行 SSE data 中的原始用量字段。"""
    if not line.startswith(b"data:"):
        return None, None, None
    try:
        import json

        return extract_usage_fields(json.loads(line[5:].strip()))
    except (UnicodeDecodeError, ValueError):
        return None, None, None
