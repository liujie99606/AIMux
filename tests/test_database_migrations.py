from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlmodel import SQLModel

from app.database_migrations import (
    BASELINE_REVISION,
    BUSINESS_TABLES,
    DatabaseMigrationError,
    _schema_signature,
)
from app.db import configure_database
from app.models import Account


def _current_revision(path: Path) -> str | None:
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    try:
        with engine.connect() as connection:
            return MigrationContext.configure(connection).get_current_revision()
    finally:
        engine.dispose()


def _create_unversioned_baseline(path: Path) -> None:
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    SQLModel.metadata.create_all(engine)
    engine.dispose()


def _upgrade_to_baseline_revision(path: Path) -> None:
    """创建仅停留在 001 的数据库，用于验证后续升级。"""
    config = Config()
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{path.as_posix()}")
    command.upgrade(config, BASELINE_REVISION)


def _make_accounts_table_match_legacy_column_addition(path: Path) -> None:
    """把账号表改造成旧 _ensure_columns 添加倍率后的真实结构。"""
    with sqlite3.connect(path) as connection:
        connection.execute("ALTER TABLE accounts RENAME TO accounts_current")
        connection.execute(
            """
            CREATE TABLE accounts (
                id VARCHAR NOT NULL PRIMARY KEY,
                name VARCHAR NOT NULL,
                type VARCHAR NOT NULL,
                base_url VARCHAR NOT NULL,
                api_key_encrypted VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                priority INTEGER NOT NULL,
                supported_models VARCHAR,
                tags VARCHAR,
                notes VARCHAR,
                last_error_code VARCHAR,
                last_error_message VARCHAR,
                last_successful_test_model VARCHAR,
                last_used_at VARCHAR,
                total_requests INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                created_at VARCHAR NOT NULL,
                updated_at VARCHAR NOT NULL,
                multiplier NUMERIC(4, 2) NOT NULL DEFAULT 0.10,
                CONSTRAINT ck_accounts_type CHECK (type IN ('openai', 'anthropic')),
                CONSTRAINT ck_accounts_status CHECK (status IN ('active', 'disabled')),
                CONSTRAINT ck_accounts_priority CHECK (priority BETWEEN 0 AND 9)
            )
            """
        )
        columns = [
            column.name
            for column in Account.__table__.columns
            if column.name != "test_default_model"
        ]
        quoted = ", ".join(columns)
        connection.execute(
            f"INSERT INTO accounts ({quoted}) SELECT {quoted} FROM accounts_current"
        )
        connection.execute("DROP TABLE accounts_current")
        connection.execute(
            "CREATE INDEX idx_accounts_dispatch ON accounts (status, priority, id)"
        )
        for column in ("priority", "status", "type"):
            connection.execute(f"CREATE INDEX ix_accounts_{column} ON accounts ({column})")


def test_empty_database_upgrades_to_current_baseline(tmp_path: Path) -> None:
    """全新数据库应由 Alembic 创建完整当前结构。"""
    path = tmp_path / "new.sqlite3"

    engine = configure_database(path)

    assert _current_revision(path) == "002_add_account_test_default_model"
    assert {"accounts", "models", "usage_records", "monitor_records"} <= set(
        inspect(engine).get_table_names()
    )


def test_alembic_head_schema_matches_sqlmodel_metadata(tmp_path: Path) -> None:
    """Alembic head 必须与当前 SQLModel 表、列、约束和索引保持一致。"""
    path = tmp_path / "head.sqlite3"
    migrated_engine = configure_database(path)
    metadata_engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(metadata_engine)
    try:
        for table in BUSINESS_TABLES:
            assert _schema_signature(migrated_engine, table) == _schema_signature(
                metadata_engine, table
            )
    finally:
        metadata_engine.dispose()


