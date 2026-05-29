import pandas as pd
from sqlalchemy import delete, func, select

from app.database import SessionLocal
from app.exceptions import AppException
from app.models import StockAdjFactor, StockCashflow, StockDaily, StockDailyBasic, StockFinancialIndicator, StockMoneyflow
from app.services import MarketDataService


def test_market_financial_and_moneyflow_upserts() -> None:
    try:
        with SessionLocal() as db:
            for model in [StockDaily, StockAdjFactor, StockDailyBasic, StockFinancialIndicator, StockCashflow, StockMoneyflow]:
                db.execute(delete(model).where(model.ts_code == "300001.SZ"))
            db.commit()

            service = MarketDataService(db)

            daily_count = service.upsert_daily(
                pd.DataFrame(
                    [
                        {
                            "ts_code": "300001.SZ",
                            "trade_date": "20260524",
                            "open": 10.0,
                            "high": 11.0,
                            "low": 9.8,
                            "close": 10.5,
                            "pre_close": 10.0,
                            "change": 0.5,
                            "pct_chg": 5.0,
                            "vol": 1000.0,
                            "amount": 10500.0,
                        }
                    ]
                )
            )
            adj_count = service.upsert_adj_factor(pd.DataFrame([{"ts_code": "300001.SZ", "trade_date": "20260524", "adj_factor": 1.0}]))
            basic_count = service.upsert_daily_basic(
                pd.DataFrame([{"ts_code": "300001.SZ", "trade_date": "20260524", "close": 10.5, "pe": 20.0, "pb": 3.0}])
            )
            indicator_count = service.upsert_financial_indicator(
                pd.DataFrame(
                    [
                        {
                            "ts_code": "300001.SZ",
                            "ann_date": "20260430",
                            "end_date": "20260331",
                            "roe": 10.0,
                            "revenue_yoy": 12.0,
                        }
                    ]
                )
            )
            cashflow_count = service.upsert_cashflow(
                pd.DataFrame([{"ts_code": "300001.SZ", "ann_date": "20260430", "end_date": "20260331", "net_profit": 100.0}])
            )
            moneyflow_count = service.upsert_moneyflow(
                pd.DataFrame([{"ts_code": "300001.SZ", "trade_date": "20260524", "net_mf_amount": 88.0}])
            )

            service.upsert_daily(
                pd.DataFrame([{"ts_code": "300001.SZ", "trade_date": "20260524", "open": 10.1, "close": 10.6}])
            )
            service.upsert_adj_factor(pd.DataFrame([{"ts_code": "300001.SZ", "trade_date": "20260524", "adj_factor": 1.1}]))
            service.upsert_daily_basic(pd.DataFrame([{"ts_code": "300001.SZ", "trade_date": "20260524", "close": 10.6, "pe": 21.0}]))
            service.upsert_financial_indicator(pd.DataFrame([{"ts_code": "300001.SZ", "end_date": "20260331", "roe": 11.0}]))
            service.upsert_cashflow(pd.DataFrame([{"ts_code": "300001.SZ", "end_date": "20260331", "net_profit": 101.0}]))
            service.upsert_moneyflow(pd.DataFrame([{"ts_code": "300001.SZ", "trade_date": "20260524", "net_mf_amount": 89.0}]))

            row_counts = {
                model.__tablename__: db.scalar(select(func.count()).select_from(model).where(model.ts_code == "300001.SZ"))
                for model in [StockDaily, StockAdjFactor, StockDailyBasic, StockFinancialIndicator, StockCashflow, StockMoneyflow]
            }
    finally:
        with SessionLocal() as db:
            for model in [StockDaily, StockAdjFactor, StockDailyBasic, StockFinancialIndicator, StockCashflow, StockMoneyflow]:
                db.execute(delete(model).where(model.ts_code == "300001.SZ"))
            db.commit()

    assert daily_count == 1
    assert adj_count == 1
    assert basic_count == 1
    assert indicator_count == 1
    assert cashflow_count == 1
    assert moneyflow_count == 1
    assert row_counts == {
        "dwd_stock_daily": 1,
        "dwd_stock_adj_factor": 1,
        "dwd_stock_daily_basic": 1,
        "dwd_stock_financial_indicator": 1,
        "dwd_stock_cashflow": 1,
        "dwd_stock_moneyflow": 1,
    }


