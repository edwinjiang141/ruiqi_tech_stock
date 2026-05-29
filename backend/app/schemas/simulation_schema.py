from typing import Literal

from pydantic import BaseModel, Field


class SimulationRunRequest(BaseModel):
    """模拟交易请求。日期要求：start_date 为已有阶段5评分的信号日，end_date 后必须已有行情数据。"""

    start_date: str = Field(..., description="复盘开始信号日，格式 YYYYMMDD 或 YYYY-MM-DD")
    end_date: str = Field(..., description="复盘结束估值日，格式 YYYYMMDD 或 YYYY-MM-DD")
    stock_count: int = Field(default=20, ge=1, le=100, description="模拟持仓股票数，默认 20")
    initial_cash: float = Field(default=1_000_000, gt=0, description="模拟初始资金规模")
    min_score: float = Field(default=65, ge=0, le=100, description="最低综合评分，候选不足时可降低")
    review_mode: Literal["hold", "rebalance"] = Field(default="hold", description="复盘方式：hold 固定信号持有；rebalance 定期调仓")


class SimulationMetric(BaseModel):
    """复盘指标，界面可直接展示中文说明。"""

    name: str
    value: float | int | str
    description: str


class SimulationHolding(BaseModel):
    ts_code: str
    name: str = ""
    industry: str = ""
    market: str = ""
    buy_date: str = Field(default="", description="实际买入成交日期；初始建仓和后续调仓买入日期可能不同")
    weight: float
    allocated_cash: float
    buy_price: float
    end_price: float
    return_rate: float


class SimulationPositionSnapshot(BaseModel):
    """调仓前后的持仓快照，用于解释组合资产如何滚动。"""

    ts_code: str
    name: str = ""
    industry: str = ""
    market: str = ""
    buy_date: str
    quantity: float
    cost_price: float
    current_price: float
    market_value: float
    return_rate: float


class SimulationTradeDetail(BaseModel):
    """调仓交易明细。卖出记录包含已实现盈亏，买入记录盈亏为 0。"""

    ts_code: str
    name: str = ""
    industry: str = ""
    market: str = ""
    side: Literal["buy", "sell"]
    price: float
    quantity: float
    amount: float
    profit_loss: float = 0
    return_rate: float = 0
    reason: str


class SimulationRebalanceStep(BaseModel):
    """一次建仓或调仓过程。"""

    trade_date: str
    signal_date: str
    before_cash: float
    before_market_value: float
    before_total_value: float
    before_holdings: list[SimulationPositionSnapshot] = Field(default_factory=list)
    sell_trades: list[SimulationTradeDetail] = Field(default_factory=list)
    buy_trades: list[SimulationTradeDetail] = Field(default_factory=list)
    after_cash: float
    after_market_value: float
    after_total_value: float
    after_holdings: list[SimulationPositionSnapshot] = Field(default_factory=list)


class SimulationReviewResult(BaseModel):
    strategy_version: str
    start_date: str
    end_date: str
    stock_count: int
    initial_cash: float
    final_value: float
    metrics: list[SimulationMetric]
    holdings: list[SimulationHolding]
    rebalances: list[SimulationRebalanceStep] = Field(default_factory=list)
    conclusion: str
    time_requirement: str


class SimulationRunSummary(BaseModel):
    """历史复盘摘要，用于前端列表展示和点击回显。"""

    strategy_version: str
    start_date: str
    end_date: str
    stock_count: int
    initial_cash: float
    final_value: float
    cumulative_return: float
    max_drawdown: float
    win_rate: float
    conclusion: str
    created_at: str
