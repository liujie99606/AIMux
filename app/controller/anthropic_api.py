from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from app.controller.compatibility import passthrough_headers
from app.controller.dependencies import verify_local_token
from app.controller.model_catalog import models_for
from app.db import get_session
from app.service.dispatch_service import forward_non_stream, forward_stream

router = APIRouter(prefix="/v1", tags=["anthropic"], dependencies=[Depends(verify_local_token)])

ANTHROPIC_HEADERS = {"anthropic-beta", "anthropic-dangerous-direct-browser-access"}


async def _json_body(request: Request) -> dict[str, Any]:
    """读取 Anthropic JSON 请求体；本地网关不接收 multipart 协议转换。"""
    try:
        body = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=415, detail="此 Anthropic 兼容端点仅支持 application/json") from exc
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    return body


async def _proxy(request: Request, endpoint: str, body: dict[str, Any], session: Session):
    """通过 Anthropic 原生账号池转发请求，并透传 beta 兼容头。"""
    kwargs = dict(
        session=session,
        body=body,
        endpoint=endpoint,
        account_type="anthropic",
        client_ip=request.client.host if request.client else None,
        settings=request.app.state.settings,
        upstream_headers=passthrough_headers(request, ANTHROPIC_HEADERS),
    )
    return await (forward_stream if body.get("stream") else forward_non_stream)(**kwargs)


async def _endpoint(request: Request, endpoint: str, session: Session):
    """复用原生调度路径暴露 Anthropic JSON POST 端点。"""
    return await _proxy(request, endpoint, await _json_body(request), session)


@router.post("/messages")
async def messages(request: Request, session: Session = Depends(get_session)):
    return await _endpoint(request, "/v1/messages", session)


@router.post("/messages/count_tokens")
async def count_tokens(request: Request, session: Session = Depends(get_session)):
    return await _endpoint(request, "/v1/messages/count_tokens", session)


@router.post("/messages/batches")
async def message_batches(request: Request, session: Session = Depends(get_session)):
    return await _endpoint(request, "/v1/messages/batches", session)


@router.post("/complete")
async def legacy_complete(request: Request, session: Session = Depends(get_session)):
    """保留 Anthropic 旧版 Complete 端点的原样转发。"""
    return await _endpoint(request, "/v1/complete", session)


@router.get("/anthropic/models")
def anthropic_models(session: Session = Depends(get_session)):
    """提供不与 OpenAI /v1/models 冲突的 Anthropic 风格模型目录。"""
    return {"data": [{"id": model, "type": "model"} for model in models_for(session, "anthropic")]}
