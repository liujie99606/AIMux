from __future__ import annotations

import logging
import re
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from filelock import FileLock, Timeout
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine

from app.models import Account, CatalogModel, MonitorRecord, UsageRecord  # noqa: F401
from app.utils.resources import resource_path

BASELINE_REVISION = "001_current_baseline"
BUSINESS_TABLES = frozenset({"accounts", "models", "usage_records", "monitor_records"})
BACKUP_LIMIT = 5
LOCK_TIMEOUT_SECONDS = 30
_logger = logging.getLogger(__name__)


class DatabaseMigrationError(RuntimeError):
    """数据库无法安全迁移时抛出的启动错误。"""


def _sqlite_url(path: Path) -> str:
    """生成适用于 Alembic 和 SQLAlchemy 的 SQLite URL。"""
    return f"sqlite:///{path.as_posix()}"


def _alembic_config(path: Path) -> Config:
    """构造不依赖工作目录和 alembic.ini 的运行时配置。"""
    migration_dir = resource_path("migrations")
    if not migration_dir.is_dir():
        raise DatabaseMigrationError(f"找不到数据库迁移资源：{migration_dir}")
    config = Config()
    config.set_main_option("script_location", str(migration_dir))
    config.set_main_option("sqlalchemy.url", _sqlite_url(path))
    return config


def _integrity_check(path: Path) -> None:
    """确认 SQLite 文件可读取且内部结构完整。"""
    try:
        with sqlite3.connect(path) as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.DatabaseError as exc:
        raise DatabaseMigrationError(f"数据库完整性检查失败：{exc}") from exc
    if result != ("ok",):
        detail = result[0] if result else "无检查结果"
        raise DatabaseMigrationError(f"数据库完整性检查失败：{detail}")


def _normalize_sql(value: str | None) -> str:
    """规整 SQLite 约束表达式中的无意义空白和引号差异。"""
    return re.sub(r"\s+", "", (value or "").lower().replace('"', ""))


def _schema_signature(engine: Engine, table: str) -> dict[str, Any]:
    """提取足以识别当前基线的表结构签名。"""
    inspector = inspect(engine)
    columns = tuple(
        (
            column["name"],
            str(column["type"]).upper(),
            bool(column["nullable"]),
            _normalize_sql(column.get("default")),
        )
        for column in inspector.get_columns(table)
    )
    primary_key = tuple(inspector.get_pk_constraint(table).get("constrained_columns") or ())
    unique_constraints = {
        tuple(item.get("column_names") or ()) for item in inspector.get_unique_constraints(table)
    }
    checks = {_normalize_sql(item.get("sqltext")) for item in inspector.get_check_constraints(table)}
    indexes = {
        (item["name"], tuple(item.get("column_names") or ()), bool(item.get("unique")))
        for item in inspector.get_indexes(table)
    }
    return {
        "columns": columns,
        "primary_key": primary_key,
        "unique_constraints": unique_constraints,
        "checks": checks,
        "indexes": indexes,
    }


def _baseline_schema_signatures() -> dict[str, dict[str, Any]]:
    """从不可变的 001 migration 生成无版本数据库的唯一合法结构签名。"""
    with tempfile.TemporaryDirectory(prefix="aimux-baseline-") as directory:
        baseline_path = Path(directory) / "baseline.sqlite3"
        command.upgrade(_alembic_config(baseline_path), BASELINE_REVISION)
        engine = create_engine(_sqlite_url(baseline_path))
        try:
            return {
                table: _schema_signature(engine, table)
                for table in sorted(BUSINESS_TABLES)
            }
        finally:
            engine.dispose()


def _validate_unversioned_baseline(path: Path) -> None:
    """严格验证无版本数据库是否精确符合不可变的 001 基线。"""
    _integrity_check(path)
    actual_engine = create_engine(_sqlite_url(path))
    try:
        actual_tables = set(inspect(actual_engine).get_table_names())
        unexpected = actual_tables - BUSINESS_TABLES
        missing = BUSINESS_TABLES - actual_tables
        if missing or unexpected:
            raise DatabaseMigrationError(
                "无版本数据库不符合当前基线："
                f"缺少表 {sorted(missing)}，额外表 {sorted(unexpected)}"
            )
        expected_signatures = _baseline_schema_signatures()
        for table in sorted(BUSINESS_TABLES):
            actual = _schema_signature(actual_engine, table)
            if actual != expected_signatures[table]:
                raise DatabaseMigrationError(
                    f"无版本数据库不符合当前基线：表 {table} 的列、约束或索引不一致"
                )
        with sqlite3.connect(path) as connection:
            invalid_key_count = connection.execute(
                "SELECT COUNT(*) FROM accounts "
                "WHERE api_key_encrypted IS NOT NULL "
                "AND api_key_encrypted != '' AND typeof(api_key_encrypted) != 'text'"
            ).fetchone()[0]
        if invalid_key_count:
            raise DatabaseMigrationError(
                "无版本数据库包含非 TEXT 密钥，不支持自动迁移旧加密 BLOB"
            )
        with sqlite3.connect(path) as connection:
            invalid_multiplier_count = connection.execute(
                "SELECT COUNT(*) FROM accounts WHERE multiplier < 0.01 OR multiplier > 0.30"
            ).fetchone()[0]
        if invalid_multiplier_count:
            raise DatabaseMigrationError("无版本数据库包含超出 0.01 至 0.30 的账号倍率")
    finally:
        actual_engine.dispose()


