from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import Session

from app.dao import model_dao
from app.models import CatalogModel
from app.schemas import ModelCreate, ModelUpdate

# 初始目录只提供用户要求的起始版本；后续型号由模型维护页增删改。
DEFAULT_MODELS = (
    ("openai", "gpt-5.5"),
    ("openai", "gpt-5.5-pro"),
    ("openai", "gpt-5.6"),
    ("openai", "gpt-5.6-sol"),
    ("openai", "gpt-5.6-terra"),
    ("openai", "gpt-5.6-luna"),
    ("anthropic", "claude-opus-4-8"),
    ("anthropic", "claude-sonnet-4-8"),
    ("anthropic", "claude-haiku-4-8"),
)


def to_view(model: CatalogModel) -> dict:
    """将数据库模型对象转换为管理 API 响应。"""
    return {
        "id": model.id,
        "name": model.name,
        "type": model.type,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def seed_defaults(session: Session) -> None:
    """幂等补充默认模型，不覆盖用户已编辑或删除的其他记录。"""
    for model_type, name in DEFAULT_MODELS:
        if not model_dao.get_by_type_and_name(session, model_type, name):
            model_dao.create(session, CatalogModel(type=model_type, name=name))


def create_model(session: Session, payload: ModelCreate) -> CatalogModel:
    """创建模型，并将重复名称转成清晰的客户端错误。"""
    if model_dao.get_by_type_and_name(session, payload.type, payload.name):
        raise HTTPException(status_code=409, detail="该类型下的模型名称已存在")
    return model_dao.create(session, CatalogModel(name=payload.name, type=payload.type))


def update_model(session: Session, model: CatalogModel, payload: ModelUpdate) -> CatalogModel:
    """更新模型前检查修改后的类型和名称是否与其他记录冲突。"""
    fields = payload.model_fields_set
    target_type = payload.type if "type" in fields else model.type
    target_name = payload.name if "name" in fields else model.name
    duplicate = model_dao.get_by_type_and_name(session, target_type, target_name)
    if duplicate and duplicate.id != model.id:
        raise HTTPException(status_code=409, detail="该类型下的模型名称已存在")
    if "type" in fields:
        model.type = target_type
    if "name" in fields:
        model.name = target_name
    return model_dao.save(session, model)
