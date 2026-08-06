from __future__ import annotations

import json

from sqlmodel import Session

from app.dao import account_dao
from app.models import Account
from app.schemas import AccountCreate, AccountUpdate
from app.service import priority
from app.utils.crypto import encrypt_api_key


def _json(value: list[str] | None) -> str | None:
    """将可选字符串列表压缩为数据库保存的 JSON；空列表表示不限。"""
    return json.dumps(value, ensure_ascii=False) if value else None


def to_view(account: Account) -> dict:
    """转换为管理 API 可返回的账号视图，绝不暴露加密密钥。"""
    return {
        "id": account.id,
        "name": account.name,
        "type": account.type,
        "base_url": account.base_url,
        "status": account.status,
        "priority": account.priority,
        "supported_models": json.loads(account.supported_models) if account.supported_models else None,
        "tags": json.loads(account.tags) if account.tags else None,
        "notes": account.notes,
        "last_error_code": account.last_error_code,
        "last_error_message": account.last_error_message,
        "last_successful_test_model": account.last_successful_test_model,
        "last_used_at": account.last_used_at,
        "total_requests": account.total_requests,
        "total_tokens": account.total_tokens,
        "created_at": account.created_at,
        "updated_at": account.updated_at,
    }


def create_account(session: Session, payload: AccountCreate) -> Account:
    """加密上游密钥后创建账号。"""
    return account_dao.create(
        session,
        Account(
            name=payload.name,
            type=payload.type,
            base_url=payload.base_url,
            api_key_encrypted=encrypt_api_key(payload.api_key),
            status=payload.status,
            priority=payload.priority,
            supported_models=_json(payload.supported_models),
            tags=_json(payload.tags),
            notes=payload.notes,
        ),
    )


def update_account(session: Session, account: Account, payload: AccountUpdate) -> Account:
    """仅更新请求中明确提供的账号字段。"""
    fields = payload.model_fields_set
    for field in ("name", "type", "base_url", "status", "priority", "notes"):
        if field in fields:
            setattr(account, field, getattr(payload, field))
    if "api_key" in fields and payload.api_key:
        account.api_key_encrypted = encrypt_api_key(payload.api_key)
    if "supported_models" in fields:
        account.supported_models = _json(payload.supported_models)
    if "tags" in fields:
        account.tags = _json(payload.tags)
    return account_dao.save(session, account)


def set_super_priority(session: Session, account: Account) -> Account:
    """将账号优先级直接设为最高值 9。"""
    account.priority = priority.super_priority()
    return account_dao.save(session, account)


def adjust_priority(session: Session, account: Account, delta: int) -> Account:
    """按增量调整优先级，自动限制在 0-9 范围内。"""
    account.priority = max(priority.PRIORITY_MIN, min(priority.PRIORITY_MAX, account.priority + delta))
    return account_dao.save(session, account)


def toggle_status(session: Session, account: Account) -> Account:
    """在 active 与 disabled 之间人工切换账号状态。"""
    account.status = "disabled" if account.status == "active" else "active"
    return account_dao.save(session, account)


def record_test_success(session: Session, account: Account, model: str | None) -> Account:
    """记录测试成功：优先级加 3，清除最近错误，但不改变人工状态。"""
    account.priority = priority.after_test_success(account.priority)
    account.last_error_code = None
    account.last_error_message = None
    account.last_successful_test_model = model
    return account_dao.save(session, account)


def record_test_failure(
    session: Session, account: Account, error_code: str | None, error_message: str | None
) -> Account:
    """记录测试失败：优先级减 1，仅保存最近错误。"""
    account.priority = priority.after_test_failure(account.priority)
    account.last_error_code = error_code
    account.last_error_message = error_message
    return account_dao.save(session, account)


def record_request_failure(
    session: Session, account: Account, error_code: str | None, error_message: str | None
) -> Account:
    """记录真实请求失败：优先级减 1，但绝不自动停用账号。"""
    account.priority = priority.after_request_failure(account.priority)
    account.last_error_code = error_code
    account.last_error_message = error_message
    return account_dao.save(session, account)
