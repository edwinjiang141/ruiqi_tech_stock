from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TaskLogCreate(BaseModel):
    """任务日志创建请求。"""

    task_name: str = Field(..., min_length=1, max_length=100)
    task_type: str = Field(..., min_length=1, max_length=50)
    status: str = Field(..., min_length=1, max_length=30)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    message: str | None = None


class TaskLogRead(BaseModel):
    """任务日志响应结构。"""

    id: int
    task_name: str
    task_type: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    message: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
