from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, select

from app.controller.dependencies import verify_local_token
from app.db import get_session
from app.models import Account
from app.service.dispatch_service import forward_non_stream, forward_stream

router = APIRouter(prefix="/v1", tags=["anthropic"], dependencies=[Depends(verify_local_token)])


@router.post("/messages")
async def messages(request: Request, session: Session = Depends(get_session)):
    body: dict[str, Any] = await request.json()
    settings = request.app.state.settings
    kwargs = dict(
        session=session, body=body, endpoint="/v1/messages", account_type="anthropic",
        client_ip=request.client.host if request.client else None, settings=settings,
    )
    return await (forward_stream if body.get("stream") else forward_non_stream)(**kwargs)


@router.get("/anthropic/models")
def anthropic_models(session: Session = Depends(get_session)):
    accounts = list(session.exec(select(Account).where(Account.type == "anthropic", Account.status == "active")).all())
    models: set[str] = set()
    for account in accounts:
        if account.supported_models:
            import json
            try:
                models.update(json.loads(account.supported_models))
            except ValueError:
                pass
    return {"data": [{"id": model, "type": "model"} for model in sorted(models)]}