def test_financial_collection_stops_calling_source_after_daily_quota(monkeypatch) -> None:
    pool_codes = ["300905.SZ", "300906.SZ", "300907.SZ"]
    try:
        with SessionLocal() as db:
            for model in [StockFinancialIndicator, StockCashflow]:
                db.execute(delete(model).where(model.ts_code.in_(pool_codes)))
            db.commit()

            fake_tushare = DailyQuotaFinancialTushareService()
            service = MarketDataService(db, tushare_service=fake_tushare)
            monkeypatch.setattr(service, "_stock_pool_codes", lambda: pool_codes)
            result = service.collect_financial("20260331")

            indicator_count = db.scalar(select(func.count()).select_from(StockFinancialIndicator).where(StockFinancialIndicator.ts_code.in_(pool_codes)))
            cashflow_count = db.scalar(select(func.count()).select_from(StockCashflow).where(StockCashflow.ts_code.in_(pool_codes)))

        assert result.status == "warning"
        assert indicator_count == 3
        assert cashflow_count == 0
        assert len(fake_tushare.indicator_calls) == 3
        assert len(fake_tushare.cashflow_calls) == 1
    finally:
        with SessionLocal() as db:
            for model in [StockFinancialIndicator, StockCashflow]:
                db.execute(delete(model).where(model.ts_code.in_(pool_codes)))
            db.commit()


def test_financial_collection_cleans_dirty_numeric_values(monkeypatch) -> None:
    pool_codes = ["300903.SZ"]
    try:
        with SessionLocal() as db:
            for model in [StockFinancialIndicator, StockCashflow]:
                db.execute(delete(model).where(model.ts_code.in_(pool_codes)))
            db.commit()

            service = MarketDataService(db, tushare_service=DirtyNumericFinancialTushareService())
            monkeypatch.setattr(service, "_stock_pool_codes", lambda: pool_codes)
            result = service.collect_financial("20260331")

            indicator = db.scalar(select(StockFinancialIndicator).where(StockFinancialIndicator.ts_code == "300903.SZ"))
            cashflow = db.scalar(select(StockCashflow).where(StockCashflow.ts_code == "300903.SZ"))

        assert result.status == "success"
        assert result.fetched_count == 2
        assert indicator is not None
        assert indicator.roe is None
        assert indicator.roa is None
        assert str(indicator.revenue_yoy) == "12.500000"
        assert cashflow is not None
        assert cashflow.net_profit is None
        assert str(cashflow.n_cashflow_act) == "100.2500"
    finally:
        with SessionLocal() as db:
            for model in [StockFinancialIndicator, StockCashflow]:
                db.execute(delete(model).where(model.ts_code.in_(pool_codes)))
            db.commit()


def test_financial_indicator_upsert_deduplicates_conflict_keys() -> None:
    ts_code = "300904.SZ"
    try:
        with SessionLocal() as db:
            db.execute(delete(StockFinancialIndicator).where(StockFinancialIndicator.ts_code == ts_code))
            db.commit()

            count = MarketDataService(db).upsert_financial_indicator(
                pd.DataFrame(
                    [
                        {"ts_code": ts_code, "ann_date": "20230424", "end_date": "20230331", "roe": 1.0},
                        {"ts_code": ts_code, "ann_date": "20230424", "end_date": "20230331", "roe": 2.0},
                    ]
                )
            )
            row = db.scalar(select(StockFinancialIndicator).where(StockFinancialIndicator.ts_code == ts_code))

        assert count == 1
        assert row is not None
        assert str(row.roe) == "2.000000"
    finally:
        with SessionLocal() as db:
            db.execute(delete(StockFinancialIndicator).where(StockFinancialIndicator.ts_code == ts_code))
            db.commit()


