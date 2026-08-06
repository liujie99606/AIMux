from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from app.controller.compatibility import passthrough_headers
from app.controller.dependencies import app_settings, verify_local_token
from app.controller.model_catalog import openai_model_list
from app.db import get_session
from app.service.dispatch_service import forward_non_stream, forward_stream

router = APIRouter(prefix="/v1", tags=["openai"], dependencies=[Depends(verify_local_token)])

OPENAI_HEADERS = {"openai-beta", "idempotency-key"}


async def _json_body(request: Request) -> dict[str, Any]:
    """读取 JSON 请求体，并为非 JSON 请求返回明确的兼容边界错误。"""
    try:
        body = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=415, detail="此 OpenAI 兼容端点仅支持 application/json") from exc
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    return body


async def _proxy(
    request: Request, endpoint: str, body: dict[str, Any], session: Session
):
    """通过 OpenAI 账号池转发 JSON 请求，并保留受支持的协议头。"""
    kwargs = dict(
        session=session,
        body=body,
        endpoint=endpoint,
        account_type="openai",
        client_ip=request.client.host if request.client else None,
        settings=app_settings(request),
        upstream_headers=passthrough_headers(request, OPENAI_HEADERS),
    )
    return await (forward_stream if body.get("stream") else forward_non_stream)(**kwargs)


async def _endpoint(request: Request, endpoint: str, session: Session):
    """复用统一转发逻辑暴露 OpenAI JSON POST 端点。"""
    return await _proxy(request, endpoint, await _json_body(request), session)


@router.post("/chat/completions")
async def chat_completions(request: Request, session: Session = Depends(get_session)):
    return await _endpoint(request, "/v1/chat/completions", session)


@router.post("/completions")
async def completions(request: Request, session: Session = Depends(get_session)):
    return await _endpoint(request, "/v1/completions", session)


@router.post("/responses")
async def responses(request: Request, session: Session = Depends(get_session)):
    return await _endpoint(request, "/v1/responses", session)


@router.post("/responses/{response_id}/cancel")
async def cancel_response(response_id: str, request: Request, session: Session = Depends(get_session)):
    return await _endpoint(request, f"/v1/responses/{response_id}/cancel", session)


@router.post("/responses/{response_id}/compact")
async def compact_response(response_id: str, request: Request, session: Session = Depends(get_session)):
    return await _endpoint(request, f"/v1/responses/{response_id}/compact", session)


@router.post("/embeddings")
async def embeddings(request: Request, session: Session = Depends(get_session)):
    return await _endpoint(request, "/v1/embeddings", session)


@router.post("/moderations")
async def moderations(request: Request, session: Session = Depends(get_session)):
    return await _endpoint(request, "/v1/moderations", session)


@router.post("/images/generations")
async def image_generations(request: Request, session: Session = Depends(get_session)):
    return await _endpoint(request, "/v1/images/generations", session)


@router.post("/audio/speech")
async def speech(request: Request, session: Session = Depends(get_session)):
    return await _endpoint(request, "/v1/audio/speech", session)


@router.post("/rerank")
async def rerank(request: Request, session: Session = Depends(get_session)):
    return await _endpoint(request, "/v1/rerank", session)


@router.get("/models")
def models(session: Session = Depends(get_session)):
    """返回所有启用账号已显式声明模型的 OpenAI 格式列表。"""
    return openai_model_list(session)


@router.get("/models/{model_id}")
def model_detail(model_id: str, session: Session = Depends(get_session)):
    """返回 OpenAI 客户端常用的单模型详情。"""
    catalog = {item["id"] for item in openai_model_list(session)["data"]}
    if model_id not in catalog:
        raise HTTPException(status_code=404, detail="模型不存在或未显式声明")
    return {"id": model_id, "object": "model", "owned_by": "aimux"}
