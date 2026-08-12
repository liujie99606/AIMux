from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel

from app.db import _ensure_columns


def test_existing_accounts_receive_default_multiplier(tmp_path) -> None:
    """旧账号表升级时应增加必填倍率列，并为已有数据补默认值。"""
    engine = create_engine(f"sqlite:///{(tmp_path / 'legacy.sqlite3').as_posix()}")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE accounts (id TEXT PRIMARY KEY NOT NULL)")
        connection.exec_driver_sql("INSERT INTO accounts (id) VALUES ('legacy-account')")
    # 真实启动先 create_all 补齐其他表，但不会修改已经存在的账号表。
    SQLModel.metadata.create_all(engine)

    _ensure_columns(engine)

    with engine.connect() as connection:
        columns = {
            row[1]: row for row in connection.exec_driver_sql("PRAGMA table_info(accounts)")
        }
        value = connection.exec_driver_sql(
            "SELECT multiplier FROM accounts WHERE id = 'legacy-account'"
        ).scalar_one()
    assert columns["multiplier"][3] == 1
    assert float(value) == 0.10
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "UPDATE accounts SET multiplier = 0.31 WHERE id = 'legacy-account'"
            )


def test_plaintext_api_key_column_is_renamed_to_historical_name(tmp_path) -> None:
    """中间版本的 api_key 明文列应无损恢复为历史字段名。"""
    engine = create_engine(f"sqlite:///{(tmp_path / 'key-column.sqlite3').as_posix()}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE accounts (id TEXT PRIMARY KEY NOT NULL, api_key TEXT NOT NULL)"
        )
        connection.exec_driver_sql(
            "INSERT INTO accounts (id, api_key) VALUES ('account', 'plain-key')"
        )
    SQLModel.metadata.create_all(engine)

    _ensure_columns(engine)

    with engine.connect() as connection:
        columns = {
            row[1] for row in connection.exec_driver_sql("PRAGMA table_info(accounts)")
        }
        value = connection.exec_driver_sql(
            "SELECT api_key_encrypted FROM accounts WHERE id = 'account'"
        ).scalar_one()
    assert "api_key_encrypted" in columns
    assert "api_key" not in columns
    assert value == "plain-key"
