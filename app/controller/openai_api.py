from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, select

from app.controller.dependencies import app_settings, verify_local_token
from app.db import get_session
from app.models import Account
from app.service.dispatch_service import forward_non_stream, forward_stream

router = APIRouter(prefix="/v1", tags=["openai"], dependencies=[Depends(verify_local_token)])


async def _proxy(request: Request, endpoint: str, body: dict[str, Any], session: Session, stream: bool):
    settings = app_settings(request)
    kwargs = dict(
        session=session, body=body, endpoint=endpoint, account_type="openai",
        client_ip=request.client.host if request.client else None, settings=settings,
    )
    return await (forward_stream if stream else forward_non_stream)(**kwargs)


@router.post("/chat/completions")
async def chat_completions(request: Request, session: Session = Depends(get_session)):
    body = await request.json()
    return await _proxy(request, "/v1/chat/completions", body, session, bool(body.get("stream")))


@router.post("/responses")
async def responses(request: Request, session: Session = Depends(get_session)):
    body = await request.json()
    return await _proxy(request, "/v1/responses", body, session, bool(body.get("stream")))


@router.get("/models")
def models(session: Session = Depends(get_session)):
    accounts = list(session.exec(select(Account).where(Account.status == "active")).all())
    result: set[str] = set()
    for account in accounts:
        if account.supported_models:
            import json
            try:
                result.update(json.loads(account.supported_models))
            except ValueError:
                pass
    return {"object": "list", "data": [{"id": model, "object": "model", "owned_by": "aimux"} for model in sorted(result)]}
