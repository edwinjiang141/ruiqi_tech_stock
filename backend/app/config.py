from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    """系统运行配置，默认值适配当前开发环境。"""

    app_name: str = "创业板与科技板块优质股票研究推荐系统"
    app_version: str = "1.2.0"
    environment: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(
        default="postgresql+psycopg://ruiqi:ruiqi123@127.0.0.1:5432/ruiqi_stock",
        alias="DATABASE_URL",
    )
    database_schema: str = Field(default="stock_research_v12", alias="DATABASE_SCHEMA")
    tushare_token: str | None = Field(default=None, alias="TUSHARE_TOKEN")
    tushare_api_url: str = Field(default="http://api.waditu.com/dataapi", alias="TUSHARE_API_URL")
    tushare_timeout: int = Field(default=30, alias="TUSHARE_TIMEOUT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=(WORKSPACE_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
