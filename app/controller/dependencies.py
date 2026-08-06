from __future__ import annotations

from fastapi import HTTPException, Request


async def verify_local_token(request: Request) -> None:
    token = request.app.state.settings.local_token
    if not token:
        return
    provided = request.headers.get("authorization", "")
    if provided != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="本地令牌无效")


def app_settings(request: Request):
    return request.app.state.settings