def test_unversioned_current_database_is_backed_up_and_stamped(tmp_path: Path) -> None:
    """当前形态无版本库应保留业务数据并创建一致性备份。"""
    path = tmp_path / "current.sqlite3"
    _create_unversioned_baseline(path)
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(
            Account.__table__.insert().values(
                id="account",
                name="账号",
                base_url="https://example.com",
                api_key_encrypted="plain-key",
            )
        )
    engine.dispose()

    configure_database(path)

    assert _current_revision(path) == "002_add_account_test_default_model"
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            "SELECT api_key_encrypted FROM accounts WHERE id = 'account'"
        ).fetchone() == ("plain-key",)
    backups = list(tmp_path.glob("current.sqlite3.migration-*-unversioned.bak"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)


def test_known_legacy_column_addition_is_normalized_before_stamp(tmp_path: Path) -> None:
    """唯一已知的旧补列结构应在备份后重建为精确 001，且数据不丢失。"""
    path = tmp_path / "legacy-current.sqlite3"
    _create_unversioned_baseline(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO accounts "
            "(id, name, type, base_url, api_key_encrypted, status, priority, multiplier, "
            "total_requests, total_tokens, created_at, updated_at) "
            "VALUES ('account', '账号', 'openai', 'https://example.com', 'plain-key', "
            "'active', 5, 0.10, 0, 0, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
        )
    _make_accounts_table_match_legacy_column_addition(path)

    migrated_engine = configure_database(path)

    expected_engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(expected_engine)
    try:
        assert _schema_signature(migrated_engine, "accounts") == _schema_signature(
            expected_engine, "accounts"
        )
    finally:
        expected_engine.dispose()
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            "SELECT api_key_encrypted, multiplier FROM accounts WHERE id = 'account'"
        ).fetchone() == ("plain-key", 0.1)
    assert _current_revision(path) == "002_add_account_test_default_model"
    assert len(list(tmp_path.glob("legacy-current.sqlite3.migration-*-unversioned.bak"))) == 1


def test_repeated_start_at_head_does_not_create_backup(tmp_path: Path) -> None:
    """已在 head 的正常启动不能反复备份或改写 revision。"""
    path = tmp_path / "repeat.sqlite3"
    configure_database(path)

    configure_database(path)

    assert _current_revision(path) == "002_add_account_test_default_model"


def test_database_at_001_upgrades_and_preserves_accounts(tmp_path: Path) -> None:
    """已发布的 001 数据库升级到 002 后保留账号并补空字段。"""
    path = tmp_path / "baseline.sqlite3"
    _upgrade_to_baseline_revision(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO accounts "
            "(id, name, type, base_url, api_key_encrypted, status, priority, multiplier, "
            "total_requests, total_tokens, created_at, updated_at) "
            "VALUES ('account', '账号', 'openai', 'https://example.com', 'plain-key', "
            "'active', 5, 0.10, 0, 0, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
        )

    configure_database(path)

    assert _current_revision(path) == "002_add_account_test_default_model"
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            "SELECT api_key_encrypted, test_default_model FROM accounts WHERE id = 'account'"
        ).fetchone() == ("plain-key", None)
    assert list(tmp_path.glob("repeat.sqlite3.migration-*.bak")) == []


def test_incomplete_unversioned_database_is_rejected_without_stamp(tmp_path: Path) -> None:
    """缺列旧库必须明确拒绝，不能再通过临时 DDL 猜测修复。"""
    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE accounts (id TEXT PRIMARY KEY NOT NULL)")

    with pytest.raises(DatabaseMigrationError, match="不符合当前基线"):
        configure_database(path)

    assert _current_revision(path) is None
    with sqlite3.connect(path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(accounts)")}
    assert columns == {"id"}


def test_unversioned_database_with_blob_key_is_rejected(tmp_path: Path) -> None:
    """当前结构中的旧 BLOB 密钥也不能被错误 stamp。"""
    path = tmp_path / "blob.sqlite3"
    _create_unversioned_baseline(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO accounts "
            "(id, name, type, base_url, api_key_encrypted, status, priority, multiplier, "
            "total_requests, total_tokens, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "account", "账号", "openai", "https://example.com", sqlite3.Binary(b"old"),
                "active", 5, 0.1, 0, 0, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z",
            ),
        )

    with pytest.raises(DatabaseMigrationError, match="非 TEXT 密钥"):
        configure_database(path)

    assert _current_revision(path) is None


def test_unknown_revision_is_rejected(tmp_path: Path) -> None:
    """不属于当前迁移图的数据库 revision 必须拒绝启动。"""
    path = tmp_path / "future.sqlite3"
    configure_database(path)
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE alembic_version SET version_num = '999_future'")

    with pytest.raises(DatabaseMigrationError, match="不属于当前应用"):
        configure_database(path)

    assert _current_revision(path) == "999_future"
