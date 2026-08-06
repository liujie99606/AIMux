from __future__ import annotations

import pytest
from sqlmodel import Session

from app.config import Settings
from app.db import configure_database


@pytest.fixture
def settings(tmp_path, monkeypatch):
    monkeypatch.setenv("AIMUX_DATA_DIR", str(tmp_path / "data"))
    return Settings(db_path=str(tmp_path / "aimux.sqlite3"))


@pytest.fixture
def session(settings):
    engine = configure_database(settings.resolved_db_path)
    with Session(engine) as database_session:
        yield database_session
