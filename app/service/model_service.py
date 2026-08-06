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
        "is_default": model.is_default,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def seed_defaults(session: Session) -> None:
    """幂等补充默认模型，不覆盖用户已编辑或删除的其他记录。

    每个协议类型在尚无默认模型时，将首个种子模型标记为测试默认。
    """
    for model_type, name in DEFAULT_MODELS:
        if not model_dao.get_by_type_and_name(session, model_type, name):
            model_dao.create(session, CatalogModel(type=model_type, name=name))
    _ensure_default_per_type(session)


def _ensure_default_per_type(session: Session) -> None:
    """每个协议类型若无默认模型，则取该类型首个模型设为默认。"""
    for model_type in ("openai", "anthropic"):
        defaults = [
            item for item in model_dao.list_models(session, model_type) if item.is_default == 1
        ]
        if not defaults:
            models = model_dao.list_models(session, model_type)
            if models:
                models[0].is_default = 1
                model_dao.save(session, models[0])


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
    old_type = model.type
    was_default = model.is_default == 1
    if "type" in fields:
        model.type = target_type
    if "name" in fields:
        model.name = target_name
    # 切换类型后清除自身默认标记，不抢占新类型的已有默认。
    if "type" in fields and old_type != target_type:
        model.is_default = 0
    saved = model_dao.save(session, model)
    # 若切换类型且原模型是旧类型的默认，补一个新默认给旧类型。
    if "type" in fields and old_type != target_type and was_default:
        _ensure_default_per_type(session)
    return saved


def set_default(session: Session, model: CatalogModel) -> CatalogModel:
    """将指定模型设为其类型的测试默认，同类型其他模型清除默认标记。"""
    model_dao.clear_default_by_type(session, model.type)
    model.is_default = 1
    return model_dao.save(session, model)


def delete_model(session: Session, model: CatalogModel) -> None:
    """删除模型；若删除的是类型默认，则自动补一个新默认。"""
    model_type = model.type
    was_default = model.is_default == 1
    model_dao.delete(session, model)
    if was_default:
        _ensure_default_per_type(session)
