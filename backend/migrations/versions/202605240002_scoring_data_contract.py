"""新增阶段5评分前置数据表

Revision ID: 202605240002
Revises: 202605240001
Create Date: 2026-05-24 21:30:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "202605240002"
down_revision: str | None = "202605240001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "stock_research_v12"


def upgrade() -> None:
    op.create_table(
        "dwd_stock_income",
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("ann_date", sa.Date(), nullable=True),
        sa.Column("f_ann_date", sa.Date(), nullable=True),
        sa.Column("report_type", sa.String(length=10), nullable=True),
        sa.Column("comp_type", sa.String(length=10), nullable=True),
        sa.Column("total_revenue", sa.Numeric(20, 4), nullable=True),
        sa.Column("revenue", sa.Numeric(20, 4), nullable=True),
        sa.Column("operate_profit", sa.Numeric(20, 4), nullable=True),
        sa.Column("total_profit", sa.Numeric(20, 4), nullable=True),
        sa.Column("n_income", sa.Numeric(20, 4), nullable=True),
        sa.Column("n_income_attr_p", sa.Numeric(20, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("ts_code", "end_date", name="pk_dwd_stock_income"),
        schema=SCHEMA,
    )
    op.create_table(
        "dwd_stock_balancesheet",
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("ann_date", sa.Date(), nullable=True),
        sa.Column("f_ann_date", sa.Date(), nullable=True),
        sa.Column("report_type", sa.String(length=10), nullable=True),
        sa.Column("comp_type", sa.String(length=10), nullable=True),
        sa.Column("total_assets", sa.Numeric(20, 4), nullable=True),
        sa.Column("total_liab", sa.Numeric(20, 4), nullable=True),
        sa.Column("total_hldr_eqy_exc_min_int", sa.Numeric(20, 4), nullable=True),
        sa.Column("total_hldr_eqy_inc_min_int", sa.Numeric(20, 4), nullable=True),
        sa.Column("goodwill", sa.Numeric(20, 4), nullable=True),
        sa.Column("total_cur_assets", sa.Numeric(20, 4), nullable=True),
        sa.Column("total_cur_liab", sa.Numeric(20, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("ts_code", "end_date", name="pk_dwd_stock_balancesheet"),
        schema=SCHEMA,
    )
    op.create_table(
        "dwd_index_weight",
        sa.Column("index_code", sa.String(length=20), nullable=False),
        sa.Column("con_code", sa.String(length=20), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("weight", sa.Numeric(18, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("index_code", "con_code", "trade_date", name="pk_dwd_index_weight"),
        schema=SCHEMA,
    )
    op.create_table(
        "dwd_stock_pledge_stat",
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("pledge_count", sa.Integer(), nullable=True),
        sa.Column("unrest_pledge", sa.Numeric(20, 4), nullable=True),
        sa.Column("rest_pledge", sa.Numeric(20, 4), nullable=True),
        sa.Column("total_share", sa.Numeric(20, 4), nullable=True),
        sa.Column("pledge_ratio", sa.Numeric(18, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("ts_code", "end_date", name="pk_dwd_stock_pledge_stat"),
        schema=SCHEMA,
    )
    op.create_table(
        "dwd_trade_calendar",
        sa.Column("exchange", sa.String(length=20), nullable=False),
        sa.Column("cal_date", sa.Date(), nullable=False),
        sa.Column("is_open", sa.Boolean(), nullable=False),
        sa.Column("pretrade_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("exchange", "cal_date", name="pk_dwd_trade_calendar"),
        schema=SCHEMA,
    )
    op.create_table(
        "dwd_stock_limit",
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("pre_close", sa.Numeric(18, 4), nullable=True),
        sa.Column("up_limit", sa.Numeric(18, 4), nullable=True),
        sa.Column("down_limit", sa.Numeric(18, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("ts_code", "trade_date", name="pk_dwd_stock_limit"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    # 不提供自动删除逻辑，避免误删已采集的生产数据。
    pass
