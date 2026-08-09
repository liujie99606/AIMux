from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlmodel import Session

from app.dao import usage_dao
from app.models import UsageRecord

UsageSummary = dict[str, int | float]
TokenStatistics = dict[str, int | float | None]


def create_record(session: Session, record: UsageRecord) -> UsageRecord:
    """创建一条使用记录。"""
    return usage_dao.create(session, record)


def to_view(record: UsageRecord) -> dict[str, Any]:
    """将使用记录转换为 API 响应字段。"""
    return record.model_dump()


def summary(records: list[UsageRecord]) -> UsageSummary:
    """按内存中的记录计算使用概览。"""
    count = len(records)
    successes = sum(1 for record in records if record.success)
    durations = [record.duration_ms for record in records if record.duration_ms is not None]
    tokens = sum(record.total_tokens or 0 for record in records)
    return {
        "request_count": count,
        "success_rate": successes / count if count else 0,
        "average_duration_ms": round(sum(durations) / len(durations)) if durations else 0,
        "total_tokens": tokens,
    }


def _local_day_range(days_before: int) -> tuple[str, str]:
    """返回本地日期对应的 UTC 查询区间，结束时间为开区间。"""
    local_now = datetime.now().astimezone()
    local_timezone = local_now.tzinfo
    assert local_timezone is not None
    start = datetime.combine(
        local_now.date() - timedelta(days=days_before), datetime.min.time(), local_timezone
    )
    end = start + timedelta(days=1)
    return (
        start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        end.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def _cleanup_cutoff() -> str:
    """返回使用记录保留三天的 UTC 清理阈值。"""
    return (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")


def list_usage_records(
    session: Session,
    *,
    offset: int,
    limit: int,
    account_id: str | None,
    model: str | None,
    account_type: str | None,
    success: bool | None,
    started_after: str | None,
    started_before: str | None,
) -> dict[str, Any]:
    """查询分页使用记录及同筛选条件下的汇总。"""
    items, total = usage_dao.list_records(
        session,
        offset=offset,
        limit=limit,
        account_id=account_id,
        model=model,
        account_type=account_type,
        success=success,
        started_after=started_after,
        started_before=started_before,
    )
    return {
        "items": [to_view(item) for item in items],
        "total": total,
        "summary": usage_dao.summarize(
            session,
            account_id=account_id,
            model=model,
            account_type=account_type,
            success=success,
            started_after=started_after,
            started_before=started_before,
        ),
    }


def get_usage_record(session: Session, record_id: str) -> dict[str, Any] | None:
    """读取并转换单条使用记录。"""
    record = usage_dao.get(session, record_id)
    return to_view(record) if record else None


def token_statistics(session: Session) -> dict[str, TokenStatistics]:
    """汇总本地今日和昨日的 Token 数据。"""
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


def cleanup_expired_records(session: Session) -> dict[str, int | str]:
    """删除严格早于三天阈值的使用记录。"""
    cutoff = _cleanup_cutoff()
    return {"deleted": usage_dao.delete_before(session, cutoff), "started_before": cutoff}
