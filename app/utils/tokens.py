from __future__ import annotations

from typing import Any


def extract_usage(payload: dict[str, Any] | None) -> tuple[int | None, int | None, int | None]:
    if not payload:
        return None, None, None
    usage = payload.get("usage") or {}
    input_tokens = usage.get("input_tokens", usage.get("prompt_tokens"))
    output_tokens = usage.get("output_tokens", usage.get("completion_tokens"))
    total_tokens = usage.get("total_tokens")
    if total_tokens is None and (input_tokens is not None or output_tokens is not None):
        total_tokens = (input_tokens or 0) + (output_tokens or 0)
    return input_tokens, output_tokens, total_tokens


def extract_usage_from_sse_line(line: bytes) -> tuple[int | None, int | None, int | None]:
    if not line.startswith(b"data:"):
        return None, None, None
    try:
        import json

        return extract_usage(json.loads(line[5:].strip()))
    except (UnicodeDecodeError, ValueError):
        return None, None, None
