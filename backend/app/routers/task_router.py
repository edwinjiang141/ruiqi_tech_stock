from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ListResponse, TaskLogCreate, TaskLogRead, success_response
from app.services import TaskLogService

router = APIRouter(prefix="/api/tasks", tags=["任务"])


@router.get("")
def list_task_logs(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    service = TaskLogService(db)
    items = [TaskLogRead.model_validate(item).model_dump(mode="json") for item in service.list_logs(limit)]
    return success_response(
        data=ListResponse(items=items, total=len(items)).model_dump(),
        message="任务日志查询成功",
    )


@router.post("")
def create_task_log(payload: TaskLogCreate, db: Session = Depends(get_db)) -> dict[str, object]:
    service = TaskLogService(db)
    task_log = service.create_log(payload)
    return success_response(
        data=TaskLogRead.model_validate(task_log).model_dump(mode="json"),
        message="任务日志创建成功",
    )
