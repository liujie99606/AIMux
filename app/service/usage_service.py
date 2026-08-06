from __future__ import annotations

from sqlmodel import Session

from app.dao import usage_dao
from app.models import UsageRecord


def create_record(session: Session, record: UsageRecord) -> UsageRecord:
    return usage_dao.create(session, record)


def to_view(record: UsageRecord) -> dict:
    return record.model_dump()


def summary(records: list[UsageRecord]) -> dict:
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
