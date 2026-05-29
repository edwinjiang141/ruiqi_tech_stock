"""初始化 V1.2 独立 schema 和核心表

Revision ID: 202605240001
Revises:
Create Date: 2026-05-24 00:01:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "202605240001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "stock_research_v12"


def upgrade() -> None:
    op.execute(sa.text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))

    op.create_table(
        "dwd_stock_basic",
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("area", sa.String(length=50), nullable=True),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("market", sa.String(length=50), nullable=True),
        sa.Column("exchange", sa.String(length=20), nullable=True),
        sa.Column("list_status", sa.String(length=10), nullable=True),
        sa.Column("list_date", sa.Date(), nullable=True),
        sa.Column("delist_date", sa.Date(), nullable=True),
        sa.Column("is_hs", sa.String(length=10), nullable=True),
        sa.Column("is_gem", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_star", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_tech_industry", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("ts_code", name="pk_dwd_stock_basic"),
        schema=SCHEMA,
    )
    op.create_table(
        "dwd_stock_daily",
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("open_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("high_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("low_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("close_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("pre_close", sa.Numeric(18, 4), nullable=True),
        sa.Column("change_amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("pct_chg", sa.Numeric(18, 6), nullable=True),
        sa.Column("volume", sa.Numeric(20, 4), nullable=True),
        sa.Column("amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("ts_code", "trade_date", name="pk_dwd_stock_daily"),
        schema=SCHEMA,
    )
    op.create_table(
        "dwd_stock_adj_factor",
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("adj_factor", sa.Numeric(18, 8), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("ts_code", "trade_date", name="pk_dwd_stock_adj_factor"),
        schema=SCHEMA,
    )
    op.create_table(
        "dwd_stock_daily_basic",
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("close_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("turnover_rate", sa.Numeric(18, 6), nullable=True),
        sa.Column("turnover_rate_f", sa.Numeric(18, 6), nullable=True),
        sa.Column("volume_ratio", sa.Numeric(18, 6), nullable=True),
        sa.Column("pe", sa.Numeric(18, 6), nullable=True),
        sa.Column("pe_ttm", sa.Numeric(18, 6), nullable=True),
        sa.Column("pb", sa.Numeric(18, 6), nullable=True),
        sa.Column("ps", sa.Numeric(18, 6), nullable=True),
        sa.Column("ps_ttm", sa.Numeric(18, 6), nullable=True),
        sa.Column("total_share", sa.Numeric(20, 4), nullable=True),
        sa.Column("float_share", sa.Numeric(20, 4), nullable=True),
        sa.Column("free_share", sa.Numeric(20, 4), nullable=True),
        sa.Column("total_mv", sa.Numeric(20, 4), nullable=True),
        sa.Column("circ_mv", sa.Numeric(20, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("ts_code", "trade_date", name="pk_dwd_stock_daily_basic"),
        schema=SCHEMA,
    )
    op.create_table(
        "dwd_stock_financial_indicator",
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("ann_date", sa.Date(), nullable=True),
        sa.Column("roe", sa.Numeric(18, 6), nullable=True),
        sa.Column("roa", sa.Numeric(18, 6), nullable=True),
        sa.Column("grossprofit_margin", sa.Numeric(18, 6), nullable=True),
        sa.Column("netprofit_margin", sa.Numeric(18, 6), nullable=True),
        sa.Column("revenue_yoy", sa.Numeric(18, 6), nullable=True),
        sa.Column("netprofit_yoy", sa.Numeric(18, 6), nullable=True),
        sa.Column("debt_to_assets", sa.Numeric(18, 6), nullable=True),
        sa.Column("current_ratio", sa.Numeric(18, 6), nullable=True),
        sa.Column("quick_ratio", sa.Numeric(18, 6), nullable=True),
        sa.Column("ocf_to_profit", sa.Numeric(18, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("ts_code", "end_date", name="pk_dwd_stock_financial_indicator"),
        schema=SCHEMA,
    )
    op.create_table(
        "dwd_stock_cashflow",
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("ann_date", sa.Date(), nullable=True),
        sa.Column("net_profit", sa.Numeric(20, 4), nullable=True),
        sa.Column("n_cashflow_act", sa.Numeric(20, 4), nullable=True),
        sa.Column("c_fr_sale_sg", sa.Numeric(20, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("ts_code", "end_date", name="pk_dwd_stock_cashflow"),
        schema=SCHEMA,
    )
    op.create_table(
        "dwd_stock_moneyflow",
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("buy_sm_amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("sell_sm_amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("buy_md_amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("sell_md_amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("buy_lg_amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("sell_lg_amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("buy_elg_amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("sell_elg_amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("net_mf_amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("ts_code", "trade_date", name="pk_dwd_stock_moneyflow"),
        schema=SCHEMA,
    )
    op.create_table(
        "dm_stock_factor_score",
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("quality_score", sa.Numeric(10, 4), nullable=True),
        sa.Column("growth_score", sa.Numeric(10, 4), nullable=True),
        sa.Column("valuation_score", sa.Numeric(10, 4), nullable=True),
        sa.Column("momentum_score", sa.Numeric(10, 4), nullable=True),
        sa.Column("capital_flow_score", sa.Numeric(10, 4), nullable=True),
        sa.Column("leadership_score", sa.Numeric(10, 4), nullable=True),
        sa.Column("risk_penalty", sa.Numeric(10, 4), nullable=True),
        sa.Column("final_score", sa.Numeric(10, 4), nullable=True),
        sa.Column("rank_in_universe", sa.Integer(), nullable=True),
        sa.Column("rank_in_industry", sa.Integer(), nullable=True),
        sa.Column("recommendation_level", sa.String(length=10), nullable=True),
        sa.Column("formula_version", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("ts_code", "trade_date", name="pk_dm_stock_factor_score"),
        schema=SCHEMA,
    )
    op.create_table(
        "dm_stock_recommendation",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("recommendation_level", sa.String(length=10), nullable=False),
        sa.Column("final_score", sa.Numeric(10, 4), nullable=True),
        sa.Column("recommendation_reason", sa.Text(), nullable=True),
        sa.Column("risk_warning", sa.Text(), nullable=True),
        sa.Column("formula_version", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_dm_stock_recommendation"),
        schema=SCHEMA,
    )
    op.create_table(
        "dm_simulation_position",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("strategy_version", sa.String(length=50), nullable=False),
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 4), nullable=True),
        sa.Column("cost_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("market_value", sa.Numeric(20, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_dm_simulation_position"),
        schema=SCHEMA,
    )
    op.create_table(
        "dm_simulation_trade",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("strategy_version", sa.String(length=50), nullable=False),
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("side", sa.String(length=10), nullable=False),
        sa.Column("price", sa.Numeric(18, 4), nullable=True),
        sa.Column("quantity", sa.Numeric(20, 4), nullable=True),
        sa.Column("amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_dm_simulation_trade"),
        schema=SCHEMA,
    )
    op.create_table(
        "sys_task_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_name", sa.String(length=100), nullable=False),
        sa.Column("task_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_sys_task_log"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    # 阶段 2 暂不提供自动删除表逻辑，避免误删数据库中已有数据。
    pass
