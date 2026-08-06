from __future__ import annotations

from sqlmodel import Session, select

from app.models import CatalogModel, utc_now


def create(session: Session, model: CatalogModel) -> CatalogModel:
    """保存一条模型目录记录。"""
    session.add(model)
    session.commit()
    session.refresh(model)
    return model


def get(session: Session, model_id: str) -> CatalogModel | None:
    """按主键读取模型目录记录。"""
    return session.get(CatalogModel, model_id)


def get_by_type_and_name(session: Session, model_type: str, name: str) -> CatalogModel | None:
    """用于保证同一协议下的模型名不重复。"""
    statement = select(CatalogModel).where(CatalogModel.type == model_type, CatalogModel.name == name)
    return session.exec(statement).first()


def list_models(session: Session, model_type: str | None = None) -> list[CatalogModel]:
    """返回可用于页面选择和协议目录的模型。

    排序优先级：协议类型 → 是否测试默认（默认在前）→ 名称 → ID。
    """
    statement = select(CatalogModel)
    if model_type:
        statement = statement.where(CatalogModel.type == model_type)
    return sorted(
        session.exec(statement).all(),
        key=lambda item: (item.type, -item.is_default, item.name.lower(), item.id),
    )


def clear_default_by_type(session: Session, model_type: str) -> None:
    """清除指定协议类型下所有模型的默认标记。"""
    statement = select(CatalogModel).where(CatalogModel.type == model_type, CatalogModel.is_default == 1)
    for item in session.exec(statement).all():
        item.is_default = 0
        session.add(item)
    session.commit()


def save(session: Session, model: CatalogModel) -> CatalogModel:
    """保存模型修改并更新时间。"""
    model.updated_at = utc_now()
    session.add(model)
    session.commit()
    session.refresh(model)
    return model


def delete(session: Session, model: CatalogModel) -> None:
    """删除模型目录记录，不修改已保存账号的历史模型配置。"""
    session.delete(model)
    session.commit()
