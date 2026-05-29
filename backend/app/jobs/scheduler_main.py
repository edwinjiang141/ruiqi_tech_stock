import logging

from app.config import get_settings
from app.logging_config import configure_logging


def main() -> None:
    settings = get_settings()
    configure_logging(settings)

    from apscheduler.schedulers.blocking import BlockingScheduler

    scheduler = BlockingScheduler(timezone="Asia/Shanghai")
    logging.info("APScheduler 已启动，后续阶段将注册采集、评分和复盘任务")
    scheduler.start()


if __name__ == "__main__":
    main()
