"""保存模拟复盘调仓过程

Revision ID: 202605240005
Revises: 202605240004
Create Date: 2026-05-25 15:30:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "202605240005"
down_revision: str | None = "202605240004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "stock_research_v12"


def upgrade() -> None:
    op.add_column("dm_simulation_review", sa.Column("rebalances_json", sa.Text(), nullable=True), schema=SCHEMA)


def downgrade() -> None:
    # 不自动删除列，避免误删已保存的调仓过程明细。
    pass
