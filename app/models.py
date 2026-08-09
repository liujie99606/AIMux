from __future__ import annotations

import time
import uuid
from typing import Optional

from sqlalchemy import CheckConstraint, Index, UniqueConstraint
from sqlmodel import Field, SQLModel


def utc_now() -> str:
    """生成统一使用的 UTC ISO 时间字符串。"""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class Account(SQLModel, table=True):
    """上游 OpenAI 或 Anthropic API Key 账号。"""
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint("type IN ('openai', 'anthropic')", name="ck_accounts_type"),
        CheckConstraint("status IN ('active', 'disabled')", name="ck_accounts_status"),
        CheckConstraint("priority BETWEEN 0 AND 9", name="ck_accounts_priority"),
        Index("idx_accounts_dispatch", "status", "priority", "id"),
    )

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    type: str = Field(default="openai", index=True)
    base_url: str
    api_key_encrypted: bytes
    status: str = Field(default="active", index=True)
    priority: int = Field(default=5, ge=0, le=9, index=True)
    supported_models: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None
    last_error_code: Optional[str] = None
    last_error_message: Optional[str] = None
    last_successful_test_model: Optional[str] = None
    last_used_at: Optional[str] = None
    total_requests: int = 0
    total_tokens: int = 0
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class CatalogModel(SQLModel, table=True):
    """可在桌面端维护的模型目录，按上游协议类型隔离。"""
    __tablename__ = "models"
    __table_args__ = (
        CheckConstraint("type IN ('openai', 'anthropic')", name="ck_models_type"),
        UniqueConstraint("type", "name", name="uq_models_type_name"),
        Index("idx_models_type_name", "type", "name"),
    )

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(index=True)
    type: str = Field(default="openai", index=True)
    is_default: int = Field(default=0)
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class UsageRecord(SQLModel, table=True):
    """一次客户端请求的完整调度和用量记录。"""
    __tablename__ = "usage_records"
    __table_args__ = (
        Index("idx_usage_started", "started_at", "id"),
        Index("idx_usage_account", "account_id", "started_at"),
        Index("idx_usage_model", "model", "started_at"),
    )

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    trace_id: str = Field(index=True)
    started_at: str = Field(index=True)
    ended_at: Optional[str] = None
    duration_ms: Optional[int] = None
    first_token_ms: Optional[int] = None
    account_id: Optional[str] = Field(default=None, index=True)
    account_name: Optional[str] = None
    account_type: Optional[str] = None
    model: Optional[str] = Field(default=None, index=True)
    reasoning_effort: Optional[str] = None
    endpoint: Optional[str] = None
    stream: bool = False
    success: bool = False
    status_code: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    client_ip: Optional[str] = None
    attempts: int = 0


class MonitorRecord(SQLModel, table=True):
    """一次账号后台监控检查的结果快照。"""
    __tablename__ = "monitor_records"
    __table_args__ = (
        Index("idx_monitor_account_checked", "account_id", "checked_at"),
        Index("idx_monitor_checked", "checked_at", "id"),
    )

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    account_id: str = Field(index=True)
    account_name: str
    account_type: str
    model: Optional[str] = None
    checked_at: str = Field(default_factory=utc_now, index=True)
    duration_ms: Optional[int] = None
    success: bool = False
    status_code: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
