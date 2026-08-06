from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.config import Settings, save_settings
from app.schemas import SettingsPayload
from app.utils import autostart

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings(request: Request):
    settings = request.app.state.settings
    settings.launch_at_login = autostart.is_enabled()
    return settings


@router.put("")
def update_settings(payload: SettingsPayload, request: Request):
    settings = Settings(**payload.model_dump())
    try:
        autostart.set_enabled(settings.launch_at_login)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"无法更新开机自启: {exc}") from exc
    save_settings(settings)
    request.app.state.settings = settings
    return settings
