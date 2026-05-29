from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TaskLog
from app.schemas.task_schema import TaskLogCreate


class TaskLogService:
    """任务日志服务，供采集、计算、评分和复盘流程复用。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_log(self, payload: TaskLogCreate) -> TaskLog:
        task_log = TaskLog(**payload.model_dump())
        self.db.add(task_log)
        self.db.commit()
        self.db.refresh(task_log)
        return task_log

    def start_log(self, task_name: str, task_type: str, started_at: datetime, message: str) -> TaskLog:
        """创建运行中任务日志，让前端能立即看到任务状态。"""

        return self.create_log(
            TaskLogCreate(
                task_name=task_name,
                task_type=task_type,
                status="running",
                started_at=started_at,
                message=message,
            )
        )

    def finish_log(self, task_log: TaskLog, status: str, finished_at: datetime, message: str) -> TaskLog:
        """更新任务最终状态。"""

        task_log.status = status
        task_log.finished_at = finished_at
        task_log.message = message
        self.db.add(task_log)
        self.db.commit()
        self.db.refresh(task_log)
        return task_log

    def list_logs(self, limit: int = 20) -> list[TaskLog]:
        statement = select(TaskLog).order_by(TaskLog.created_at.desc()).limit(limit)
        return list(self.db.scalars(statement).all())
