from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete

from app.database import SessionLocal
from app.models import SimulationPortfolio, SimulationPortfolioHolding, SimulationPortfolioNav, StockBasic, StockDaily, StockFactorScore
from app.services import PortfolioService


def test_portfolio_tracks_daily_returns_and_history() -> None:
    codes = ["300821.SZ", "300822.SZ", "300823.SZ"]
    score_date = date(2026, 7, 1)
    portfolio_id = "portfolio-20260701-20260705-top2-cash100000-score65-399006SZ"
    expanded_portfolio_id = "portfolio-20260701-20260705-top3-cash100000-score60-399006SZ"
    try:
        with SessionLocal() as db:
            db.execute(delete(SimulationPortfolioNav).where(SimulationPortfolioNav.portfolio_id.in_([portfolio_id, expanded_portfolio_id])))
            db.execute(delete(SimulationPortfolioHolding).where(SimulationPortfolioHolding.portfolio_id.in_([portfolio_id, expanded_portfolio_id])))
            db.execute(delete(SimulationPortfolio).where(SimulationPortfolio.portfolio_id.in_([portfolio_id, expanded_portfolio_id])))
            db.execute(delete(StockFactorScore).where(StockFactorScore.ts_code.in_(codes)))
            db.execute(delete(StockDaily).where(StockDaily.ts_code.in_(codes)))
            db.execute(delete(StockBasic).where(StockBasic.ts_code.in_(codes)))
            db.commit()

            for index, code in enumerate(codes):
                db.add(StockBasic(ts_code=code, name=f"组合股票{index + 1}", industry="软件服务", market="创业板", list_status="L"))
                db.add(
                    StockFactorScore(
                        ts_code=code,
                        trade_date=score_date,
                        final_score=Decimal(str(90 - index * 15)),
                        recommendation_level="A" if index < 2 else "C",
                        rank_in_universe=index + 1,
                        formula_version="v1.2.0",
                    )
                )
                for day in range(0, 5):
                    price = Decimal(str(10 + index + day))
                    db.add(
                        StockDaily(
                            ts_code=code,
                            trade_date=score_date + timedelta(days=day),
                            open_price=price,
                            close_price=price + Decimal("0.5"),
                            amount=Decimal("100000"),
                        )
                    )
            db.commit()

            service = PortfolioService(db)
            result = service.run_portfolio("20260701", "20260705", stock_count=2, initial_cash=100000, min_score=65)
            expanded_result = service.run_portfolio("20260701", "20260705", stock_count=3, initial_cash=100000, min_score=60)
            history_items, history_total = service.list_portfolios(limit=5)
            saved_result = service.get_portfolio(result.portfolio_id)

        assert result.stock_count == 2
        assert len(result.holdings) == 2
        assert expanded_result.stock_count == 3
        assert any(holding.recommendation_level == "C" for holding in expanded_result.holdings)
        assert len(result.nav) == 4
        assert result.cumulative_return > 0
        assert result.benchmark_source == "pool_equal_weight"
        assert history_total >= 1
        assert any(item["portfolio_id"] == result.portfolio_id for item in history_items)
        assert saved_result.nav[-1].portfolio_value == result.nav[-1].portfolio_value
    finally:
        with SessionLocal() as db:
            db.execute(delete(SimulationPortfolioNav).where(SimulationPortfolioNav.portfolio_id.in_([portfolio_id, expanded_portfolio_id])))
            db.execute(delete(SimulationPortfolioHolding).where(SimulationPortfolioHolding.portfolio_id.in_([portfolio_id, expanded_portfolio_id])))
            db.execute(delete(SimulationPortfolio).where(SimulationPortfolio.portfolio_id.in_([portfolio_id, expanded_portfolio_id])))
            db.execute(delete(StockFactorScore).where(StockFactorScore.ts_code.in_(codes)))
            db.execute(delete(StockDaily).where(StockDaily.ts_code.in_(codes)))
            db.execute(delete(StockBasic).where(StockBasic.ts_code.in_(codes)))
            db.commit()
