from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.exceptions import AppException
from app.formulas.common import to_float
from app.models import (
    IndexDaily,
    SimulationPortfolio,
    SimulationPortfolioHolding,
    SimulationPortfolioNav,
    StockBasic,
    StockDaily,
    StockFactorScore,
)
from app.schemas import PortfolioHolding, PortfolioNavPoint, PortfolioResult, PortfolioSummary


BENCHMARK_NAMES = {
    "399006.SZ": "创业板指",
    "000688.SH": "科创50",
    "000300.SH": "沪深300",
}


class PortfolioService:
    """基于阶段5推荐结果生成模拟组合，并按每日收盘价计算组合收益。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def run_portfolio(
        self,
        score_date: str | date,
        end_date: str | date,
        stock_count: int,
        initial_cash: float,
        min_score: float = 65,
        benchmark_code: str = "399006.SZ",
    ) -> PortfolioResult:
        signal_date = self._parse_date(score_date)
        observe_end = self._parse_date(end_date)
        if signal_date >= observe_end:
            raise AppException("组合观察结束日期必须晚于评分日期。", code="INVALID_PORTFOLIO_DATE_RANGE", status_code=422)

        trading_dates = self._trading_dates(signal_date, observe_end)
        if len(trading_dates) < 2:
            raise AppException("观察区间内行情不足，至少需要评分日之后一个交易日。", code="PORTFOLIO_DATA_INSUFFICIENT", status_code=422)
        start_date = trading_dates[1]

        candidates = self._candidate_scores(signal_date, stock_count, min_score)
        if not candidates:
            raise AppException(
                f"{signal_date:%Y-%m-%d} 没有满足最低综合分 {min_score} 的推荐股票，无法生成模拟组合。",
                code="PORTFOLIO_CANDIDATES_EMPTY",
                status_code=422,
            )

        portfolio_id = self._portfolio_id(signal_date, observe_end, stock_count, initial_cash, min_score, benchmark_code)
        self._clear_portfolio(portfolio_id)

        holdings = self._build_holdings(candidates, start_date, initial_cash, observe_end, stock_count)
        if not holdings:
            raise AppException("候选股票在建仓日缺少可用价格，无法生成模拟组合。", code="PORTFOLIO_PRICE_MISSING", status_code=422)

        benchmark_returns, benchmark_source = self._benchmark_returns(benchmark_code, trading_dates[1:])
        nav_points = self._build_nav_points(holdings, trading_dates[1:], initial_cash, benchmark_returns)
        final_nav = nav_points[-1]
        cumulative_return = final_nav.portfolio_return
        benchmark_return = final_nav.benchmark_return
        excess_return = final_nav.excess_return
        max_drawdown = self._max_drawdown([item.portfolio_value for item in nav_points])
        benchmark_name = BENCHMARK_NAMES.get(benchmark_code, benchmark_code)
        conclusion = self._conclusion(cumulative_return, excess_return, max_drawdown, benchmark_name)

        result = PortfolioResult(
            portfolio_id=portfolio_id,
            name=f"{signal_date:%Y-%m-%d} 推荐模拟组合",
            score_date=signal_date.isoformat(),
            start_date=start_date.isoformat(),
            end_date=observe_end.isoformat(),
            stock_count=len(holdings),
            initial_cash=initial_cash,
            min_score=min_score,
            benchmark_code=benchmark_code,
            benchmark_name=benchmark_name,
            benchmark_source=benchmark_source,
            final_value=round(final_nav.portfolio_value, 4),
            cumulative_return=round(cumulative_return, 6),
            benchmark_return=round(benchmark_return, 6),
            excess_return=round(excess_return, 6),
            max_drawdown=round(max_drawdown, 6),
            conclusion=conclusion,
            holdings=holdings,
            nav=nav_points,
        )
        self._save_result(result)
        return result

    def list_portfolios(self, limit: int = 20) -> tuple[list[dict[str, object]], int]:
        statement = select(SimulationPortfolio).order_by(SimulationPortfolio.created_at.desc()).limit(limit)
        rows = list(self.db.scalars(statement))
        return [self._summary(row).model_dump(mode="json") for row in rows], len(rows)

    def get_portfolio(self, portfolio_id: str) -> PortfolioResult:
        row = self.db.get(SimulationPortfolio, portfolio_id)
        if row is None:
            raise AppException("未找到该模拟组合。", code="PORTFOLIO_NOT_FOUND", status_code=404)
        return self._result(row)

    def _candidate_scores(self, score_date: date, stock_count: int, min_score: float) -> list[tuple[StockFactorScore, StockBasic]]:
        # 股票数量由 stock_count 控制，最低分由 min_score 控制；不再额外按推荐等级过滤，
        # 否则用户把最低分调低到 C/D 区间时也无法扩大组合。
        candidate_limit = max(stock_count * 5, stock_count + 50)
        statement = (
            select(StockFactorScore, StockBasic)
            .join(StockBasic, StockBasic.ts_code == StockFactorScore.ts_code)
            .where(
                StockFactorScore.trade_date == score_date,
                StockFactorScore.final_score >= min_score,
            )
            .order_by(StockFactorScore.final_score.desc(), StockFactorScore.rank_in_universe.asc())
            .limit(candidate_limit)
        )
        return list(self.db.execute(statement).all())

    def _build_holdings(
        self,
        candidates: list[tuple[StockFactorScore, StockBasic]],
        buy_date: date,
        initial_cash: float,
        end_date: date,
        stock_count: int,
    ) -> list[PortfolioHolding]:
        priced: list[tuple[StockFactorScore, StockBasic, float, float]] = []
        for score, stock in candidates:
            buy_price = self._price(score.ts_code, buy_date, use_open=True)
            end_price = self._price(score.ts_code, end_date, use_open=False) or buy_price
            if buy_price and buy_price > 0:
                priced.append((score, stock, buy_price, end_price))
            if len(priced) >= stock_count:
                break
        if not priced:
            return []

        weight = 1 / len(priced)
        allocation = initial_cash * weight
        holdings: list[PortfolioHolding] = []
        for score, stock, buy_price, end_price in priced:
            quantity = allocation / buy_price
            market_value = quantity * end_price
            final_score = to_float(score.final_score) or 0.0
            reason = f"{score.trade_date:%Y-%m-%d} 因子评分入选，等级 {score.recommendation_level or '-'}，综合分 {round(final_score, 2)}"
            holdings.append(
                PortfolioHolding(
                    ts_code=score.ts_code,
                    name=stock.name or "",
                    industry=stock.industry or "未分类",
                    market=stock.market or "",
                    score=round(final_score, 4),
                    recommendation_level=score.recommendation_level or "",
                    weight=round(weight, 6),
                    quantity=round(quantity, 4),
                    buy_price=round(buy_price, 4),
                    current_price=round(end_price, 4),
                    market_value=round(market_value, 4),
                    return_rate=round(end_price / buy_price - 1, 6),
                    reason=reason,
                )
            )
        return holdings

    def _build_nav_points(
        self,
        holdings: list[PortfolioHolding],
        trading_dates: list[date],
        initial_cash: float,
        benchmark_returns: dict[date, float],
    ) -> list[PortfolioNavPoint]:
        nav: list[PortfolioNavPoint] = []
        for current_date in trading_dates:
            value = 0.0
            for holding in holdings:
                current_price = self._price(holding.ts_code, current_date, use_open=False) or holding.buy_price
                value += holding.quantity * current_price
            portfolio_return = value / initial_cash - 1
            benchmark_return = benchmark_returns.get(current_date, 0.0)
            nav.append(
                PortfolioNavPoint(
                    trade_date=current_date.isoformat(),
                    portfolio_value=round(value, 4),
                    portfolio_return=round(portfolio_return, 6),
                    benchmark_return=round(benchmark_return, 6),
                    excess_return=round(portfolio_return - benchmark_return, 6),
                )
            )
        return nav

    def _benchmark_returns(self, benchmark_code: str, trading_dates: list[date]) -> tuple[dict[date, float], str]:
        index_returns = self._index_returns(benchmark_code, trading_dates)
        if index_returns:
            return index_returns, "index"
        return self._pool_equal_weight_returns(trading_dates), "pool_equal_weight"

    def _index_returns(self, benchmark_code: str, trading_dates: list[date]) -> dict[date, float]:
        rows = self.db.execute(
            select(IndexDaily.trade_date, IndexDaily.close_price)
            .where(IndexDaily.index_code == benchmark_code, IndexDaily.trade_date.in_(trading_dates))
            .order_by(IndexDaily.trade_date)
        ).all()
        prices = {row_date: to_float(close) for row_date, close in rows if to_float(close)}
        if not prices or trading_dates[0] not in prices:
            # 兼容指数行情暂时采到 dwd_stock_daily 的情况。
            rows = self.db.execute(
                select(StockDaily.trade_date, StockDaily.close_price)
                .where(StockDaily.ts_code == benchmark_code, StockDaily.trade_date.in_(trading_dates))
                .order_by(StockDaily.trade_date)
            ).all()
            prices = {row_date: to_float(close) for row_date, close in rows if to_float(close)}
        start_price = prices.get(trading_dates[0])
        if not start_price:
            return {}
        return {day: (price / start_price - 1) for day, price in prices.items() if price}

    def _pool_equal_weight_returns(self, trading_dates: list[date]) -> dict[date, float]:
        start_date = trading_dates[0]
        start_rows = self.db.execute(select(StockDaily.ts_code, StockDaily.close_price).where(StockDaily.trade_date == start_date)).all()
        start_prices = {code: to_float(close) for code, close in start_rows if to_float(close)}
        if not start_prices:
            return {day: 0.0 for day in trading_dates}
        rows = self.db.execute(
            select(StockDaily.ts_code, StockDaily.trade_date, StockDaily.close_price)
            .where(StockDaily.ts_code.in_(start_prices), StockDaily.trade_date.in_(trading_dates))
            .order_by(StockDaily.trade_date)
        ).all()
        grouped: dict[date, list[float]] = {day: [] for day in trading_dates}
        for code, row_date, close in rows:
            start_price = start_prices.get(code)
            current_price = to_float(close)
            if start_price and current_price:
                grouped.setdefault(row_date, []).append(current_price / start_price - 1)
        return {day: (sum(values) / len(values) if values else 0.0) for day, values in grouped.items()}

    def _save_result(self, result: PortfolioResult) -> None:
        portfolio = SimulationPortfolio(
            portfolio_id=result.portfolio_id,
            name=result.name,
            score_date=self._parse_date(result.score_date),
            start_date=self._parse_date(result.start_date),
            end_date=self._parse_date(result.end_date),
            stock_count=result.stock_count,
            initial_cash=Decimal(str(round(result.initial_cash, 4))),
            min_score=Decimal(str(round(result.min_score, 4))),
            benchmark_code=result.benchmark_code,
            benchmark_name=result.benchmark_name,
            benchmark_source=result.benchmark_source,
            final_value=Decimal(str(round(result.final_value, 4))),
            cumulative_return=Decimal(str(round(result.cumulative_return, 6))),
            benchmark_return=Decimal(str(round(result.benchmark_return, 6))),
            excess_return=Decimal(str(round(result.excess_return, 6))),
            max_drawdown=Decimal(str(round(result.max_drawdown, 6))),
            conclusion=result.conclusion,
        )
        self.db.add(portfolio)
        for holding in result.holdings:
            self.db.add(
                SimulationPortfolioHolding(
                    portfolio_id=result.portfolio_id,
                    ts_code=holding.ts_code,
                    name=holding.name,
                    industry=holding.industry,
                    market=holding.market,
                    score=Decimal(str(round(holding.score, 4))),
                    recommendation_level=holding.recommendation_level,
                    weight=Decimal(str(round(holding.weight, 8))),
                    quantity=Decimal(str(round(holding.quantity, 4))),
                    buy_price=Decimal(str(round(holding.buy_price, 4))),
                    current_price=Decimal(str(round(holding.current_price, 4))),
                    market_value=Decimal(str(round(holding.market_value, 4))),
                    return_rate=Decimal(str(round(holding.return_rate, 6))),
                    reason=holding.reason,
                )
            )
        for item in result.nav:
            self.db.add(
                SimulationPortfolioNav(
                    portfolio_id=result.portfolio_id,
                    trade_date=self._parse_date(item.trade_date),
                    portfolio_value=Decimal(str(round(item.portfolio_value, 4))),
                    portfolio_return=Decimal(str(round(item.portfolio_return, 6))),
                    benchmark_return=Decimal(str(round(item.benchmark_return, 6))),
                    excess_return=Decimal(str(round(item.excess_return, 6))),
                )
            )
        self.db.commit()

    def _result(self, row: SimulationPortfolio) -> PortfolioResult:
        holdings = [
            PortfolioHolding(
                ts_code=item.ts_code,
                name=item.name or "",
                industry=item.industry or "",
                market=item.market or "",
                score=float(item.score or 0),
                recommendation_level=item.recommendation_level or "",
                weight=float(item.weight or 0),
                quantity=float(item.quantity or 0),
                buy_price=float(item.buy_price or 0),
                current_price=float(item.current_price or 0),
                market_value=float(item.market_value or 0),
                return_rate=float(item.return_rate or 0),
                reason=item.reason or "",
            )
            for item in self.db.scalars(
                select(SimulationPortfolioHolding).where(SimulationPortfolioHolding.portfolio_id == row.portfolio_id).order_by(SimulationPortfolioHolding.score.desc())
            )
        ]
        nav = [
            PortfolioNavPoint(
                trade_date=item.trade_date.isoformat(),
                portfolio_value=float(item.portfolio_value or 0),
                portfolio_return=float(item.portfolio_return or 0),
                benchmark_return=float(item.benchmark_return or 0),
                excess_return=float(item.excess_return or 0),
            )
            for item in self.db.scalars(
                select(SimulationPortfolioNav).where(SimulationPortfolioNav.portfolio_id == row.portfolio_id).order_by(SimulationPortfolioNav.trade_date)
            )
        ]
        return PortfolioResult(
            portfolio_id=row.portfolio_id,
            name=row.name,
            score_date=row.score_date.isoformat(),
            start_date=row.start_date.isoformat(),
            end_date=row.end_date.isoformat(),
            stock_count=row.stock_count,
            initial_cash=float(row.initial_cash or 0),
            min_score=float(row.min_score or 0),
            benchmark_code=row.benchmark_code or "",
            benchmark_name=row.benchmark_name or "",
            benchmark_source=row.benchmark_source or "",
            final_value=float(row.final_value or 0),
            cumulative_return=float(row.cumulative_return or 0),
            benchmark_return=float(row.benchmark_return or 0),
            excess_return=float(row.excess_return or 0),
            max_drawdown=float(row.max_drawdown or 0),
            conclusion=row.conclusion or "",
            holdings=holdings,
            nav=nav,
        )

    @staticmethod
    def _summary(row: SimulationPortfolio) -> PortfolioSummary:
        return PortfolioSummary(
            portfolio_id=row.portfolio_id,
            name=row.name,
            score_date=row.score_date.isoformat(),
            start_date=row.start_date.isoformat(),
            end_date=row.end_date.isoformat(),
            stock_count=row.stock_count,
            initial_cash=float(row.initial_cash or 0),
            final_value=float(row.final_value or 0),
            cumulative_return=float(row.cumulative_return or 0),
            benchmark_return=float(row.benchmark_return or 0),
            excess_return=float(row.excess_return or 0),
            max_drawdown=float(row.max_drawdown or 0),
            benchmark_name=row.benchmark_name or "",
            benchmark_source=row.benchmark_source or "",
            conclusion=row.conclusion or "",
            created_at=row.created_at.isoformat(),
        )

    def _clear_portfolio(self, portfolio_id: str) -> None:
        self.db.execute(delete(SimulationPortfolioNav).where(SimulationPortfolioNav.portfolio_id == portfolio_id))
        self.db.execute(delete(SimulationPortfolioHolding).where(SimulationPortfolioHolding.portfolio_id == portfolio_id))
        self.db.execute(delete(SimulationPortfolio).where(SimulationPortfolio.portfolio_id == portfolio_id))
        self.db.commit()

    def _trading_dates(self, start_date: date, end_date: date) -> list[date]:
        return list(self.db.scalars(select(StockDaily.trade_date).where(StockDaily.trade_date >= start_date, StockDaily.trade_date <= end_date).distinct().order_by(StockDaily.trade_date)))

    def _price(self, ts_code: str, trade_date: date, use_open: bool) -> float | None:
        column = StockDaily.open_price if use_open else StockDaily.close_price
        value = to_float(self.db.scalar(select(column).where(StockDaily.ts_code == ts_code, StockDaily.trade_date == trade_date)))
        if value:
            return value
        fallback = StockDaily.close_price if use_open else StockDaily.open_price
        return to_float(self.db.scalar(select(fallback).where(StockDaily.ts_code == ts_code, StockDaily.trade_date == trade_date)))

    @staticmethod
    def _portfolio_id(score_date: date, end_date: date, stock_count: int, initial_cash: float, min_score: float, benchmark_code: str) -> str:
        score_key = str(min_score).replace(".", "p")
        benchmark_key = benchmark_code.replace(".", "")
        return f"portfolio-{score_date:%Y%m%d}-{end_date:%Y%m%d}-top{stock_count}-cash{int(initial_cash)}-score{score_key}-{benchmark_key}"

    @staticmethod
    def _max_drawdown(values: list[float]) -> float:
        if not values:
            return 0.0
        peak = values[0]
        max_drawdown = 0.0
        for value in values:
            peak = max(peak, value)
            if peak:
                max_drawdown = max(max_drawdown, (peak - value) / peak)
        return -max_drawdown

    @staticmethod
    def _conclusion(cumulative_return: float, excess_return: float, max_drawdown: float, benchmark_name: str) -> str:
        if cumulative_return > 0 and excess_return > 0:
            return f"模拟组合取得正收益并跑赢{benchmark_name}，该评分日推荐组合表现较好。"
        if cumulative_return > 0:
            return f"模拟组合取得正收益但未跑赢{benchmark_name}，需要观察行业暴露和持仓分散度。"
        if excess_return > 0:
            return f"模拟组合为负收益但相对{benchmark_name}有超额，说明区间大盘环境较弱。"
        return f"模拟组合未跑赢{benchmark_name}，建议复核该评分日推荐股票、最低分和风险扣分。"

    @staticmethod
    def _parse_date(value: str | date) -> date:
        if isinstance(value, date):
            return value
        return datetime.strptime(value.replace("-", ""), "%Y%m%d").date()
