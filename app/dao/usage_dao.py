from __future__ import annotations

from sqlalchemy import delete, func
from sqlmodel import Session, select

from app.models import UsageRecord


def create(session: Session, record: UsageRecord) -> UsageRecord:
    """写入一条使用记录。"""
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def get(session: Session, record_id: str) -> UsageRecord | None:
    """按主键读取使用记录详情。"""
    return session.get(UsageRecord, record_id)


def delete_before(session: Session, started_before: str) -> int:
    """删除开始时间早于指定 UTC 时间的使用记录。"""
    result = session.exec(delete(UsageRecord).where(UsageRecord.started_at < started_before))
    session.commit()
    return result.rowcount or 0


def list_records(
    session: Session,
    *,
    offset: int = 0,
    limit: int = 50,
    account_id: str | None = None,
    model: str | None = None,
    account_type: str | None = None,
    success: bool | None = None,
    started_after: str | None = None,
    started_before: str | None = None,
) -> tuple[list[UsageRecord], int]:
    """按给定维度筛选使用记录，并按时间倒序分页。"""
    statement = select(UsageRecord)
    if account_id:
        statement = statement.where(UsageRecord.account_id == account_id)
    if model:
        statement = statement.where(UsageRecord.model == model)
    if account_type:
        statement = statement.where(UsageRecord.account_type == account_type)
    if success is not None:
        statement = statement.where(UsageRecord.success == success)
    if started_after:
        statement = statement.where(UsageRecord.started_at >= started_after)
    if started_before:
        statement = statement.where(UsageRecord.started_at <= started_before)
    records = list(session.exec(statement).all())
    records.sort(key=lambda item: (item.started_at, item.id), reverse=True)
    return records[offset : offset + limit], len(records)


def summarize(
    session: Session,
    *,
    account_id: str | None = None,
    model: str | None = None,
    account_type: str | None = None,
    success: bool | None = None,
    started_after: str | None = None,
    started_before: str | None = None,
) -> dict:
    """基于同一筛选条件实时计算请求数、成功率、耗时和 token 汇总。"""
    statement = select(
        func.count(UsageRecord.id),
        func.sum(UsageRecord.success),
        func.avg(UsageRecord.duration_ms),
        func.sum(UsageRecord.total_tokens),
    )
    if account_id:
        statement = statement.where(UsageRecord.account_id == account_id)
    if model:
        statement = statement.where(UsageRecord.model == model)
    if account_type:
        statement = statement.where(UsageRecord.account_type == account_type)
    if success is not None:
        statement = statement.where(UsageRecord.success == success)
    if started_after:
        statement = statement.where(UsageRecord.started_at >= started_after)
    if started_before:
        statement = statement.where(UsageRecord.started_at <= started_before)
    count, successes, average, tokens = session.exec(statement).one()
    return {
        "request_count": count or 0,
        "success_rate": (successes or 0) / count if count else 0,
        "average_duration_ms": round(average or 0),
        "total_tokens": tokens or 0,
    }


def summarize_tokens(session: Session, *, started_after: str, started_before: str) -> dict:
    """汇总指定时间范围内的输入、输出、缓存和总 Token。"""
    statement = select(
        func.sum(UsageRecord.input_tokens),
        func.sum(UsageRecord.output_tokens),
        func.sum(UsageRecord.cached_tokens),
        func.sum(UsageRecord.total_tokens),
    ).where(
        UsageRecord.started_at >= started_after,
        UsageRecord.started_at < started_before,
    )
    input_tokens, output_tokens, cached_tokens, total_tokens = session.exec(statement).one()
    input_count = input_tokens or 0
    output_count = output_tokens or 0
    cached_count = cached_tokens or 0
    total_count = total_tokens or 0
    return {
        "input_tokens": input_count,
        "output_tokens": output_count,
        "cached_tokens": cached_count,
        "total_tokens": total_count,
        "cache_rate": cached_count / input_count if input_count else None,
    }
