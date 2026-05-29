from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.schemas import ListResponse, success_response
from app.database import get_db
from app.services import ScoringService, TaskLogService

router = APIRouter(prefix="/api/factors", tags=["因子"])


@router.get("")
def list_factor_scores(
    trade_date: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """查询阶段5因子评分结果。"""

    items, total = ScoringService(db).list_factor_scores(trade_date=trade_date, limit=limit)
    return success_response(data=ListResponse(items=items, total=total).model_dump(), message="因子评分查询成功")


@router.get("/history")
def list_factor_score_history(
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """查询已有因子评分交易日历史记录。"""

    items, total = ScoringService(db).list_score_history(limit=limit, offset=offset)
    return success_response(data=ListResponse(items=items, total=total).model_dump(), message="历史评分记录查询成功")


@router.post("/calculate")
def calculate_factor_scores(
    trade_date: str = Query(..., pattern=r"^\d{4}-?\d{2}-?\d{2}$"),
    top_n: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """按指定交易日执行因子计算、评分和推荐生成。"""

    task_service = TaskLogService(db)
    task_log = task_service.start_log("calculate_factor_scores", "scoring", datetime.now(), "因子评分任务已提交，正在执行。")
    try:
        result = ScoringService(db).calculate_for_date(trade_date, top_n=top_n)
    except Exception:
        db.rollback()
        task_service.finish_log(task_log, "failed", datetime.now(), "因子评分任务执行失败，请查看后台日志。")
        raise

    task_service.finish_log(task_log, result.status, datetime.now(), result.message)
    return success_response(data=result.model_dump(), message="因子评分任务完成")
