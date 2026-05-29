import logging

from app.config import Settings


def configure_logging(settings: Settings) -> None:
    """配置中文友好的控制台日志。"""

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )
