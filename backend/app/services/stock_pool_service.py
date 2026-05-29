from datetime import date, datetime
from typing import Any

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import StockBasic
from app.schemas import CollectionResult
from app.services.tushare_service import TushareService


TECH_INDUSTRY_KEYWORDS = (
    "半导体",
    "软件",
    "互联网",
    "通信",
    "电子",
    "计算机",
    "信息技术",
    "自动化",
    "机器人",
    "新能源",
    "电池",
    "光伏",
    "芯片",
)

UPSERT_BATCH_SIZE = 1000


class StockPoolService:
    """股票池构建服务，负责采集股票基础信息并幂等写入数据库。"""

    def __init__(self, db: Session, tushare_service: TushareService | None = None) -> None:
        self.db = db
        self.tushare_service = tushare_service or TushareService()

    def collect_stock_pool(self) -> CollectionResult:
        dataframe = self.tushare_service.stock_basic()
        count = self.upsert_stock_basic(dataframe)
        return CollectionResult(
            task_name="collect_stock_pool",
            source="stock_basic",
            fetched_count=len(dataframe),
            inserted_or_updated_count=count,
            message="股票池基础数据采集完成",
        )

    def upsert_stock_basic(self, dataframe: pd.DataFrame) -> int:
        records = [self._normalize_record(record) for record in dataframe.to_dict(orient="records")]
        records = [record for record in records if record.get("ts_code")]
        if not records:
            return 0

        for batch in self._chunk_records(records, UPSERT_BATCH_SIZE):
            statement = insert(StockBasic).values(batch)
            update_columns = {
                column.name: getattr(statement.excluded, column.name)
                for column in StockBasic.__table__.columns
                if column.name not in {"ts_code", "created_at"}
            }
            update_columns["updated_at"] = func.now()

            upsert = statement.on_conflict_do_update(
                index_elements=[StockBasic.ts_code],
                set_=update_columns,
            )
            self.db.execute(upsert)
        self.db.commit()
        return len(records)

    def list_stocks(self, limit: int = 50) -> tuple[list[StockBasic], int]:
        total = self.db.scalar(select(func.count()).select_from(StockBasic)) or 0
        statement = select(StockBasic).order_by(StockBasic.ts_code).limit(limit)
        return list(self.db.scalars(statement).all()), total

    def _normalize_record(self, record: dict[str, Any]) -> dict[str, Any]:
        ts_code = self._clean_text(record.get("ts_code"))
        market = self._clean_text(record.get("market"))
        industry = self._clean_text(record.get("industry"))

        return {
            "ts_code": ts_code,
            "symbol": self._clean_text(record.get("symbol")),
            "name": self._clean_text(record.get("name")),
            "area": self._clean_text(record.get("area")),
            "industry": industry,
            "market": market,
            "exchange": self._clean_text(record.get("exchange")),
            "list_status": self._clean_text(record.get("list_status")),
            "list_date": self._parse_date(record.get("list_date")),
            "delist_date": self._parse_date(record.get("delist_date")),
            "is_hs": self._clean_text(record.get("is_hs")),
            "is_gem": bool(ts_code and ts_code.startswith("300")),
            "is_star": market == "科创板" or bool(ts_code and ts_code.startswith("688")),
            "is_tech_industry": self._is_tech_industry(industry),
        }

    @staticmethod
    def _clean_text(value: Any) -> str | None:
        if value is None or pd.isna(value):
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if value is None or pd.isna(value):
            return None
        text = str(value).strip()
        if not text:
            return None
        return datetime.strptime(text, "%Y%m%d").date()

    @staticmethod
    def _is_tech_industry(industry: str | None) -> bool:
        if not industry:
            return False
        return any(keyword in industry for keyword in TECH_INDUSTRY_KEYWORDS)

    @staticmethod
    def _chunk_records(records: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
        return [records[index : index + batch_size] for index in range(0, len(records), batch_size)]
