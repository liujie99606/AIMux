from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.dao import account_dao, monitor_dao
from app.db import get_session
from app.schemas import MonitorResponse
from app.service import monitor_service

router = APIRouter(prefix="/api/monitor", tags=["monitor"])


@router.get("/records", response_model=MonitorResponse)
def records(request: Request, limit: int = 30, session: Session = Depends(get_session)) -> dict:
    """返回当前启用账号最近监控记录，状态按旧到新排列。"""
    limit = max(1, min(limit, 30))
    accounts, _ = account_dao.list_accounts(session, limit=10_000, status="active")
    grouped = monitor_dao.list_grouped(session, [account.id for account in accounts], limit)
    return {
        "items": [
            {
                "account_id": account.id,
                "account_name": account.name,
                "account_type": account.type,
                "multiplier": account.multiplier,
                "model": monitor_service.test_model(session, account),
                "records": [monitor_service.to_view(item) for item in grouped.get(account.id, [])],
            }
            for account in accounts
        ],
        "monitoring_enabled": request.app.state.settings.monitoring_enabled,
    }
