from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ListResponse, SimulationRunRequest, success_response
from app.services import SimulationService

router = APIRouter(prefix="/api/simulations", tags=["模拟复盘"])


@router.get("")
def list_simulations(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """查询最近模拟复盘运行记录。"""

    items, total = SimulationService(db).list_recent_runs(limit=limit)
    return success_response(data=ListResponse(items=items, total=total).model_dump(), message="模拟复盘列表查询成功")


@router.get("/{strategy_version}")
def get_simulation_review(strategy_version: str, db: Session = Depends(get_db)) -> dict[str, object]:
    """查询单次历史复盘详情。"""

    result = SimulationService(db).get_review(strategy_version)
    return success_response(data=result.model_dump(), message="模拟复盘详情查询成功")


@router.post("/run")
def run_simulation(payload: SimulationRunRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    """执行阶段6模拟交易复盘，并返回资金分配、持仓收益和复盘指标。"""

    result = SimulationService(db).run_review(
        start_date=payload.start_date,
        end_date=payload.end_date,
        stock_count=payload.stock_count,
        initial_cash=payload.initial_cash,
        min_score=payload.min_score,
        review_mode=payload.review_mode,
    )
    return success_response(data=result.model_dump(), message="模拟交易复盘完成")
