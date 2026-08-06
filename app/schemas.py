from __future__ import annotations

from typing import Literal

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
    created_at: str
    updated_at: str


class BatchTestRequest(BaseModel):
    ids: list[str] = Field(min_length=1)
    model: str | None = None


class TestRequest(BaseModel):
    model: str | None = None


class TestResult(BaseModel):
    account_id: str
    success: bool
    status_code: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    model: str | None = None


class SettingsPayload(BaseModel):
    host: str = "127.0.0.1"
    port: int = Field(default=7788, ge=1, le=65535)
    db_path: str = ""
    upstream_timeout_seconds: int = Field(default=300, ge=1, le=3600)
    first_token_timeout_seconds: int = Field(default=60, ge=1, le=3600)
    request_retry_attempts: int = Field(default=1, ge=0, le=20)
    local_token: str = ""
    launch_at_login: bool = False
