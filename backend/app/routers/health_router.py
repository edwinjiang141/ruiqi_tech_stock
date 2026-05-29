from fastapi import APIRouter

from app.config import get_settings
from app.database import check_database
from app.schemas import success_response

router = APIRouter(prefix="/api/health", tags=["健康检查"])


@router.get("")
def health_check() -> dict[str, object]:
    settings = get_settings()
    database_status = check_database()
    return success_response(
        data={
            "status": "ok",
            "app_name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "database": database_status,
        }
    )
