from __future__ import annotations

from pathlib import Path
from typing import Generator

from sqlmodel import SQLModel, Session, create_engine

_engine = None


def configure_database(path: Path | str):
    """配置 SQLite 引擎，并确保当前模型对应的表与索引已创建。"""
    global _engine
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _engine = create_engine(
        f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(_engine)
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
