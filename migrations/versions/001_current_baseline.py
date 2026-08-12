from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "001_current_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建 AIMux 引入 Alembic 时的完整当前结构。"""
    op.create_table(
        "accounts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("base_url", sa.String(), nullable=False),
        sa.Column("api_key_encrypted", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("multiplier", sa.Numeric(4, 2), nullable=False),
        sa.Column("supported_models", sa.String(), nullable=True),
        sa.Column("tags", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("last_error_code", sa.String(), nullable=True),
        sa.Column("last_error_message", sa.String(), nullable=True),
        sa.Column("last_successful_test_model", sa.String(), nullable=True),
        sa.Column("last_used_at", sa.String(), nullable=True),
        sa.Column("total_requests", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.CheckConstraint("type IN ('openai', 'anthropic')", name="ck_accounts_type"),
        sa.CheckConstraint("status IN ('active', 'disabled')", name="ck_accounts_status"),
        sa.CheckConstraint("priority BETWEEN 0 AND 9", name="ck_accounts_priority"),
        sa.CheckConstraint(
            "multiplier BETWEEN 0.01 AND 0.30", name="ck_accounts_multiplier"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_accounts_dispatch", "accounts", ["status", "priority", "id"])
    for column in ("priority", "status", "type"):
        op.create_index(f"ix_accounts_{column}", "accounts", [column])

    op.create_table(
        "models",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("is_default", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.CheckConstraint("type IN ('openai', 'anthropic')", name="ck_models_type"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("type", "name", name="uq_models_type_name"),
    )
    op.create_index("idx_models_type_name", "models", ["type", "name"])
    op.create_index("ix_models_name", "models", ["name"])
    op.create_index("ix_models_type", "models", ["type"])

    op.create_table(
        "usage_records",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("trace_id", sa.String(), nullable=False),
        sa.Column("started_at", sa.String(), nullable=False),
        sa.Column("ended_at", sa.String(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("first_token_ms", sa.Integer(), nullable=True),
        sa.Column("account_id", sa.String(), nullable=True),
        sa.Column("account_name", sa.String(), nullable=True),
        sa.Column("account_type", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("reasoning_effort", sa.String(), nullable=True),
        sa.Column("endpoint", sa.String(), nullable=True),
        sa.Column("stream", sa.Boolean(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("cached_tokens", sa.Integer(), nullable=True),
        sa.Column("client_ip", sa.String(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_usage_started", "usage_records", ["started_at", "id"])
    op.create_index("idx_usage_account", "usage_records", ["account_id", "started_at"])
    op.create_index("idx_usage_model", "usage_records", ["model", "started_at"])
    for column in ("account_id", "model", "started_at", "trace_id"):
        op.create_index(f"ix_usage_records_{column}", "usage_records", [column])

    op.create_table(
        "monitor_records",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("account_name", sa.String(), nullable=False),
        sa.Column("account_type", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("checked_at", sa.String(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_monitor_account_checked", "monitor_records", ["account_id", "checked_at"]
    )
    op.create_index("idx_monitor_checked", "monitor_records", ["checked_at", "id"])
    op.create_index("ix_monitor_records_account_id", "monitor_records", ["account_id"])
    op.create_index("ix_monitor_records_checked_at", "monitor_records", ["checked_at"])


def downgrade() -> None:
    """AIMux 不支持自动降级用户数据库。"""
    raise RuntimeError("AIMux 不支持数据库自动降级")
