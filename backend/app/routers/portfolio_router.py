from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ListResponse, PortfolioRunRequest, success_response
from app.services import PortfolioService

router = APIRouter(prefix="/api/portfolios", tags=["模拟组合"])


@router.get("")
def list_portfolios(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """查询历史模拟组合。"""

    items, total = PortfolioService(db).list_portfolios(limit=limit)
    return success_response(data=ListResponse(items=items, total=total).model_dump(), message="模拟组合列表查询成功")


@router.get("/{portfolio_id}")
def get_portfolio(portfolio_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    """查询单个模拟组合的持仓和每日净值。"""

    result = PortfolioService(db).get_portfolio(portfolio_id)
    return success_response(data=result.model_dump(), message="模拟组合详情查询成功")


@router.post("/run")
def run_portfolio(payload: PortfolioRunRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    """按评分日推荐生成模拟组合，并计算每日组合收益与基准收益。"""

    result = PortfolioService(db).run_portfolio(
        score_date=payload.score_date,
        end_date=payload.end_date,
        stock_count=payload.stock_count,
        initial_cash=payload.initial_cash,
        min_score=payload.min_score,
        benchmark_code=payload.benchmark_code,
    )
    return success_response(data=result.model_dump(), message="模拟组合生成成功")
