"""新增模拟交易复盘结果表

Revision ID: 202605240003
Revises: 202605240002
Create Date: 2026-05-25 12:20:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "202605240003"
down_revision: str | None = "202605240002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "stock_research_v12"


def upgrade() -> None:
    op.create_table(
        "dm_simulation_review",
        sa.Column("strategy_version", sa.String(length=100), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("stock_count", sa.Integer(), nullable=False),
        sa.Column("initial_cash", sa.Numeric(20, 4), nullable=True),
        sa.Column("final_value", sa.Numeric(20, 4), nullable=True),
        sa.Column("cumulative_return", sa.Numeric(18, 6), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(18, 6), nullable=True),
        sa.Column("win_rate", sa.Numeric(18, 6), nullable=True),
        sa.Column("metrics_json", sa.Text(), nullable=True),
        sa.Column("holdings_json", sa.Text(), nullable=True),
        sa.Column("conclusion", sa.Text(), nullable=True),
        sa.Column("time_requirement", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("strategy_version", name="pk_dm_simulation_review"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    # 不提供自动删除逻辑，避免误删历史复盘结果。
    pass
