from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import (
    StockAdjFactor,
    StockBasic,
    StockCashflow,
    StockDaily,
    StockDailyBasic,
    StockFinancialIndicator,
    StockMoneyflow,
)
from app.exceptions import AppException
from app.schemas import CollectionResult
from app.services.tushare_service import TushareService


UPSERT_BATCH_SIZE = 1000
NUMERIC_FIELDS = {
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "pre_close",
    "change_amount",
    "pct_chg",
    "volume",
    "amount",
    "adj_factor",
    "turnover_rate",
    "turnover_rate_f",
    "volume_ratio",
    "pe",
    "pe_ttm",
    "pb",
    "ps",
    "ps_ttm",
    "total_share",
    "float_share",
    "free_share",
    "total_mv",
    "circ_mv",
    "roe",
    "roa",
    "grossprofit_margin",
    "netprofit_margin",
    "revenue_yoy",
    "netprofit_yoy",
    "debt_to_assets",
    "current_ratio",
    "quick_ratio",
    "ocf_to_profit",
    "net_profit",
    "n_cashflow_act",
    "c_fr_sale_sg",
    "buy_sm_amount",
    "sell_sm_amount",
    "buy_md_amount",
    "sell_md_amount",
    "buy_lg_amount",
    "sell_lg_amount",
    "buy_elg_amount",
    "sell_elg_amount",
    "net_mf_amount",
}
NULL_TEXT_VALUES = {"", "none", "nan", "nat", "null", "--", "-", "n/a", "na"}


