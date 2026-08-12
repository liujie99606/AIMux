from __future__ import annotations

from pathlib import Path
from typing import Any, Generator

from sqlmodel import Session, create_engine

from app.database_migrations import migrate_database
from app.service.model_service import seed_defaults

_engine = None


def configure_database(path: Path | str) -> Any:
    """迁移 SQLite 数据库后配置引擎并播种默认模型。"""
    global _engine
    db_path = Path(path).expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    migrate_database(db_path)
    _engine = create_engine(
        f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False}
    )
    with Session(_engine) as session:
        seed_defaults(session)
    return _engine


def get_engine():
    """返回已初始化的全局数据库引擎，避免业务层重复创建连接。"""
    if _engine is None:
        raise RuntimeError("Database has not been configured")
    return _engine


def get_session() -> Generator[Session, None, None]:
    """为 FastAPI 请求提供独立的数据库会话，并在请求结束后自动关闭。"""
    with Session(get_engine()) as session:
        yield session
