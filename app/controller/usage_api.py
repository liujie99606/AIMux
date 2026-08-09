from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.dao import usage_dao
from app.db import get_session
from app.service import usage_service

router = APIRouter(prefix="/api/usage", tags=["usage"])


def _local_day_range(days_before: int) -> tuple[str, str]:
    """返回本地日期对应的 UTC 查询区间，结束时间为开区间。"""
    local_now = datetime.now().astimezone()
    local_timezone = local_now.tzinfo
    assert local_timezone is not None
    today = local_now.date()
    start = datetime.combine(today - timedelta(days=days_before), datetime.min.time(), local_timezone)
    end = start + timedelta(days=1)
    return (
        start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        end.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


@router.get("/statistics")
def statistics(session: Session = Depends(get_session)):
    """返回本地今日和昨日的 Token 汇总。"""
    yesterday_start, yesterday_end = _local_day_range(1)
    today_start, today_end = _local_day_range(0)
    return {
        "yesterday": usage_dao.summarize_tokens(
            session, started_after=yesterday_start, started_before=yesterday_end
        ),
        "today": usage_dao.summarize_tokens(
            session, started_after=today_start, started_before=today_end
        ),
    }


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