class MarketDataService:
    """行情、财务和资金流数据采集服务。"""

    def __init__(self, db: Session, tushare_service: TushareService | None = None) -> None:
        self.db = db
        self.tushare_service = tushare_service or TushareService()

    def collect_daily_market(self, trade_date: str) -> CollectionResult:
        daily_count = self.upsert_daily(self.tushare_service.daily(trade_date))
        adj_count = self.upsert_adj_factor(self.tushare_service.adj_factor(trade_date))
        basic_count = self.upsert_daily_basic(self.tushare_service.daily_basic(trade_date))
        total_count = daily_count + adj_count + basic_count
        return CollectionResult(
            task_name="collect_daily_market",
            source="daily,adj_factor,daily_basic",
            fetched_count=total_count,
            inserted_or_updated_count=total_count,
            message=f"{trade_date} 行情、复权和每日指标采集完成",
        )

    def collect_financial(self, period: str) -> CollectionResult:
        stock_codes = self._stock_pool_codes()
        period_date = self._parse_period(period)
        existing_indicator_codes = self._existing_financial_codes(StockFinancialIndicator, period_date, stock_codes)
        existing_cashflow_codes = self._existing_financial_codes(StockCashflow, period_date, stock_codes)
        pending_indicator_count = len(stock_codes) - len(existing_indicator_codes)
        pending_cashflow_count = len(stock_codes) - len(existing_cashflow_codes)
        failed_items: list[str] = []
        indicator_count = 0
        cashflow_count = 0
        indicator_quota_exceeded = False
        cashflow_quota_exceeded = False

        for ts_code in stock_codes:
            if ts_code not in existing_indicator_codes and not indicator_quota_exceeded:
                try:
                    indicator_count += self.upsert_financial_indicator(
                        self._validated_financial_frame(self.tushare_service.fina_indicator(ts_code, period), ts_code, period)
                    )
                except AppException as exc:
                    failed_items.append(f"{ts_code}:fina_indicator:{exc.message}")
                    indicator_quota_exceeded = exc.code == "TUSHARE_DAILY_QUOTA_EXCEEDED"
                except SQLAlchemyError:
                    self.db.rollback()
                    failed_items.append(f"{ts_code}:fina_indicator:数据库写入失败，已跳过")
                except Exception:
                    self.db.rollback()
                    failed_items.append(f"{ts_code}:fina_indicator:未知异常，已跳过")

            if ts_code not in existing_cashflow_codes and not cashflow_quota_exceeded:
                try:
                    cashflow_count += self.upsert_cashflow(self._validated_financial_frame(self.tushare_service.cashflow(ts_code, period), ts_code, period))
                except AppException as exc:
                    failed_items.append(f"{ts_code}:cashflow:{exc.message}")
                    cashflow_quota_exceeded = exc.code == "TUSHARE_DAILY_QUOTA_EXCEEDED"
                except SQLAlchemyError:
                    self.db.rollback()
                    failed_items.append(f"{ts_code}:cashflow:数据库写入失败，已跳过")
                except Exception:
                    self.db.rollback()
                    failed_items.append(f"{ts_code}:cashflow:未知异常，已跳过")

        total_count = indicator_count + cashflow_count
        status = "warning" if failed_items else "success"
        failure_summary = f"，失败 {len(failed_items)} 次，已跳过失败股票" if failed_items else ""
        return CollectionResult(
            task_name="collect_financial",
            source="fina_indicator,cashflow",
            fetched_count=total_count,
            inserted_or_updated_count=total_count,
            status=status,
            message=(
                f"{period} 财务指标和现金流采集完成，股票池覆盖 {len(stock_codes)} 只股票，"
                f"本次补缺财务指标 {indicator_count}/{pending_indicator_count} 条、现金流 {cashflow_count}/{pending_cashflow_count} 条"
                f"{failure_summary}"
            ),
        )

    def collect_moneyflow(self, trade_date: str) -> CollectionResult:
        count = self.upsert_moneyflow(self.tushare_service.moneyflow(trade_date))
        return CollectionResult(
            task_name="collect_moneyflow",
            source="moneyflow",
            fetched_count=count,
            inserted_or_updated_count=count,
            message=f"{trade_date} 资金流采集完成",
        )

    def upsert_daily(self, dataframe: pd.DataFrame) -> int:
        mapping = {
            "ts_code": "ts_code",
            "trade_date": "trade_date",
            "open": "open_price",
            "high": "high_price",
            "low": "low_price",
            "close": "close_price",
            "pre_close": "pre_close",
            "change": "change_amount",
            "pct_chg": "pct_chg",
            "vol": "volume",
            "amount": "amount",
        }
        return self._upsert(dataframe, StockDaily, mapping, ["ts_code", "trade_date"], date_fields={"trade_date"})

    def upsert_adj_factor(self, dataframe: pd.DataFrame) -> int:
        mapping = {"ts_code": "ts_code", "trade_date": "trade_date", "adj_factor": "adj_factor"}
        return self._upsert(dataframe, StockAdjFactor, mapping, ["ts_code", "trade_date"], date_fields={"trade_date"})

    def upsert_daily_basic(self, dataframe: pd.DataFrame) -> int:
        mapping = {
            "ts_code": "ts_code",
            "trade_date": "trade_date",
            "close": "close_price",
            "turnover_rate": "turnover_rate",
            "turnover_rate_f": "turnover_rate_f",
            "volume_ratio": "volume_ratio",
            "pe": "pe",
            "pe_ttm": "pe_ttm",
            "pb": "pb",
            "ps": "ps",
            "ps_ttm": "ps_ttm",
            "total_share": "total_share",
            "float_share": "float_share",
            "free_share": "free_share",
            "total_mv": "total_mv",
            "circ_mv": "circ_mv",
        }
        return self._upsert(dataframe, StockDailyBasic, mapping, ["ts_code", "trade_date"], date_fields={"trade_date"})

    def upsert_financial_indicator(self, dataframe: pd.DataFrame) -> int:
        mapping = {
            "ts_code": "ts_code",
            "ann_date": "ann_date",
            "end_date": "end_date",
            "roe": "roe",
            "roa": "roa",
            "grossprofit_margin": "grossprofit_margin",
            "netprofit_margin": "netprofit_margin",
            "revenue_yoy": "revenue_yoy",
            "netprofit_yoy": "netprofit_yoy",
            "debt_to_assets": "debt_to_assets",
            "current_ratio": "current_ratio",
            "quick_ratio": "quick_ratio",
            "ocf_to_profit": "ocf_to_profit",
        }
        return self._upsert(dataframe, StockFinancialIndicator, mapping, ["ts_code", "end_date"], date_fields={"ann_date", "end_date"})

    def upsert_cashflow(self, dataframe: pd.DataFrame) -> int:
        mapping = {
            "ts_code": "ts_code",
            "ann_date": "ann_date",
            "end_date": "end_date",
            "net_profit": "net_profit",
            "n_cashflow_act": "n_cashflow_act",
            "c_fr_sale_sg": "c_fr_sale_sg",
        }
        return self._upsert(dataframe, StockCashflow, mapping, ["ts_code", "end_date"], date_fields={"ann_date", "end_date"})

    def upsert_moneyflow(self, dataframe: pd.DataFrame) -> int:
        mapping = {
            "ts_code": "ts_code",
            "trade_date": "trade_date",
            "buy_sm_amount": "buy_sm_amount",
            "sell_sm_amount": "sell_sm_amount",
            "buy_md_amount": "buy_md_amount",
            "sell_md_amount": "sell_md_amount",
            "buy_lg_amount": "buy_lg_amount",
            "sell_lg_amount": "sell_lg_amount",
            "buy_elg_amount": "buy_elg_amount",
            "sell_elg_amount": "sell_elg_amount",
            "net_mf_amount": "net_mf_amount",
        }
        return self._upsert(dataframe, StockMoneyflow, mapping, ["ts_code", "trade_date"], date_fields={"trade_date"})

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
            upsert = statement.on_conflict_do_update(index_elements=conflict_columns, set_=update_columns)
            self.db.execute(upsert)
        self.db.commit()
        return len(records)

    def _normalize_record(self, record: dict[str, Any], mapping: dict[str, str], date_fields: set[str]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for source_field, target_field in mapping.items():
            value = record.get(source_field)
            if target_field in date_fields:
                normalized[target_field] = self._parse_date(value)
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

    def _existing_financial_codes(self, model: type, period: date, stock_codes: list[str]) -> set[str]:
        statement = select(model.ts_code).where(model.end_date == period, model.ts_code.in_(stock_codes))
        return set(self.db.scalars(statement).all())

    @staticmethod
    def _validated_financial_frame(dataframe: pd.DataFrame, expected_ts_code: str, period: str) -> pd.DataFrame:
        if dataframe.empty:
            return dataframe
        if "ts_code" not in dataframe.columns:
            raise AppException(f"Tushare 财务接口返回缺少 ts_code，已跳过 {expected_ts_code}", code="TUSHARE_DATA_MISMATCH")

        filtered = dataframe[dataframe["ts_code"].astype(str) == expected_ts_code]
        if "end_date" in filtered.columns:
            filtered = filtered[filtered["end_date"].astype(str) == period]
        if filtered.empty:
            raise AppException(f"Tushare 财务接口返回股票或报告期不匹配，已跳过 {expected_ts_code}", code="TUSHARE_DATA_MISMATCH")
        return filtered.copy()

    @staticmethod
    def _parse_period(period: str) -> date:
        return datetime.strptime(period, "%Y%m%d").date()

    @staticmethod
    def _concat_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
        valid_frames = [frame for frame in frames if not frame.empty]
        if not valid_frames:
            return pd.DataFrame()
        return pd.concat(valid_frames, ignore_index=True)

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
        if isinstance(value, float):
            return Decimal(str(value))
        if isinstance(value, int):
            return Decimal(value)
        try:
            return Decimal(str(value))
        except Exception:
            return None

    @staticmethod
    def _deduplicate_records(records: list[dict[str, Any]], conflict_columns: list[str]) -> list[dict[str, Any]]:
        deduplicated: dict[tuple[Any, ...], dict[str, Any]] = {}
        for record in records:
            deduplicated[tuple(record.get(column) for column in conflict_columns)] = record
        return list(deduplicated.values())

    @staticmethod
    def _chunk_records(records: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
        return [records[index : index + batch_size] for index in range(0, len(records), batch_size)]
