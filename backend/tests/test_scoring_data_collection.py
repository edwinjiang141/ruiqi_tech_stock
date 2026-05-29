from datetime import date

import pandas as pd
from sqlalchemy import delete, func, select

from app.database import SessionLocal
from app.exceptions import AppException
from app.models import IndexWeight, StockBalanceSheet, StockIncome, StockLimit, StockPledgeStat, TradeCalendar
from app.services import ScoringDataCollectionService


def test_scoring_data_upserts_are_idempotent_and_clean_dirty_values() -> None:
    ts_code = "300991.SZ"
    index_code = "399006.SZ"
    test_date = date(2026, 3, 31)
    try:
        with SessionLocal() as db:
            for model in [StockIncome, StockBalanceSheet, StockPledgeStat, StockLimit]:
                db.execute(delete(model).where(model.ts_code == ts_code))
            db.execute(delete(IndexWeight).where((IndexWeight.index_code == index_code) & (IndexWeight.con_code == ts_code)))
            db.execute(delete(TradeCalendar).where(TradeCalendar.cal_date == test_date))
            db.commit()

            service = ScoringDataCollectionService(db)
            income_count = service.upsert_income(
                pd.DataFrame(
                    [
                        {
                            "ts_code": ts_code,
                            "ann_date": "20260430",
                            "f_ann_date": "20260430",
                            "end_date": "20260331",
                            "total_revenue": "--",
                            "revenue": "123.45",
                            "n_income_attr_p": "nan",
                        }
                    ]
                )
            )
            balance_count = service.upsert_balancesheet(
                pd.DataFrame(
                    [
                        {
                            "ts_code": ts_code,
                            "ann_date": "20260430",
                            "end_date": "20260331",
                            "total_assets": "1000",
                            "total_liab": "",
                            "goodwill": "12.34",
                        }
                    ]
                )
            )
            pledge_count = service.upsert_pledge_stat(pd.DataFrame([{"ts_code": ts_code, "end_date": "20260331", "pledge_count": "2", "pledge_ratio": "3.5"}]))
            calendar_count = service.upsert_trade_calendar(pd.DataFrame([{"exchange": "SSE", "cal_date": "20260331", "is_open": "1"}]))
            limit_count = service.upsert_stock_limit(pd.DataFrame([{"ts_code": ts_code, "trade_date": "20260331", "up_limit": "20.12", "down_limit": "--"}]))
            weight_count = service.upsert_index_weight(pd.DataFrame([{"index_code": index_code, "con_code": ts_code, "trade_date": "20260331", "weight": "1.23"}]))

            service.upsert_income(pd.DataFrame([{"ts_code": ts_code, "end_date": "20260331", "revenue": "456.78"}]))

            income = db.scalar(select(StockIncome).where(StockIncome.ts_code == ts_code))
            balance = db.scalar(select(StockBalanceSheet).where(StockBalanceSheet.ts_code == ts_code))
            pledge = db.scalar(select(StockPledgeStat).where(StockPledgeStat.ts_code == ts_code))
            stock_limit = db.scalar(select(StockLimit).where(StockLimit.ts_code == ts_code))
            row_counts = {
                "income": db.scalar(select(func.count()).select_from(StockIncome).where(StockIncome.ts_code == ts_code)),
                "balance": db.scalar(select(func.count()).select_from(StockBalanceSheet).where(StockBalanceSheet.ts_code == ts_code)),
                "pledge": db.scalar(select(func.count()).select_from(StockPledgeStat).where(StockPledgeStat.ts_code == ts_code)),
                "calendar": db.scalar(select(func.count()).select_from(TradeCalendar).where(TradeCalendar.cal_date == test_date)),
                "limit": db.scalar(select(func.count()).select_from(StockLimit).where(StockLimit.ts_code == ts_code)),
                "weight": db.scalar(select(func.count()).select_from(IndexWeight).where((IndexWeight.index_code == index_code) & (IndexWeight.con_code == ts_code))),
            }

        assert income_count == 1
        assert balance_count == 1
        assert pledge_count == 1
        assert calendar_count == 1
        assert limit_count == 1
        assert weight_count == 1
        assert income is not None
        assert str(income.revenue) == "456.7800"
        assert income.total_revenue is None
        assert balance is not None
        assert balance.total_liab is None
        assert pledge is not None
        assert pledge.pledge_count == 2
        assert stock_limit is not None
        assert stock_limit.down_limit is None
        assert row_counts == {"income": 1, "balance": 1, "pledge": 1, "calendar": 1, "limit": 1, "weight": 1}
    finally:
        with SessionLocal() as db:
            for model in [StockIncome, StockBalanceSheet, StockPledgeStat, StockLimit]:
                db.execute(delete(model).where(model.ts_code == ts_code))
            db.execute(delete(IndexWeight).where((IndexWeight.index_code == index_code) & (IndexWeight.con_code == ts_code)))
            db.execute(delete(TradeCalendar).where(TradeCalendar.cal_date == test_date))
            db.commit()


class PartialFailureScoringTushareService:
    def income(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        return pd.DataFrame([{"ts_code": ts_code, "ann_date": "20260430", "end_date": start_date, "revenue": "100"}])

    def balancesheet(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        if ts_code == "688992.SH":
            raise AppException("模拟资产负债表失败", code="TUSHARE_CALL_FAILED", status_code=502)
        return pd.DataFrame([{"ts_code": ts_code, "ann_date": "20260430", "end_date": start_date, "total_assets": "200"}])


def test_scoring_financial_collection_keeps_partial_success(monkeypatch) -> None:
    codes = ["300992.SZ", "688992.SH"]
    try:
        with SessionLocal() as db:
            for model in [StockIncome, StockBalanceSheet]:
                db.execute(delete(model).where(model.ts_code.in_(codes)))
            db.commit()

            service = ScoringDataCollectionService(db, tushare_service=PartialFailureScoringTushareService())
            monkeypatch.setattr(service, "_stock_pool_codes", lambda: codes)
            result = service.collect_scoring_financial_range("20260331", "20260331")

            income_count = db.scalar(select(func.count()).select_from(StockIncome).where(StockIncome.ts_code.in_(codes)))
            balance_count = db.scalar(select(func.count()).select_from(StockBalanceSheet).where(StockBalanceSheet.ts_code.in_(codes)))

        assert result.status == "warning"
        assert result.fetched_count == 3
        assert income_count == 2
        assert balance_count == 1
    finally:
        with SessionLocal() as db:
            for model in [StockIncome, StockBalanceSheet]:
                db.execute(delete(model).where(model.ts_code.in_(codes)))
            db.commit()
