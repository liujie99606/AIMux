from __future__ import annotations

import json

from sqlmodel import Session, select

from app.models import Account


def models_for(session: Session, account_type: str | None = None) -> list[str]:
    """汇总启用账号显式声明的模型；未声明模型的账号不虚构模型名。"""
    statement = select(Account).where(Account.status == "active")
    if account_type:
        statement = statement.where(Account.type == account_type)
    models: set[str] = set()
    for account in session.exec(statement).all():
        if not account.supported_models:
            continue
        try:
            parsed = json.loads(account.supported_models)
        except ValueError:
            continue
        if isinstance(parsed, list):
            models.update(str(item) for item in parsed)
    return sorted(models)


def openai_model_list(session: Session) -> dict:
    """生成 OpenAI 兼容的模型列表响应。"""
    return {
        "object": "list",
        "data": [
            {"id": model, "object": "model", "owned_by": "aimux"}
            for model in models_for(session)
        ],
    }
