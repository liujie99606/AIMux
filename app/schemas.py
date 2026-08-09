from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


AccountType = Literal["openai", "anthropic"]
AccountStatus = Literal["active", "disabled"]


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    type: AccountType = "openai"
    base_url: str = Field(min_length=1)
    api_key: str = Field(min_length=1)
    status: AccountStatus = "active"
    priority: int = Field(default=5, ge=0, le=9)
    supported_models: list[str] | None = None
    tags: list[str] | None = None
    notes: str | None = None

    @field_validator("base_url")
    @classmethod
    def strip_base_url(cls, value: str) -> str:
        return value.rstrip("/")


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    type: AccountType | None = None
    base_url: str | None = None
    api_key: str | None = None
    status: AccountStatus | None = None
    priority: int | None = Field(default=None, ge=0, le=9)
    supported_models: list[str] | None = None
    tags: list[str] | None = None
    notes: str | None = None

    @field_validator("base_url")
    @classmethod
    def strip_base_url(cls, value: str | None) -> str | None:
        return value.rstrip("/") if value else value


class AccountView(BaseModel):
    id: str
    name: str
    type: AccountType
    base_url: str
    status: AccountStatus
    priority: int
    supported_models: list[str] | None
    tags: list[str] | None
    notes: str | None
    last_error_code: str | None
    last_error_message: str | None
    last_successful_test_model: str | None
    last_used_at: str | None
    total_requests: int
    total_tokens: int
    created_at: str
    updated_at: str


class ModelCreate(BaseModel):
    """模型维护页创建模型时提交的字段。"""
    name: str = Field(min_length=1, max_length=160)
    type: AccountType

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("模型名称不能为空")
        return value


class ModelUpdate(BaseModel):
    """模型维护页可修改模型名称和协议类型。"""
    name: str | None = Field(default=None, min_length=1, max_length=160)
    type: AccountType | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class ModelView(BaseModel):
    id: str
    name: str
    type: AccountType
    is_default: int
    created_at: str
    updated_at: str


class TestRequest(BaseModel):
    model: str | None = None


class TestResult(BaseModel):
    account_id: str
    success: bool
    status_code: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    response_body: str | None = None
    model: str | None = None


class MonitorRecordView(BaseModel):
    """监控状态格所需的单次检查结果。"""

    checked_at: str
    model: str | None = None
    success: bool
    duration_ms: int | None = None
    status_code: int | None = None
    error_code: str | None = None
    error_message: str | None = None


class MonitorAccountView(BaseModel):
    """当前启用账号的监控记录分组。"""

    account_id: str
    account_name: str
    account_type: AccountType
    model: str | None = None
    records: list[MonitorRecordView]


class MonitorResponse(BaseModel):
    """监控页面查询响应。"""

    items: list[MonitorAccountView]
    monitoring_enabled: bool


class SettingsPayload(BaseModel):
    host: str = "127.0.0.1"
    port: int = Field(default=7788, ge=1, le=65535)
    db_path: str = ""
    upstream_timeout_seconds: int = Field(default=300, ge=1, le=3600)
    first_token_timeout_seconds: int = Field(default=60, ge=1, le=3600)
    request_retry_attempts: int = Field(default=10, ge=1, le=20)
    upstream_proxy_enabled: bool = False
    upstream_proxy_url: str = "http://127.0.0.1:7890"
    monitoring_enabled: bool = True
    local_token: str = ""
    launch_at_login: bool = False

    @field_validator("upstream_proxy_url")
    @classmethod
    def validate_upstream_proxy_url(cls, value: str) -> str:
        """校验 HTTP 上游代理地址，并统一移除末尾斜杠。"""
        normalized = value.strip().rstrip("/")
        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("上游代理地址必须是 HTTP 或 HTTPS 地址")
        return normalized
