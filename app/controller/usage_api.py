from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db import get_session
from app.service import usage_service

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("/statistics")
def statistics(session: Session = Depends(get_session)) -> dict[str, Any]:
    """返回今日、昨日及各启用账号今日的 Token 汇总。"""
    return usage_service.token_statistics(session)


@router.delete("/records/expired")
def cleanup_expired_records(session: Session = Depends(get_session)) -> dict[str, int | str]:
    """删除超过三天的使用记录，并返回实际删除数量。"""
    return usage_service.cleanup_expired_records(session)


@router.get("/records")
def records(
    offset: int = 0,
    limit: int = 20,
    account_id: str | None = None,
    model: str | None = None,
    type: str | None = None,
    success: bool | None = None,
    started_after: str | None = None,
    started_before: str | None = None,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """按筛选条件分页读取使用记录。"""
    return usage_service.list_usage_records(
        session,
        offset=max(offset, 0),
        limit=min(limit, 200),
        account_id=account_id,
        model=model,
        account_type=type,
        success=success,
        started_after=started_after,
        started_before=started_before,
    )


@router.get("/records/{record_id}")
def record_detail(record_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    """返回单条使用记录详情。"""
    record = usage_service.get_usage_record(session, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="使用记录不存在")
    return record
