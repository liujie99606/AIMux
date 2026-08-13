from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.config import Settings
from app.controller.dependencies import app_settings
from app.dao import account_dao
from app.db import get_session
from app.schemas import AccountCreate, AccountUpdate, AccountView, TestRequest, TestResult
from app.service import account_service
from app.service import monitor_service

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def _account(session: Session, account_id: str):
    account = account_dao.get(session, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    return account


@router.post("", response_model=AccountView)
def create(payload: AccountCreate, session: Session = Depends(get_session)):
    return account_service.to_view(account_service.create_account(session, payload))


@router.get("")
def list_all(
    offset: int = 0, limit: int = 50, type: str | None = None, status: str | None = None,
    session: Session = Depends(get_session),
):
    records, total = account_dao.list_accounts(session, offset=offset, limit=min(limit, 200), account_type=type, status=status)
    return {"items": [account_service.to_view(item) for item in records], "total": total}


@router.get("/{account_id}", response_model=AccountView)
def get_one(account_id: str, session: Session = Depends(get_session)):
    return account_service.to_view(_account(session, account_id))


@router.put("/{account_id}", response_model=AccountView)
def update(account_id: str, payload: AccountUpdate, session: Session = Depends(get_session)):
    return account_service.to_view(account_service.update_account(session, _account(session, account_id), payload))


@router.delete("/{account_id}", status_code=204)
def remove(account_id: str, session: Session = Depends(get_session)):
    account_dao.delete(session, _account(session, account_id))


async def _test_one(session: Session, account_id: str, model: str | None, settings: Settings) -> dict:
    account = _account(session, account_id)
    chosen_model = monitor_service.test_model(session, account, model)
    if chosen_model is None:
        return TestResult(
            account_id=account.id,
            success=False,
            error_code="test_model_unavailable",
            error_message="该协议尚未配置测试默认模型",
        ).model_dump()
    try:
        response = await monitor_service.send_ping(account, chosen_model, settings)
    except Exception as exc:
        account_service.record_test_failure(session, account, "test_connection_error", str(exc))
        return TestResult(account_id=account.id, success=False, error_code="test_connection_error", error_message=str(exc), model=chosen_model).model_dump()
    if 200 <= response.status_code < 300:
        account_service.record_test_success(session, account, chosen_model)
        return TestResult(account_id=account.id, success=True, status_code=response.status_code, response_body=response.content[:4096].decode("utf-8", errors="replace"), model=chosen_model).model_dump()
    content = response.content[:4096].decode("utf-8", errors="replace")
    account_service.record_test_failure(session, account, "test_failed", content)
    return TestResult(account_id=account.id, success=False, status_code=response.status_code, error_code="test_failed", error_message=content, model=chosen_model).model_dump()


@router.post("/{account_id}/test", response_model=TestResult)
async def test(account_id: str, payload: TestRequest | None = None, session: Session = Depends(get_session), settings: Settings = Depends(app_settings)):
    return await _test_one(session, account_id, payload.model if payload else None, settings)


@router.post("/{account_id}/super-priority", response_model=AccountView)
def make_super(account_id: str, session: Session = Depends(get_session)):
    return account_service.to_view(account_service.set_super_priority(session, _account(session, account_id)))


@router.post("/{account_id}/toggle-status", response_model=AccountView)
def toggle(account_id: str, session: Session = Depends(get_session)):
    return account_service.to_view(account_service.toggle_status(session, _account(session, account_id)))


@router.post("/{account_id}/adjust-priority", response_model=AccountView)
def adjust_priority(account_id: str, delta: int, session: Session = Depends(get_session)):
    """按 delta 增减优先级，自动限制在 0-9 范围内。"""
    return account_service.to_view(account_service.adjust_priority(session, _account(session, account_id), delta))
