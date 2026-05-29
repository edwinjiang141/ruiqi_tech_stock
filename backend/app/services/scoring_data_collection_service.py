from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.exceptions import AppException
from app.models import (
    IndexWeight,
    StockBalanceSheet,
    StockBasic,
    StockIncome,
    StockLimit,
    StockPledgeStat,
    TradeCalendar,
)
from app.schemas import CollectionResult, QualityMetric, QualityReport
from app.services.tushare_service import TushareService

UPSERT_BATCH_SIZE = 1000
NULL_TEXT_VALUES = {"", "none", "nan", "nat", "null", "--", "-", "n/a", "na"}
NUMERIC_FIELDS = {
    "total_revenue",
    "revenue",
    "operate_profit",
    "total_profit",
    "n_income",
    "n_income_attr_p",
    "total_assets",
    "total_liab",
    "total_hldr_eqy_exc_min_int",
    "total_hldr_eqy_inc_min_int",
    "goodwill",
    "total_cur_assets",
    "total_cur_liab",
    "weight",
    "unrest_pledge",
    "rest_pledge",
    "total_share",
    "pledge_ratio",
    "pre_close",
    "up_limit",
    "down_limit",
}


class ScoringDataCollectionService:
    """阶段5评分前置数据采集，按 2000 积分权限设计为低频、可重试、可幂等。"""

    def __init__(self, db: Session, tushare_service: TushareService | None = None) -> None:
        self.db = db
        self.tushare_service = tushare_service or TushareService()

    def collect_scoring_financial_range(self, start_period: str, end_period: str) -> CollectionResult:
        stock_codes = self._stock_pool_codes()
        income_count = 0
        balance_count = 0
        failed_items: list[str] = []

        for ts_code in stock_codes:
            try:
                income_count += self.upsert_income(self._filter_stock_period_frame(self.tushare_service.income(ts_code, start_period, end_period), ts_code))
            except Exception as exc:
                self.db.rollback()
                failed_items.append(f"{ts_code}:income:{self._safe_error(exc)}")

            try:
                balance_count += self.upsert_balancesheet(
                    self._filter_stock_period_frame(self.tushare_service.balancesheet(ts_code, start_period, end_period), ts_code)
                )
            except Exception as exc:
                self.db.rollback()
                failed_items.append(f"{ts_code}:balancesheet:{self._safe_error(exc)}")

        total_count = income_count + balance_count
        status = "warning" if failed_items else "success"
        failure_summary = f"，失败 {len(failed_items)} 次，已跳过失败股票" if failed_items else ""
        return CollectionResult(
            task_name="collect_scoring_financial_range",
            source="income,balancesheet",
            fetched_count=total_count,
            inserted_or_updated_count=total_count,
            status=status,
            message=f"{start_period} 至 {end_period} 评分财务前置数据补齐完成，股票池覆盖 {len(stock_codes)} 只股票{failure_summary}",
        )

    def collect_scoring_risk_data(self, start_date: str, end_date: str) -> CollectionResult:
        stock_codes = self._stock_pool_codes()
        dates = self._date_range(start_date, end_date, max_days=31)
        pledge_count = 0
        calendar_count = 0
        limit_count = 0
        failed_items: list[str] = []

        try:
            calendar_count = self.upsert_trade_calendar(self.tushare_service.trade_cal(start_date, end_date))
        except Exception as exc:
            self.db.rollback()
            failed_items.append(f"trade_cal:{self._safe_error(exc)}")

        for trade_date in dates:
            try:
                limit_count += self.upsert_stock_limit(self.tushare_service.stk_limit(trade_date))
            except Exception as exc:
                self.db.rollback()
                failed_items.append(f"{trade_date}:stk_limit:{self._safe_error(exc)}")

        for ts_code in stock_codes:
            try:
                pledge_count += self.upsert_pledge_stat(self._filter_stock_period_frame(self.tushare_service.pledge_stat(ts_code), ts_code))
            except Exception as exc:
                self.db.rollback()
                failed_items.append(f"{ts_code}:pledge_stat:{self._safe_error(exc)}")

        total_count = pledge_count + calendar_count + limit_count
        status = "warning" if failed_items else "success"
        failure_summary = f"，失败 {len(failed_items)} 次，已跳过失败项" if failed_items else ""
        return CollectionResult(
            task_name="collect_scoring_risk_data",
            source="pledge_stat,trade_cal,stk_limit",
            fetched_count=total_count,
            inserted_or_updated_count=total_count,
            status=status,
            message=f"{start_date} 至 {end_date} 风险与交易日历数据补齐完成{failure_summary}",
        )

    def collect_index_weight_range(self, index_codes: list[str], start_date: str, end_date: str) -> CollectionResult:
        changed_count = 0
        failed_items: list[str] = []
        for index_code in index_codes:
            try:
                changed_count += self.upsert_index_weight(self.tushare_service.index_weight(index_code, start_date, end_date))
            except Exception as exc:
                self.db.rollback()
                failed_items.append(f"{index_code}:index_weight:{self._safe_error(exc)}")

        status = "warning" if failed_items else "success"
        failure_summary = f"，失败 {len(failed_items)} 个指数" if failed_items else ""
        return CollectionResult(
            task_name="collect_index_weight_range",
            source="index_weight",
            fetched_count=changed_count,
            inserted_or_updated_count=changed_count,
            status=status,
            message=f"{start_date} 至 {end_date} 指数权重补齐完成，覆盖 {len(index_codes)} 个指数{failure_summary}",
        )

    def check_scoring_data_quality(self) -> QualityReport:
        stock_pool_count = self._stock_pool_count()
        income_count = self.db.scalar(select(func.count()).select_from(StockIncome)) or 0
        balance_count = self.db.scalar(select(func.count()).select_from(StockBalanceSheet)) or 0
        pledge_count = self.db.scalar(select(func.count()).select_from(StockPledgeStat)) or 0
        index_weight_count = self.db.scalar(select(func.count()).select_from(IndexWeight)) or 0
        calendar_count = self.db.scalar(select(func.count()).select_from(TradeCalendar).where(TradeCalendar.is_open.is_(True))) or 0
        limit_count = self.db.scalar(select(func.count()).select_from(StockLimit)) or 0

        metrics = [
            QualityMetric(name="stock_pool_count", value=stock_pool_count, passed=stock_pool_count > 0, message="股票池必须先完成采集"),
            QualityMetric(name="income_count", value=income_count, passed=income_count > 0, message="利润表数据用于 CAGR、环比改善和营收排名"),
            QualityMetric(name="balancesheet_count", value=balance_count, passed=balance_count > 0, message="资产负债表数据用于净资产和商誉风险"),
            QualityMetric(name="pledge_stat_count", value=pledge_count, passed=pledge_count > 0, message="股权质押数据用于质押风险扣分"),
            QualityMetric(name="index_weight_count", value=index_weight_count, passed=index_weight_count > 0, message="指数权重数据用于龙头地位评分"),
            QualityMetric(name="open_trade_calendar_count", value=calendar_count, passed=calendar_count >= 120, message="至少需要 120 个开放交易日用于评分窗口"),
            QualityMetric(name="stock_limit_count", value=limit_count, passed=limit_count > 0, message="涨跌停数据用于后续模拟交易约束"),
        ]
        return QualityReport(target="scoring_data_contract", passed=all(metric.passed for metric in metrics), metrics=metrics)

    def _stock_pool_count(self) -> int:
        return (
            self.db.scalar(
                select(func.count())
                .select_from(StockBasic)
                .where((StockBasic.is_gem.is_(True)) | (StockBasic.is_star.is_(True)) | (StockBasic.is_tech_industry.is_(True)))
            )
            or 0
        )

    def upsert_income(self, dataframe: pd.DataFrame) -> int:
        mapping = {
            "ts_code": "ts_code",
            "ann_date": "ann_date",
            "f_ann_date": "f_ann_date",
            "end_date": "end_date",
            "report_type": "report_type",
            "comp_type": "comp_type",
            "total_revenue": "total_revenue",
            "revenue": "revenue",
            "operate_profit": "operate_profit",
            "total_profit": "total_profit",
            "n_income": "n_income",
            "n_income_attr_p": "n_income_attr_p",
        }
        return self._upsert(dataframe, StockIncome, mapping, ["ts_code", "end_date"], date_fields={"ann_date", "f_ann_date", "end_date"})

    def upsert_balancesheet(self, dataframe: pd.DataFrame) -> int:
        mapping = {
            "ts_code": "ts_code",
            "ann_date": "ann_date",
            "f_ann_date": "f_ann_date",
            "end_date": "end_date",
            "report_type": "report_type",
            "comp_type": "comp_type",
            "total_assets": "total_assets",
            "total_liab": "total_liab",
            "total_hldr_eqy_exc_min_int": "total_hldr_eqy_exc_min_int",
            "total_hldr_eqy_inc_min_int": "total_hldr_eqy_inc_min_int",
            "goodwill": "goodwill",
            "total_cur_assets": "total_cur_assets",
            "total_cur_liab": "total_cur_liab",
        }
        return self._upsert(dataframe, StockBalanceSheet, mapping, ["ts_code", "end_date"], date_fields={"ann_date", "f_ann_date", "end_date"})

    def upsert_index_weight(self, dataframe: pd.DataFrame) -> int:
        mapping = {"index_code": "index_code", "con_code": "con_code", "trade_date": "trade_date", "weight": "weight"}
        return self._upsert(dataframe, IndexWeight, mapping, ["index_code", "con_code", "trade_date"], date_fields={"trade_date"})

    def upsert_pledge_stat(self, dataframe: pd.DataFrame) -> int:
        mapping = {
            "ts_code": "ts_code",
            "end_date": "end_date",
            "pledge_count": "pledge_count",
            "unrest_pledge": "unrest_pledge",
            "rest_pledge": "rest_pledge",
            "total_share": "total_share",
            "pledge_ratio": "pledge_ratio",
        }
        return self._upsert(dataframe, StockPledgeStat, mapping, ["ts_code", "end_date"], date_fields={"end_date"})

    def upsert_trade_calendar(self, dataframe: pd.DataFrame) -> int:
        mapping = {"exchange": "exchange", "cal_date": "cal_date", "is_open": "is_open", "pretrade_date": "pretrade_date"}
        return self._upsert(dataframe, TradeCalendar, mapping, ["exchange", "cal_date"], date_fields={"cal_date", "pretrade_date"})

    def upsert_stock_limit(self, dataframe: pd.DataFrame) -> int:
        mapping = {"ts_code": "ts_code", "trade_date": "trade_date", "pre_close": "pre_close", "up_limit": "up_limit", "down_limit": "down_limit"}
        return self._upsert(dataframe, StockLimit, mapping, ["ts_code", "trade_date"], date_fields={"trade_date"})

    def _upsert(
        self,
        dataframe: pd.DataFrame,
        model: type,
        mapping: dict[str, str],
        conflict_columns: list[str],
        date_fields: set[str],
    ) -> int:
        records = [self._normalize_record(record, mapping, date_fields) for record in dataframe.to_dict(orient="records")]
        records = [record for record in records if all(record.get(column) is not None for column in conflict_columns)]
        records = self._deduplicate_records(records, conflict_columns)
        if not records:
            return 0

        for batch in self._chunk_records(records, UPSERT_BATCH_SIZE):
            statement = insert(model).values(batch)
            update_columns = {
                column.name: getattr(statement.excluded, column.name)
                for column in model.__table__.columns
                if column.name not in {*conflict_columns, "created_at"}
            }
            self.db.execute(statement.on_conflict_do_update(index_elements=conflict_columns, set_=update_columns))
        self.db.commit()
        return len(records)

    def _normalize_record(self, record: dict[str, Any], mapping: dict[str, str], date_fields: set[str]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for source_field, target_field in mapping.items():
            value = record.get(source_field)
            if target_field in date_fields:
                normalized[target_field] = self._parse_date(value)
            elif target_field == "pledge_count":
                normalized[target_field] = self._clean_int(value)
            elif target_field == "is_open":
                normalized[target_field] = self._clean_bool(value)
            elif target_field in NUMERIC_FIELDS:
                normalized[target_field] = self._clean_numeric(value)
            else:
                normalized[target_field] = self._clean_value(value)
        return normalized

    def _stock_pool_codes(self) -> list[str]:
        statement = (
            select(StockBasic.ts_code)
            .where((StockBasic.is_gem.is_(True)) | (StockBasic.is_star.is_(True)) | (StockBasic.is_tech_industry.is_(True)))
            .order_by(StockBasic.ts_code)
        )
        codes = list(self.db.scalars(statement).all())
        if not codes:
            raise AppException("股票池为空，请先执行股票池采集。", code="STOCK_POOL_EMPTY", status_code=400)
        return codes

    @staticmethod
    def _filter_stock_period_frame(dataframe: pd.DataFrame, expected_ts_code: str) -> pd.DataFrame:
        if dataframe.empty:
            return dataframe
        if "ts_code" not in dataframe.columns:
            raise AppException(f"Tushare 返回缺少 ts_code，已跳过 {expected_ts_code}", code="TUSHARE_DATA_MISMATCH")
        return dataframe[dataframe["ts_code"].astype(str) == expected_ts_code].copy()

    @staticmethod
    def _parse_date(value: Any) -> Any:
        if value is None or pd.isna(value):
            return None
        text = str(value).strip()
        if not text or text.lower() in NULL_TEXT_VALUES:
            return None
        if text.endswith(".0"):
            text = text[:-2]
        return datetime.strptime(text, "%Y%m%d").date()

    @staticmethod
    def _clean_value(value: Any) -> Any:
        if value is None or pd.isna(value):
            return None
        if isinstance(value, str):
            text = value.strip()
            return None if text.lower() in NULL_TEXT_VALUES else text
        return value

    @staticmethod
    def _clean_numeric(value: Any) -> Decimal | None:
        if value is None or pd.isna(value):
            return None
        if isinstance(value, str):
            text = value.strip().replace(",", "")
            if text.lower() in NULL_TEXT_VALUES:
                return None
            value = text
        try:
            return Decimal(str(value))
        except Exception:
            return None

    @staticmethod
    def _clean_int(value: Any) -> int | None:
        numeric = ScoringDataCollectionService._clean_numeric(value)
        return int(numeric) if numeric is not None else None

    @staticmethod
    def _clean_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None or pd.isna(value):
            return False
        return str(value).strip() in {"1", "true", "True", "Y", "y"}

    @staticmethod
    def _date_range(start_date: str, end_date: str, max_days: int) -> list[str]:
        start = datetime.strptime(start_date, "%Y%m%d").date()
        end = datetime.strptime(end_date, "%Y%m%d").date()
        if start > end:
            raise AppException("开始日期不能晚于结束日期", code="INVALID_DATE_RANGE", status_code=422)
        if (end - start).days + 1 > max_days:
            raise AppException(f"单次区间最多支持 {max_days} 天", code="DATE_RANGE_TOO_LARGE", status_code=422)
        return [(start + timedelta(days=offset)).strftime("%Y%m%d") for offset in range((end - start).days + 1)]

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        if isinstance(exc, AppException):
            return exc.message
        if isinstance(exc, SQLAlchemyError):
            return "数据库写入失败"
        return "接口或数据处理异常"

    @staticmethod
    def _deduplicate_records(records: list[dict[str, Any]], conflict_columns: list[str]) -> list[dict[str, Any]]:
        deduplicated: dict[tuple[Any, ...], dict[str, Any]] = {}
        for record in records:
            deduplicated[tuple(record.get(column) for column in conflict_columns)] = record
        return list(deduplicated.values())

    @staticmethod
    def _chunk_records(records: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
        return [records[index : index + batch_size] for index in range(0, len(records), batch_size)]
