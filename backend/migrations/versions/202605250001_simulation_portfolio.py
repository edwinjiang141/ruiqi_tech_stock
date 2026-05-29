"""新增模拟组合持久化表

Revision ID: 202605250001
Revises: 202605240005
Create Date: 2026-05-25 20:30:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "202605250001"
down_revision: str | None = "202605240005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "stock_research_v12"


def upgrade() -> None:
    op.create_table(
        "dwd_index_daily",
        sa.Column("index_code", sa.String(length=20), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("close_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("pct_chg", sa.Numeric(18, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("index_code", "trade_date"),
        schema=SCHEMA,
    )
    op.create_table(
        "dm_simulation_portfolio",
        sa.Column("portfolio_id", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("score_date", sa.Date(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("stock_count", sa.Integer(), nullable=False),
        sa.Column("initial_cash", sa.Numeric(20, 4), nullable=True),
        sa.Column("min_score", sa.Numeric(10, 4), nullable=True),
        sa.Column("benchmark_code", sa.String(length=20), nullable=True),
        sa.Column("benchmark_name", sa.String(length=80), nullable=True),
        sa.Column("benchmark_source", sa.String(length=30), nullable=True),
        sa.Column("final_value", sa.Numeric(20, 4), nullable=True),
        sa.Column("cumulative_return", sa.Numeric(18, 6), nullable=True),
        sa.Column("benchmark_return", sa.Numeric(18, 6), nullable=True),
        sa.Column("excess_return", sa.Numeric(18, 6), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(18, 6), nullable=True),
        sa.Column("conclusion", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("portfolio_id"),
        schema=SCHEMA,
    )
    op.create_table(
        "dm_simulation_portfolio_holding",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("portfolio_id", sa.String(length=120), nullable=False),
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("market", sa.String(length=50), nullable=True),
        sa.Column("score", sa.Numeric(10, 4), nullable=True),
        sa.Column("recommendation_level", sa.String(length=10), nullable=True),
        sa.Column("weight", sa.Numeric(18, 8), nullable=True),
        sa.Column("quantity", sa.Numeric(20, 4), nullable=True),
        sa.Column("buy_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("current_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("market_value", sa.Numeric(20, 4), nullable=True),
        sa.Column("return_rate", sa.Numeric(18, 6), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index("ix_dm_simulation_portfolio_holding_portfolio_id", "dm_simulation_portfolio_holding", ["portfolio_id"], schema=SCHEMA)
    op.create_table(
        "dm_simulation_portfolio_nav",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("portfolio_id", sa.String(length=120), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("portfolio_value", sa.Numeric(20, 4), nullable=True),
        sa.Column("portfolio_return", sa.Numeric(18, 6), nullable=True),
        sa.Column("benchmark_return", sa.Numeric(18, 6), nullable=True),
        sa.Column("excess_return", sa.Numeric(18, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index("ix_dm_simulation_portfolio_nav_portfolio_id", "dm_simulation_portfolio_nav", ["portfolio_id"], schema=SCHEMA)


def downgrade() -> None:
    # 组合收益记录属于业务结果，不在自动降级中删除，避免误删历史组合。
    pass
