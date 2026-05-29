from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ListResponse, StockRead, success_response
from app.services import StockPoolService

router = APIRouter(prefix="/api/stocks", tags=["股票"])


@router.get("")
def list_stocks(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """查询股票基础信息列表。"""

    service = StockPoolService(db)
    items, total = service.list_stocks(limit=limit)
    payload = [StockRead.model_validate(item).model_dump(mode="json") for item in items]
    return success_response(data=ListResponse(items=payload, total=total).model_dump(), message="股票列表查询成功")
