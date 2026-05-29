from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.config import get_settings
from app.models.base import Base


SCHEMA = get_settings().database_schema


class StockBasic(Base):
    """股票基础信息表，用于构建创业板、科创板、科技属性股票池。"""

    __tablename__ = "dwd_stock_basic"
    __table_args__ = {"schema": SCHEMA}

    ts_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    symbol: Mapped[str | None] = mapped_column(String(20))
    name: Mapped[str | None] = mapped_column(String(100))
    area: Mapped[str | None] = mapped_column(String(50))
    industry: Mapped[str | None] = mapped_column(String(100))
    market: Mapped[str | None] = mapped_column(String(50))
    exchange: Mapped[str | None] = mapped_column(String(20))
    list_status: Mapped[str | None] = mapped_column(String(10))
    list_date: Mapped[date | None] = mapped_column(Date)
    delist_date: Mapped[date | None] = mapped_column(Date)
    is_hs: Mapped[str | None] = mapped_column(String(10))
    is_gem: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_star: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_tech_industry: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StockDaily(Base):
    __tablename__ = "dwd_stock_daily"
    __table_args__ = {"schema": SCHEMA}

    ts_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    open_price: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    high_price: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    low_price: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    close_price: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    pre_close: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    change_amount: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    pct_chg: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    volume: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    amount: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StockAdjFactor(Base):
    __tablename__ = "dwd_stock_adj_factor"
    __table_args__ = {"schema": SCHEMA}

    ts_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    adj_factor: Mapped[Numeric | None] = mapped_column(Numeric(18, 8))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StockDailyBasic(Base):
    __tablename__ = "dwd_stock_daily_basic"
    __table_args__ = {"schema": SCHEMA}

    ts_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    close_price: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    turnover_rate: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    turnover_rate_f: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    volume_ratio: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    pe: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    pe_ttm: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    pb: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    ps: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    ps_ttm: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    total_share: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    float_share: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    free_share: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    total_mv: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    circ_mv: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StockFinancialIndicator(Base):
    __tablename__ = "dwd_stock_financial_indicator"
    __table_args__ = {"schema": SCHEMA}

    ts_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    end_date: Mapped[date] = mapped_column(Date, primary_key=True)
    ann_date: Mapped[date | None] = mapped_column(Date)
    roe: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    roa: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    grossprofit_margin: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    netprofit_margin: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    revenue_yoy: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    netprofit_yoy: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    debt_to_assets: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    current_ratio: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    quick_ratio: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    ocf_to_profit: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StockCashflow(Base):
    __tablename__ = "dwd_stock_cashflow"
    __table_args__ = {"schema": SCHEMA}

    ts_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    end_date: Mapped[date] = mapped_column(Date, primary_key=True)
    ann_date: Mapped[date | None] = mapped_column(Date)
    net_profit: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    n_cashflow_act: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    c_fr_sale_sg: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StockMoneyflow(Base):
    __tablename__ = "dwd_stock_moneyflow"
    __table_args__ = {"schema": SCHEMA}

    ts_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    buy_sm_amount: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    sell_sm_amount: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    buy_md_amount: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    sell_md_amount: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    buy_lg_amount: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    sell_lg_amount: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    buy_elg_amount: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    sell_elg_amount: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    net_mf_amount: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StockIncome(Base):
    """利润表关键字段，用于成长性、营收排名和 CAGR 计算。"""

    __tablename__ = "dwd_stock_income"
    __table_args__ = {"schema": SCHEMA}

    ts_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    end_date: Mapped[date] = mapped_column(Date, primary_key=True)
    ann_date: Mapped[date | None] = mapped_column(Date)
    f_ann_date: Mapped[date | None] = mapped_column(Date)
    report_type: Mapped[str | None] = mapped_column(String(10))
    comp_type: Mapped[str | None] = mapped_column(String(10))
    total_revenue: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    revenue: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    operate_profit: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    total_profit: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    n_income: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    n_income_attr_p: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StockBalanceSheet(Base):
    """资产负债表关键字段，用于净资产、商誉和偿债风险计算。"""

    __tablename__ = "dwd_stock_balancesheet"
    __table_args__ = {"schema": SCHEMA}

    ts_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    end_date: Mapped[date] = mapped_column(Date, primary_key=True)
    ann_date: Mapped[date | None] = mapped_column(Date)
    f_ann_date: Mapped[date | None] = mapped_column(Date)
    report_type: Mapped[str | None] = mapped_column(String(10))
    comp_type: Mapped[str | None] = mapped_column(String(10))
    total_assets: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    total_liab: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    total_hldr_eqy_exc_min_int: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    total_hldr_eqy_inc_min_int: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    goodwill: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    total_cur_assets: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    total_cur_liab: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class IndexWeight(Base):
    """指数成分权重，用于龙头地位评分。"""

    __tablename__ = "dwd_index_weight"
    __table_args__ = {"schema": SCHEMA}

    index_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    con_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    weight: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StockPledgeStat(Base):
    """股权质押统计，用于质押风险扣分。"""

    __tablename__ = "dwd_stock_pledge_stat"
    __table_args__ = {"schema": SCHEMA}

    ts_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    end_date: Mapped[date] = mapped_column(Date, primary_key=True)
    pledge_count: Mapped[int | None] = mapped_column(Integer)
    unrest_pledge: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    rest_pledge: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    total_share: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    pledge_ratio: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TradeCalendar(Base):
    """交易日历，用于有效交易日窗口和上市天数判断。"""

    __tablename__ = "dwd_trade_calendar"
    __table_args__ = {"schema": SCHEMA}

    exchange: Mapped[str] = mapped_column(String(20), primary_key=True)
    cal_date: Mapped[date] = mapped_column(Date, primary_key=True)
    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False)
    pretrade_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StockLimit(Base):
    """每日涨跌停价格，用于模拟交易买卖可行性判断。"""

    __tablename__ = "dwd_stock_limit"
    __table_args__ = {"schema": SCHEMA}

    ts_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    pre_close: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    up_limit: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    down_limit: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StockFactorScore(Base):
    __tablename__ = "dm_stock_factor_score"
    __table_args__ = {"schema": SCHEMA}

    ts_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    quality_score: Mapped[Numeric | None] = mapped_column(Numeric(10, 4))
    growth_score: Mapped[Numeric | None] = mapped_column(Numeric(10, 4))
    valuation_score: Mapped[Numeric | None] = mapped_column(Numeric(10, 4))
    momentum_score: Mapped[Numeric | None] = mapped_column(Numeric(10, 4))
    capital_flow_score: Mapped[Numeric | None] = mapped_column(Numeric(10, 4))
    leadership_score: Mapped[Numeric | None] = mapped_column(Numeric(10, 4))
    risk_penalty: Mapped[Numeric | None] = mapped_column(Numeric(10, 4))
    final_score: Mapped[Numeric | None] = mapped_column(Numeric(10, 4))
    rank_in_universe: Mapped[int | None] = mapped_column(Integer)
    rank_in_industry: Mapped[int | None] = mapped_column(Integer)
    recommendation_level: Mapped[str | None] = mapped_column(String(10))
    formula_version: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StockRecommendation(Base):
    __tablename__ = "dm_stock_recommendation"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    recommendation_level: Mapped[str] = mapped_column(String(10), nullable=False)
    final_score: Mapped[Numeric | None] = mapped_column(Numeric(10, 4))
    recommendation_reason: Mapped[str | None] = mapped_column(Text)
    risk_warning: Mapped[str | None] = mapped_column(Text)
    formula_version: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SimulationPosition(Base):
    __tablename__ = "dm_simulation_position"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    cost_price: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    market_value: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SimulationTrade(Base):
    __tablename__ = "dm_simulation_trade"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    price: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    quantity: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    amount: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SimulationReview(Base):
    """模拟交易复盘结果表，用于保存历史复盘摘要和可回显明细。"""

    __tablename__ = "dm_simulation_review"
    __table_args__ = {"schema": SCHEMA}

    strategy_version: Mapped[str] = mapped_column(String(100), primary_key=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    stock_count: Mapped[int] = mapped_column(Integer, nullable=False)
    initial_cash: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    final_value: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    cumulative_return: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    max_drawdown: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    win_rate: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    metrics_json: Mapped[str | None] = mapped_column(Text)
    holdings_json: Mapped[str | None] = mapped_column(Text)
    rebalances_json: Mapped[str | None] = mapped_column(Text)
    conclusion: Mapped[str | None] = mapped_column(Text)
    time_requirement: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class IndexDaily(Base):
    """指数日线行情，用于模拟组合的大盘基准收益对比。"""

    __tablename__ = "dwd_index_daily"
    __table_args__ = {"schema": SCHEMA}

    index_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    close_price: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    pct_chg: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SimulationPortfolio(Base):
    """模拟组合摘要表，用于保存基于某一评分日推荐生成的组合。"""

    __tablename__ = "dm_simulation_portfolio"
    __table_args__ = {"schema": SCHEMA}

    portfolio_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    score_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    stock_count: Mapped[int] = mapped_column(Integer, nullable=False)
    initial_cash: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    min_score: Mapped[Numeric | None] = mapped_column(Numeric(10, 4))
    benchmark_code: Mapped[str | None] = mapped_column(String(20))
    benchmark_name: Mapped[str | None] = mapped_column(String(80))
    benchmark_source: Mapped[str | None] = mapped_column(String(30))
    final_value: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    cumulative_return: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    benchmark_return: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    excess_return: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    max_drawdown: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    conclusion: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SimulationPortfolioHolding(Base):
    """模拟组合初始持仓。"""

    __tablename__ = "dm_simulation_portfolio_holding"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[str] = mapped_column(String(120), nullable=False)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str | None] = mapped_column(String(100))
    industry: Mapped[str | None] = mapped_column(String(100))
    market: Mapped[str | None] = mapped_column(String(50))
    score: Mapped[Numeric | None] = mapped_column(Numeric(10, 4))
    recommendation_level: Mapped[str | None] = mapped_column(String(10))
    weight: Mapped[Numeric | None] = mapped_column(Numeric(18, 8))
    quantity: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    buy_price: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    current_price: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    market_value: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    return_rate: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SimulationPortfolioNav(Base):
    """模拟组合每日净值，用于收益曲线和基准对比。"""

    __tablename__ = "dm_simulation_portfolio_nav"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[str] = mapped_column(String(120), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    portfolio_value: Mapped[Numeric | None] = mapped_column(Numeric(20, 4))
    portfolio_return: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    benchmark_return: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    excess_return: Mapped[Numeric | None] = mapped_column(Numeric(18, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TaskLog(Base):
    __tablename__ = "sys_task_log"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_name: Mapped[str] = mapped_column(String(100), nullable=False)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
