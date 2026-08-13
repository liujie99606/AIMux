from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "002_add_account_test_default_model"
down_revision = "001_current_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """为账号新增可选的测试默认模型。"""
    op.add_column("accounts", sa.Column("test_default_model", sa.String(), nullable=True))


def downgrade() -> None:
    """AIMux 不支持自动降级用户数据库。"""
    raise RuntimeError("AIMux 不支持数据库自动降级")