class FakeFinancialTushareService:
    def __init__(self) -> None:
        self.indicator_calls: list[tuple[str, str]] = []
        self.cashflow_calls: list[tuple[str, str]] = []

    def fina_indicator(self, ts_code: str, period: str) -> pd.DataFrame:
        self.indicator_calls.append((ts_code, period))
        code_index = int(ts_code[:3]) if ts_code[:3].isdigit() else 1
        return pd.DataFrame(
            [
                {
                    "ts_code": ts_code,
                    "ann_date": "20260430",
                    "end_date": period,
                    "roe": float(code_index),
                    "revenue_yoy": float(code_index + 1),
                }
            ]
        )

    def cashflow(self, ts_code: str, period: str) -> pd.DataFrame:
        self.cashflow_calls.append((ts_code, period))
        code_index = int(ts_code[:3]) if ts_code[:3].isdigit() else 1
        return pd.DataFrame(
            [
                {
                    "ts_code": ts_code,
                    "ann_date": "20260430",
                    "end_date": period,
                    "net_profit": float(code_index),
                    "n_cashflow_act": float(code_index - 1),
                }
            ]
        )


def test_financial_collection_uses_stock_pool_codes(monkeypatch) -> None:
    pool_codes = ["300901.SZ", "688901.SH", "600901.SH"]
    try:
        with SessionLocal() as db:
            for model in [StockFinancialIndicator, StockCashflow]:
                db.execute(delete(model).where(model.ts_code.in_(pool_codes)))
            db.commit()

            fake_tushare = FakeFinancialTushareService()
            service = MarketDataService(db, tushare_service=fake_tushare)
            monkeypatch.setattr(service, "_stock_pool_codes", lambda: pool_codes)
            result = service.collect_financial("20260331")

            indicator_count = db.scalar(select(func.count()).select_from(StockFinancialIndicator).where(StockFinancialIndicator.ts_code.in_(pool_codes)))
            cashflow_count = db.scalar(select(func.count()).select_from(StockCashflow).where(StockCashflow.ts_code.in_(pool_codes)))

        assert result.fetched_count == 6
        assert sorted(fake_tushare.indicator_calls) == sorted((code, "20260331") for code in pool_codes)
        assert sorted(fake_tushare.cashflow_calls) == sorted((code, "20260331") for code in pool_codes)
        assert indicator_count == 3
        assert cashflow_count == 3
    finally:
        with SessionLocal() as db:
            for model in [StockFinancialIndicator, StockCashflow]:
                db.execute(delete(model).where(model.ts_code.in_(pool_codes)))
            db.commit()


def test_financial_collection_only_backfills_missing_rows(monkeypatch) -> None:
    pool_codes = ["300908.SZ", "300909.SZ", "300910.SZ"]
    try:
        with SessionLocal() as db:
            for model in [StockFinancialIndicator, StockCashflow]:
                db.execute(delete(model).where(model.ts_code.in_(pool_codes)))
            db.commit()

            service = MarketDataService(db)
            service.upsert_financial_indicator(pd.DataFrame([{"ts_code": "300908.SZ", "ann_date": "20260430", "end_date": "20260331", "roe": 1.0}]))
            service.upsert_cashflow(pd.DataFrame([{"ts_code": "300909.SZ", "ann_date": "20260430", "end_date": "20260331", "net_profit": 100.0}]))

            fake_tushare = FakeFinancialTushareService()
            service = MarketDataService(db, tushare_service=fake_tushare)
            monkeypatch.setattr(service, "_stock_pool_codes", lambda: pool_codes)
            result = service.collect_financial("20260331")

            indicator_count = db.scalar(select(func.count()).select_from(StockFinancialIndicator).where(StockFinancialIndicator.ts_code.in_(pool_codes)))
            cashflow_count = db.scalar(select(func.count()).select_from(StockCashflow).where(StockCashflow.ts_code.in_(pool_codes)))

        assert result.fetched_count == 4
        assert sorted(fake_tushare.indicator_calls) == [("300909.SZ", "20260331"), ("300910.SZ", "20260331")]
        assert sorted(fake_tushare.cashflow_calls) == [("300908.SZ", "20260331"), ("300910.SZ", "20260331")]
        assert indicator_count == 3
        assert cashflow_count == 3
    finally:
        with SessionLocal() as db:
            for model in [StockFinancialIndicator, StockCashflow]:
                db.execute(delete(model).where(model.ts_code.in_(pool_codes)))
            db.commit()


