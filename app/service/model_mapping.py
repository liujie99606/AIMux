from __future__ import annotations

import json

from app.models import Account


def resolve_upstream_model(account: Account, requested_model: str | None) -> str | None:
    """按当前账号的精确映射解析发往上游的模型名。"""
    if requested_model is None or not account.model_mappings:
        return requested_model
    try:
        mappings = json.loads(account.model_mappings)
    except (TypeError, json.JSONDecodeError):
        return requested_model
    if not isinstance(mappings, dict):
        return requested_model
    target = mappings.get(requested_model)
    return target.strip() if isinstance(target, str) and target.strip() else requested_model
