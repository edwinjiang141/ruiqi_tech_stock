from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


settings = get_settings()

engine: Engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database() -> dict[str, object]:
    """只读检查数据库连接和目标 schema 状态。"""

    with engine.connect() as connection:
        database_name = connection.execute(text("SELECT current_database()")).scalar_one()
        user_name = connection.execute(text("SELECT current_user")).scalar_one()
        schema_exists = inspect(connection).has_schema(settings.database_schema)

    return {
        "database": database_name,
        "user": user_name,
        "schema": settings.database_schema,
        "schema_exists": schema_exists,
    }
