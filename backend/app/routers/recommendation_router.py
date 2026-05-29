from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.schemas import ListResponse, success_response
from app.database import get_db
from app.services import RecommendationService

router = APIRouter(prefix="/api/recommendations", tags=["推荐"])


@router.get("")
def list_recommendations(
    trade_date: str | None = Query(default=None),
    level: str | None = Query(default=None, pattern=r"^[SABCD]$"),
    min_score: float | None = Query(default=None, ge=0, le=100),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """查询阶段5每日推荐结果。"""

    items, total = RecommendationService(db).list_recommendations(trade_date=trade_date, level=level, min_score=min_score, limit=limit)
    return success_response(data=ListResponse(items=items, total=total).model_dump(), message="推荐列表查询成功")
