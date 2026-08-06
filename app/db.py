from __future__ import annotations

from pathlib import Path
from typing import Generator

from sqlmodel import SQLModel, Session, create_engine

from app.service.model_service import seed_defaults

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
    _ensure_columns(_engine)
    # 已有数据库升级时同样会创建新表，并仅补齐缺失的默认模型。
    with Session(_engine) as session:
        seed_defaults(session)
    return _engine


def _ensure_columns(engine) -> None:
    """幂等补齐已有表缺失的列，兼容旧库升级时自动加列。"""
    additions = [
        ("usage_records", "reasoning_effort", "TEXT"),
        ("models", "is_default", "INTEGER NOT NULL DEFAULT 0"),
    ]
    with engine.connect() as conn:
        for table, column, definition in additions:
            existing = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
            if column not in existing:
                conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        conn.commit()


def get_engine():
    """返回已初始化的全局数据库引擎，避免业务层重复创建连接。"""
    if _engine is None:
        raise RuntimeError("Database has not been configured")
    return _engine


def get_session() -> Generator[Session, None, None]:
    """为 FastAPI 请求提供独立的数据库会话，并在请求结束后自动关闭。"""
    with Session(get_engine()) as session:
        yield session
