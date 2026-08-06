from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.dao import model_dao
from app.db import get_session
from app.schemas import ModelCreate, ModelUpdate, ModelView
from app.service import model_service

router = APIRouter(prefix="/api/models", tags=["models"])


def _model(session: Session, model_id: str):
    """读取模型维护对象，不存在时返回统一 404 错误。"""
    model = model_dao.get(session, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    return model


@router.get("")
def list_all(type: str | None = None, session: Session = Depends(get_session)):
    """按可选协议类型返回全部模型目录。"""
    return {"items": [model_service.to_view(item) for item in model_dao.list_models(session, type)]}


@router.post("", response_model=ModelView)
def create(payload: ModelCreate, session: Session = Depends(get_session)):
    """新增模型目录记录。"""
    return model_service.to_view(model_service.create_model(session, payload))


@router.put("/{model_id}", response_model=ModelView)
def update(model_id: str, payload: ModelUpdate, session: Session = Depends(get_session)):
    """编辑模型名称或协议类型。"""
    return model_service.to_view(model_service.update_model(session, _model(session, model_id), payload))


@router.delete("/{model_id}", status_code=204)
def remove(model_id: str, session: Session = Depends(get_session)):
    """删除不再需要的模型目录记录。"""
    model_service.delete_model(session, _model(session, model_id))


@router.post("/{model_id}/set-default", response_model=ModelView)
def set_default(model_id: str, session: Session = Depends(get_session)):
    """将指定模型设为其协议类型的测试默认，同类型其他模型清除默认。"""
    return model_service.to_view(model_service.set_default(session, _model(session, model_id)))
