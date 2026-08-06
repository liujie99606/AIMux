from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.dao import usage_dao
from app.db import get_session
from app.service import usage_service

router = APIRouter(prefix="/api/usage", tags=["usage"])


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
):
    items, total = usage_dao.list_records(
        session, offset=max(offset, 0), limit=min(limit, 200), account_id=account_id, model=model,
        account_type=type, success=success, started_after=started_after, started_before=started_before,
    )
    return {
        "items": [usage_service.to_view(item) for item in items],
        "total": total,
        "summary": usage_dao.summarize(
            session, account_id=account_id, model=model, account_type=type, success=success,
            started_after=started_after, started_before=started_before,
        ),
    }


@router.get("/records/{record_id}")
def record_detail(record_id: str, session: Session = Depends(get_session)):
    record = usage_dao.get(session, record_id)
    if not record:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="使用记录不存在")
    return usage_service.to_view(record)
