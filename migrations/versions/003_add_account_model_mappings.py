from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "003_add_account_model_mappings"
down_revision = "002_add_account_test_default_model"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """为账号增加可选的客户端到上游模型映射 JSON。"""
    op.add_column("accounts", sa.Column("model_mappings", sa.String(), nullable=True))


def downgrade() -> None:
    """AIMux 不支持自动降级用户数据库。"""
    raise RuntimeError("AIMux 不支持数据库自动降级")
