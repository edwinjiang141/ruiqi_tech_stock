from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class StockRead(BaseModel):
    """股票基础信息响应结构。"""

    ts_code: str
    symbol: str | None
    name: str | None
    area: str | None
    industry: str | None
    market: str | None
    exchange: str | None
    list_status: str | None
    list_date: date | None
    delist_date: date | None
    is_hs: str | None
    is_gem: bool
    is_star: bool
    is_tech_industry: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
