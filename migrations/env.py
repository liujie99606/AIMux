from __future__ import annotations

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.models import Account, CatalogModel, MonitorRecord, UsageRecord  # noqa: F401
from sqlmodel import SQLModel

config = context.config
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """以 SQL 输出模式运行迁移。"""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """连接目标数据库并运行迁移。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
