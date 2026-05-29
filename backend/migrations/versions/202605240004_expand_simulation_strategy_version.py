"""扩展模拟复盘编号字段长度

Revision ID: 202605240004
Revises: 202605240003
Create Date: 2026-05-25 12:48:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "202605240004"
down_revision: str | None = "202605240003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "stock_research_v12"


def upgrade() -> None:
    op.alter_column("dm_simulation_position", "strategy_version", existing_type=sa.String(length=50), type_=sa.String(length=100), schema=SCHEMA)
    op.alter_column("dm_simulation_trade", "strategy_version", existing_type=sa.String(length=50), type_=sa.String(length=100), schema=SCHEMA)


def downgrade() -> None:
    # 不自动缩短字段，避免历史复盘编号被截断。
    pass