def _backup_database(path: Path, revision: str) -> Path:
    """使用 SQLite Backup API 创建并校验迁移前一致性备份。"""
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    backup = path.with_name(f"{path.name}.migration-{timestamp}-{revision}.bak")
    try:
        with sqlite3.connect(path) as source, sqlite3.connect(backup) as target:
            source.backup(target)
        _integrity_check(backup)
    except (OSError, sqlite3.DatabaseError, DatabaseMigrationError) as exc:
        backup.unlink(missing_ok=True)
        raise DatabaseMigrationError(f"无法创建迁移备份：{exc}") from exc
    backups = sorted(
        path.parent.glob(f"{path.name}.migration-*.bak"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for expired in backups[BACKUP_LIMIT:]:
        expired.unlink(missing_ok=True)
    return backup


def _current_revision(path: Path) -> str | None:
    """读取数据库当前 Alembic revision。"""
    engine = create_engine(_sqlite_url(path))
    try:
        with engine.connect() as connection:
            heads = MigrationContext.configure(connection).get_current_heads()
    finally:
        engine.dispose()
    if len(heads) > 1:
        raise DatabaseMigrationError(f"数据库包含不受支持的多个 revision：{heads}")
    return heads[0] if heads else None


def _validate_versioned_revision(config: Config, revision: str) -> str:
    """确认当前 revision 属于本应用的单线迁移图且不高于 head。"""
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    if len(heads) != 1:
        raise DatabaseMigrationError(f"应用迁移图必须只有一个 head，当前为：{heads}")
    head = heads[0]
    try:
        known = script.get_revision(revision)
    except Exception as exc:
        raise DatabaseMigrationError(f"数据库 revision 不属于当前应用：{revision}") from exc
    if known is None:
        raise DatabaseMigrationError(f"数据库 revision 不属于当前应用：{revision}")
    ancestors = {item.revision for item in script.walk_revisions("base", head)}
    if revision not in ancestors:
        raise DatabaseMigrationError(f"数据库 revision 高于或偏离当前应用 head：{revision}")
    return head


def _user_tables(path: Path) -> set[str]:
    """返回数据库中的非 SQLite 内部表。"""
    if not path.exists() or path.stat().st_size == 0:
        return set()
    with sqlite3.connect(path) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    return {name for (name,) in rows}


def migrate_database(path: Path) -> None:
    """在跨进程锁内识别数据库形态并安全升级至当前 head。"""
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(path.with_name(f"{path.name}.migrate.lock")), timeout=LOCK_TIMEOUT_SECONDS)
    try:
        with lock:
            config = _alembic_config(path)
            user_tables = _user_tables(path)
            current = _current_revision(path) if path.exists() and path.stat().st_size else None
            script = ScriptDirectory.from_config(config)
            head = script.get_current_head()
            _logger.info("数据库迁移检查：path=%s current=%s head=%s", path, current, head)
            if current is None and user_tables:
                _validate_unversioned_baseline(path)
                backup = _backup_database(path, "unversioned")
                _logger.info("已创建无版本数据库迁移备份：%s", backup)
                command.stamp(config, BASELINE_REVISION)
            elif current is not None:
                head = _validate_versioned_revision(config, current)
                if current != head:
                    backup = _backup_database(path, current)
                    _logger.info("已创建数据库迁移备份：%s", backup)
            command.upgrade(config, "head")
            _integrity_check(path)
            migrated_revision = _current_revision(path)
            if migrated_revision != head:
                raise DatabaseMigrationError(
                    f"数据库迁移后 revision 异常：{migrated_revision}，预期 {head}"
                )
    except Timeout as exc:
        raise DatabaseMigrationError(
            f"等待数据库迁移锁超时（{LOCK_TIMEOUT_SECONDS} 秒）：{path}"
        ) from exc
    except DatabaseMigrationError:
        raise
    except Exception as exc:
        raise DatabaseMigrationError(f"数据库迁移失败：{exc}") from exc
