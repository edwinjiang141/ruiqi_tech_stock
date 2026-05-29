from datetime import datetime

from app.database import SessionLocal
from app.services import TaskLogService


def test_task_log_can_track_running_and_finished_status() -> None:
    with SessionLocal() as db:
        service = TaskLogService(db)
        task_log = service.start_log(
            task_name="阶段测试运行中任务",
            task_type="collection",
            started_at=datetime.now(),
            message="任务已提交，正在执行。",
        )

        assert task_log.status == "running"
        assert task_log.finished_at is None

        finished_log = service.finish_log(task_log, "success", datetime.now(), "任务执行完成")

        assert finished_log.status == "success"
        assert finished_log.finished_at is not None
        assert finished_log.message == "任务执行完成"

        db.delete(finished_log)
        db.commit()
