from __future__ import annotations

import json

from sqlmodel import Session, select

from app.models import Account, utc_now


def _models(value: str | None) -> list[str]:
    """将数据库中的模型 JSON 字符串转换为模型列表；异常数据按空列表处理。"""
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return [str(item) for item in parsed] if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def create(session: Session, account: Account) -> Account:
    """持久化新账号并刷新数据库生成的字段。"""
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def get(session: Session, account_id: str) -> Account | None:
    """按主键读取账号，不存在时返回 None。"""
    return session.get(Account, account_id)


def delete(session: Session, account: Account) -> None:
    """硬删除指定账号。"""
    session.delete(account)
    session.commit()


def list_accounts(
    session: Session,
    *,
    offset: int = 0,
    limit: int = 50,
    account_type: str | None = None,
    status: str | None = None,
) -> tuple[list[Account], int]:
    """按类型和状态筛选账号，并返回当前页数据及总数。"""
    statement = select(Account)
    if account_type:
        statement = statement.where(Account.type == account_type)
    if status:
        statement = statement.where(Account.status == status)
    accounts = list(session.exec(statement).all())
    accounts.sort(
        key=lambda item: (
            item.status != "active",
            -item.priority,
            item.multiplier,
            item.name.lower(),
            item.id,
        )
    )
    return accounts[offset : offset + limit], len(accounts)


def pick_one(
    session: Session,
    model: str | None,
    account_type: str | None,
) -> Account | None:
    """从实时数据库中选择优先级最高、可用且支持模型的账号。"""
    statement = select(Account).where(Account.status == "active")
    if account_type:
        statement = statement.where(Account.type == account_type)
    candidates = list(session.exec(statement).all())
    eligible = [
        account for account in candidates
        if model is None or not _models(account.supported_models) or model in _models(account.supported_models)
    ]
    # 明确声明模型的账号优先于通配账号，其次按优先级、倍率和稳定名称排序。
    eligible.sort(
        key=lambda item: (
            -(model in _models(item.supported_models)),
            -item.priority,
            item.multiplier,
            item.name.lower(),
            item.id,
        )
    )
    return eligible[0] if eligible else None


def save(session: Session, account: Account) -> Account:
    """保存账号变更，同时刷新更新时间。"""
    account.updated_at = utc_now()
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def mark_used(session: Session, account: Account) -> None:
    """记录一次账号命中，不参与后续调度排序。"""
    account.total_requests += 1
    account.last_used_at = utc_now()
    save(session, account)


def add_tokens(session: Session, account: Account, tokens: int | None) -> None:
    """将上游返回的 token 数累加到账号统计。"""
    if not tokens:
        return
    account.total_tokens += tokens
    save(session, account)
