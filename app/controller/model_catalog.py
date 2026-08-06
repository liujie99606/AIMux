from __future__ import annotations

from sqlmodel import Session, select

from app.models import CatalogModel


def models_for(session: Session, account_type: str | None = None) -> list[str]:
    """从模型目录读取模型，不受账号是否已添加或是否启用影响。"""
    statement = select(CatalogModel)
    if account_type:
        statement = statement.where(CatalogModel.type == account_type)
    return sorted(item.name for item in session.exec(statement).all())


def openai_model_list(session: Session) -> dict:
    """生成 OpenAI 兼容的模型列表响应。"""
    return {
        "object": "list",
        "data": [
            {"id": model, "object": "model", "owned_by": "aimux"}
            for model in models_for(session, "openai")
        ],
    }