class PartialFailureFinancialTushareService:
    def fina_indicator(self, ts_code: str, period: str) -> pd.DataFrame:
        if ts_code == "688902.SH":
            return pd.DataFrame([{"ts_code": "000000.SZ", "ann_date": "20260430", "end_date": period, "roe": 10.0}])
        return pd.DataFrame([{"ts_code": ts_code, "ann_date": "20260430", "end_date": period, "roe": 11.0}])

    def cashflow(self, ts_code: str, period: str) -> pd.DataFrame:
        if ts_code == "600902.SH":
            raise AppException("模拟接口频率超限后仍失败", code="TUSHARE_CALL_FAILED", status_code=502)
        return pd.DataFrame([{"ts_code": ts_code, "ann_date": "20260430", "end_date": period, "net_profit": 101.0}])


class DirtyNumericFinancialTushareService:
    def fina_indicator(self, ts_code: str, period: str) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "ts_code": ts_code,
                    "ann_date": "20260430",
                    "end_date": period,
                    "roe": "--",
                    "roa": "",
                    "grossprofit_margin": "nan",
                    "revenue_yoy": "12.5",
                }
            ]
        )

    def cashflow(self, ts_code: str, period: str) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "ts_code": ts_code,
                    "ann_date": "20260430",
                    "end_date": period,
                    "net_profit": "--",
                    "n_cashflow_act": "100.25",
                }
            ]
        )


class DailyQuotaFinancialTushareService:
    def __init__(self) -> None:
        self.indicator_calls: list[tuple[str, str]] = []
        self.cashflow_calls: list[tuple[str, str]] = []

    def fina_indicator(self, ts_code: str, period: str) -> pd.DataFrame:
        self.indicator_calls.append((ts_code, period))
        return pd.DataFrame([{"ts_code": ts_code, "ann_date": "20260430", "end_date": period, "roe": 11.0}])

    def cashflow(self, ts_code: str, period: str) -> pd.DataFrame:
        self.cashflow_calls.append((ts_code, period))
        raise AppException("Tushare 接口 cashflow 日调用额度已用尽，请明天额度恢复后继续补采。", code="TUSHARE_DAILY_QUOTA_EXCEEDED", status_code=429)


def test_financial_collection_skips_mismatched_and_failed_stock(monkeypatch) -> None:
    pool_codes = ["300902.SZ", "688902.SH", "600902.SH"]
    try:
        with SessionLocal() as db:
            for model in [StockFinancialIndicator, StockCashflow]:
                db.execute(delete(model).where(model.ts_code.in_(pool_codes)))
            db.commit()

            service = MarketDataService(db, tushare_service=PartialFailureFinancialTushareService())
            monkeypatch.setattr(service, "_stock_pool_codes", lambda: pool_codes)
            result = service.collect_financial("20260331")

            indicator_count = db.scalar(select(func.count()).select_from(StockFinancialIndicator).where(StockFinancialIndicator.ts_code.in_(pool_codes)))
            cashflow_count = db.scalar(select(func.count()).select_from(StockCashflow).where(StockCashflow.ts_code.in_(pool_codes)))

        assert result.status == "warning"
        assert result.fetched_count == 4
        assert indicator_count == 2
        assert cashflow_count == 2
    finally:
        with SessionLocal() as db:
            for model in [StockFinancialIndicator, StockCashflow]:
                db.execute(delete(model).where(model.ts_code.in_(pool_codes)))
            db.commit()
