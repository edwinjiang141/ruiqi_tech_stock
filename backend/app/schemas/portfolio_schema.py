from pydantic import BaseModel, Field


class PortfolioRunRequest(BaseModel):
    """模拟组合生成请求。score_date 为已有评分推荐日期，start/end 为每日收益观察区间。"""

    score_date: str = Field(..., description="因子评分与推荐日期，格式 YYYYMMDD 或 YYYY-MM-DD")
    end_date: str = Field(..., description="组合收益观察结束日期，格式 YYYYMMDD 或 YYYY-MM-DD")
    stock_count: int = Field(default=20, ge=1, le=100, description="组合股票数")
    initial_cash: float = Field(default=100_000, gt=0, description="模拟资金规模")
    min_score: float = Field(default=65, ge=0, le=100, description="最低综合分")
    benchmark_code: str = Field(default="399006.SZ", description="基准指数代码，缺少指数行情时回退股票池等权")


class PortfolioHolding(BaseModel):
    ts_code: str
    name: str = ""
    industry: str = ""
    market: str = ""
    score: float
    recommendation_level: str = ""
    weight: float
    quantity: float
    buy_price: float
    current_price: float
    market_value: float
    return_rate: float
    reason: str


class PortfolioNavPoint(BaseModel):
    trade_date: str
    portfolio_value: float
    portfolio_return: float
    benchmark_return: float
    excess_return: float


class PortfolioResult(BaseModel):
    portfolio_id: str
    name: str
    score_date: str
    start_date: str
    end_date: str
    stock_count: int
    initial_cash: float
    min_score: float
    benchmark_code: str
    benchmark_name: str
    benchmark_source: str
    final_value: float
    cumulative_return: float
    benchmark_return: float
    excess_return: float
    max_drawdown: float
    conclusion: str
    holdings: list[PortfolioHolding]
    nav: list[PortfolioNavPoint]


class PortfolioSummary(BaseModel):
    portfolio_id: str
    name: str
    score_date: str
    start_date: str
    end_date: str
    stock_count: int
    initial_cash: float
    final_value: float
    cumulative_return: float
    benchmark_return: float
    excess_return: float
    max_drawdown: float
    benchmark_name: str
    benchmark_source: str
    conclusion: str
    created_at: str
