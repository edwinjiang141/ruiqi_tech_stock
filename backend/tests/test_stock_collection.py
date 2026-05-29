import pandas as pd
from sqlalchemy import delete, func, select

from app.database import SessionLocal
from app.models import StockBasic
from app.services import DataQualityService, StockPoolService


def test_stock_pool_upsert_and_quality_check() -> None:
    dataframe = pd.DataFrame(
        [
            {
                "ts_code": "300001.SZ",
                "symbol": "300001",
                "name": "阶段测试股票",
                "area": "广东",
                "industry": "软件服务",
                "market": "创业板",
                "exchange": "SZSE",
                "list_status": "L",
                "list_date": "20100101",
                "delist_date": None,
                "is_hs": "N",
            }
        ]
    )

    try:
        with SessionLocal() as db:
            db.execute(delete(StockBasic).where(StockBasic.ts_code == "300001.SZ"))
            db.commit()

            service = StockPoolService(db)
            changed_count = service.upsert_stock_basic(dataframe)
            repeat_count = service.upsert_stock_basic(dataframe)
            stocks, total = service.list_stocks(limit=10000)
            report = DataQualityService(db).check_stock_basic()
            duplicate_guard_count = db.scalar(select(func.count()).select_from(StockBasic).where(StockBasic.ts_code == "300001.SZ"))
    finally:
        with SessionLocal() as db:
            db.execute(delete(StockBasic).where(StockBasic.ts_code == "300001.SZ"))
            db.commit()

    assert changed_count == 1
    assert repeat_count == 1
    assert duplicate_guard_count == 1
    assert total >= 1
    assert any(stock.ts_code == "300001.SZ" for stock in stocks)
    assert report.passed is True


def test_stock_pool_large_batch_is_split_to_avoid_postgres_parameter_limit() -> None:
    dataframe = pd.DataFrame(
        [
            {
                "ts_code": f"399{i:03d}.SZ",
                "symbol": f"399{i:03d}",
                "name": f"批量测试股票{i}",
                "area": "广东",
                "industry": "软件服务",
                "market": "创业板",
                "exchange": "SZSE",
                "list_status": "L",
                "list_date": "20200101",
                "delist_date": None,
                "is_hs": "N",
            }
            for i in range(1100)
        ]
    )

    try:
        with SessionLocal() as db:
            db.execute(delete(StockBasic).where(StockBasic.ts_code.like("399%.SZ")))
            db.commit()

            changed_count = StockPoolService(db).upsert_stock_basic(dataframe)
            repeat_count = StockPoolService(db).upsert_stock_basic(dataframe)
            row_count = db.scalar(select(func.count()).select_from(StockBasic).where(StockBasic.ts_code.like("399%.SZ")))
    finally:
        with SessionLocal() as db:
            db.execute(delete(StockBasic).where(StockBasic.ts_code.like("399%.SZ")))
            db.commit()

    assert changed_count == 1100
    assert repeat_count == 1100
    assert row_count == 1100
