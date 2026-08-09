from __future__ import annotations

from collections import defaultdict

from sqlmodel import Session, select

from app.models import MonitorRecord


def create(session: Session, record: MonitorRecord) -> MonitorRecord:
    """保存一条账号监控记录。"""
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def list_grouped(
    session: Session,
    account_ids: list[str],
    limit: int = 30,
) -> dict[str, list[MonitorRecord]]:
    """按账号读取最近记录，并以旧到新顺序分组。"""
    if not account_ids:
        return {}
    statement = select(MonitorRecord).where(MonitorRecord.account_id.in_(account_ids))
    records = list(session.exec(statement).all())
    grouped: dict[str, list[MonitorRecord]] = defaultdict(list)
    for record in records:
        grouped[record.account_id].append(record)
    for account_id in grouped:
        grouped[account_id] = sorted(
            grouped[account_id], key=lambda item: (item.checked_at, item.id), reverse=True
        )[:limit]
        grouped[account_id].reverse()
    return dict(grouped)
