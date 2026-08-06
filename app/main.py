from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, load_settings
from app.controller import account_api, anthropic_api, openai_api, settings_api, usage_api
from app.controller.dependencies import verify_local_token
from app.db import configure_database


def create_app(settings: Settings | None = None) -> FastAPI:
    """创建 API 应用；此处会初始化数据库并自动建表。"""
    settings = settings or load_settings()
    configure_database(settings.resolved_db_path)
    app = FastAPI(title="AIMux", version="0.1.0")
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1", "http://localhost"],
        allow_methods=["*"], allow_headers=["*"],
    )
    app.include_router(openai_api.router)
    app.include_router(anthropic_api.router)
    app.include_router(account_api.router, dependencies=[Depends(verify_local_token)])
    app.include_router(usage_api.router, dependencies=[Depends(verify_local_token)])
    app.include_router(settings_api.router, dependencies=[Depends(verify_local_token)])

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
