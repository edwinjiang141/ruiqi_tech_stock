from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, select

from app.database import SessionLocal
from app.exceptions import AppException
from app.models import SimulationPosition, SimulationReview, SimulationTrade, StockBasic, StockDaily, StockFactorScore
from app.services import SimulationService


def test_simulation_uses_stage5_scores_and_cash_scale() -> None:
    codes = ["300801.SZ", "300802.SZ", "300803.SZ"]
    strategy_prefix = "review-hold-20260501-20260512-top20-cash1000000-score65p0"
    start = date(2026, 5, 1)
    try:
        with SessionLocal() as db:
            for model in [SimulationTrade, SimulationPosition, SimulationReview]:
                db.execute(delete(model).where(model.strategy_version == strategy_prefix))
            db.execute(delete(StockFactorScore).where(StockFactorScore.ts_code.in_(codes)))
            db.execute(delete(StockDaily).where(StockDaily.ts_code.in_(codes)))
            db.execute(delete(StockBasic).where(StockBasic.ts_code.in_(codes)))
            db.commit()

            for index, code in enumerate(codes):
                db.add(StockBasic(ts_code=code, name=f"测试股票{index + 1}", industry="软件服务", market="创业板"))
                db.add(
                    StockFactorScore(
                        ts_code=code,
                        trade_date=start,
                        final_score=Decimal(str(90 - index * 5)),
                        recommendation_level="A",
                        rank_in_universe=index + 1,
                        formula_version="v1.2.0",
                    )
                )
                for day in range(0, 12):
                    price = Decimal(str(10 + index + day * (0.2 if code != "300803.SZ" else -0.1)))
                    db.add(
                        StockDaily(
                            ts_code=code,
                            trade_date=start + timedelta(days=day),
                            open_price=price,
                            close_price=price + Decimal("0.1"),
                            amount=Decimal("100000"),
                        )
                    )
            db.commit()

            result = SimulationService(db).run_review("20260501", "20260512", stock_count=20, initial_cash=1000000, min_score=65.0)
            trades = list(db.scalars(select(SimulationTrade).where(SimulationTrade.strategy_version == result.strategy_version)))
            positions = list(db.scalars(select(SimulationPosition).where(SimulationPosition.strategy_version == result.strategy_version)))
            history_items, history_total = SimulationService(db).list_recent_runs(limit=5)
            saved_result = SimulationService(db).get_review(result.strategy_version)

        assert result.stock_count == 20
        assert result.initial_cash == 1000000
        assert len(result.holdings) <= 20
        assert {holding.ts_code for holding in result.holdings} == {"300801.SZ", "300802.SZ", "300803.SZ"}
        assert {trade.side for trade in trades} == {"buy"}
        assert all(holding.buy_date for holding in result.holdings)
        assert all(holding.name for holding in result.holdings)
        assert any(metric.name == "累计收益率" for metric in result.metrics)
        assert trades
        assert positions
        assert history_total >= 1
        assert any(item["strategy_version"] == result.strategy_version for item in history_items)
        assert saved_result.conclusion == result.conclusion
    finally:
        with SessionLocal() as db:
            for model in [SimulationTrade, SimulationPosition, SimulationReview]:
                db.execute(delete(model).where(model.strategy_version == strategy_prefix))
            db.execute(delete(StockFactorScore).where(StockFactorScore.ts_code.in_(codes)))
            db.execute(delete(StockDaily).where(StockDaily.ts_code.in_(codes)))
            db.execute(delete(StockBasic).where(StockBasic.ts_code.in_(codes)))
            db.commit()


def test_simulation_requires_start_date_scores() -> None:
    with SessionLocal() as db:
        service = SimulationService(db)
        try:
            service.run_review("20990101", "20990102", stock_count=20, initial_cash=100000, min_score=60)
        except AppException as exc:
            assert exc.code == "SIMULATION_SIGNAL_MISSING"
        else:
            raise AssertionError("缺少阶段5评分时应拒绝复盘")


def test_rebalance_review_records_cash_trades_and_holdings() -> None:
    codes = ["300811.SZ", "300812.SZ"]
    strategy_prefix = "review-rebalance-20260601-20260612-top1-cash100000-score65p0"
    start = date(2026, 6, 1)
    second_signal = date(2026, 6, 5)
    try:
        with SessionLocal() as db:
            for model in [SimulationTrade, SimulationPosition, SimulationReview]:
                db.execute(delete(model).where(model.strategy_version == strategy_prefix))
            db.execute(delete(StockFactorScore).where(StockFactorScore.ts_code.in_(codes)))
            db.execute(delete(StockDaily).where(StockDaily.ts_code.in_(codes)))
            db.execute(delete(StockBasic).where(StockBasic.ts_code.in_(codes)))
            db.commit()

            for index, code in enumerate(codes):
                db.add(StockBasic(ts_code=code, name=f"调仓股票{index + 1}", industry="电子", market="科创板"))
            db.add(
                StockFactorScore(
                    ts_code=codes[0],
                    trade_date=start,
                    final_score=Decimal("90"),
                    recommendation_level="A",
                    rank_in_universe=1,
                    formula_version="v1.2.0",
                )
            )
            db.add(
                StockFactorScore(
                    ts_code=codes[1],
                    trade_date=second_signal,
                    final_score=Decimal("92"),
                    recommendation_level="A",
                    rank_in_universe=1,
                    formula_version="v1.2.0",
                )
            )
            for index, code in enumerate(codes):
                for day in range(0, 12):
                    price = Decimal(str(10 + index + day * 0.5))
                    db.add(
                        StockDaily(
                            ts_code=code,
                            trade_date=start + timedelta(days=day),
                            open_price=price,
                            close_price=price + Decimal("0.2"),
                            amount=Decimal("100000"),
                        )
                    )
            db.commit()

            result = SimulationService(db).run_review("20260601", "20260612", stock_count=1, initial_cash=100000, min_score=65.0, review_mode="rebalance")
            saved_result = SimulationService(db).get_review(result.strategy_version)

        assert len(result.rebalances) >= 2
        assert result.rebalances[0].buy_trades
        assert any(step.sell_trades for step in result.rebalances)
        assert any(step.before_holdings for step in result.rebalances[1:])
        assert result.rebalances[0].buy_trades[0].name
        assert saved_result.rebalances[0].after_total_value == result.rebalances[0].after_total_value
    finally:
        with SessionLocal() as db:
            for model in [SimulationTrade, SimulationPosition, SimulationReview]:
                db.execute(delete(model).where(model.strategy_version == strategy_prefix))
            db.execute(delete(StockFactorScore).where(StockFactorScore.ts_code.in_(codes)))
            db.execute(delete(StockDaily).where(StockDaily.ts_code.in_(codes)))
            db.execute(delete(StockBasic).where(StockBasic.ts_code.in_(codes)))
            db.commit()
