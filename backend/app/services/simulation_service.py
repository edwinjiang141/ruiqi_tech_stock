from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import pandas as pd
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.exceptions import AppException
from app.formulas.common import to_float
from app.models import SimulationPosition, SimulationReview, SimulationTrade, StockBasic, StockDaily, StockFactorScore
from app.schemas import SimulationHolding, SimulationMetric, SimulationPositionSnapshot, SimulationRebalanceStep, SimulationReviewResult, SimulationRunSummary, SimulationTradeDetail

COMMISSION_RATE = 0.0003
STAMP_DUTY_RATE = 0.0005
TRANSFER_FEE_RATE = 0.00001
SLIPPAGE_RATE = 0.0005
REBALANCE_TRADING_DAYS = 5


@dataclass
class PositionState:
    """模拟持仓状态。quantity 用股数表示，cost_price 用买入成交价表示。"""

    ts_code: str
    quantity: float
    cost_price: float
    buy_date: date


class SimulationService:
    """阶段6模拟交易与复盘服务。

    时间要求：
    1. start_date 是阶段5盘后评分/推荐信号日，系统按 T+1 开盘价模拟买入；
    2. end_date 必须晚于 start_date，且区间内要有日线行情，否则无法计算收益；
    3. Rank IC 需要 end_date 之后至少 5/10/20 个交易日行情，数据不足时返回 0；
    4. 本版按每 5 个交易日调仓，交易成本参数按 V1.2 默认值集中配置。
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def run_review(
        self,
        start_date: str | date,
        end_date: str | date,
        stock_count: int,
        initial_cash: float,
        min_score: float = 65,
        review_mode: str = "hold",
    ) -> SimulationReviewResult:
        signal_date = self._parse_date(start_date)
        review_end = self._parse_date(end_date)
        if review_mode not in {"hold", "rebalance"}:
            raise AppException("复盘方式只能是固定信号持有或定期调仓。", code="INVALID_SIMULATION_REVIEW_MODE", status_code=422)
        if signal_date >= review_end:
            raise AppException("复盘结束日期必须晚于开始信号日", code="INVALID_SIMULATION_DATE_RANGE", status_code=422)
        score_count = self.db.scalar(select(func.count()).select_from(StockFactorScore).where(StockFactorScore.trade_date == signal_date))
        if not score_count:
            raise AppException(
                f"{signal_date:%Y-%m-%d} 没有阶段5因子评分结果，不能作为复盘开始信号日。请先在“研究推荐应用”计算该日评分，或选择已有评分的日期。",
                code="SIMULATION_SIGNAL_MISSING",
                status_code=422,
            )
        initial_targets = self._target_codes(signal_date, stock_count, min_score)
        if not initial_targets:
            raise AppException(
                f"{signal_date:%Y-%m-%d} 没有满足最低综合分 {min_score} 的候选股票，无法按参数建仓。请降低最低综合分、减少股票数，或重新检查阶段5评分结果。",
                code="SIMULATION_CANDIDATES_EMPTY",
                status_code=422,
            )

        score_key = str(min_score).replace(".", "p")
        strategy_version = f"review-{review_mode}-{signal_date:%Y%m%d}-{review_end:%Y%m%d}-top{stock_count}-cash{int(initial_cash)}-score{score_key}"
        trading_dates = self._trading_dates(signal_date, review_end)
        if len(trading_dates) < 2:
            raise AppException("复盘区间内行情数据不足，至少需要 T+1 买入日和一个估值日", code="SIMULATION_DATA_INSUFFICIENT", status_code=422)

        self._clear_previous_run(strategy_version)
        cash = float(initial_cash)
        positions: dict[str, PositionState] = {}
        equity_curve: list[tuple[date, float]] = []
        closed_returns: list[float] = []
        total_buy_amount = 0.0
        total_sell_amount = 0.0
        rebalances: list[SimulationRebalanceStep] = []

        for index, current_date in enumerate(trading_dates[1:], start=1):
            should_rebalance = index == 1 or (review_mode == "rebalance" and (index - 1) % REBALANCE_TRADING_DAYS == 0)
            if should_rebalance:
                signal = signal_date if review_mode == "hold" else self._previous_signal_date(current_date)
                target_codes = initial_targets if review_mode == "hold" else self._target_codes(signal, stock_count, min_score)
                before_cash = cash
                before_holdings = self._position_snapshots(positions, current_date)
                before_market_value = sum(item.market_value for item in before_holdings)
                cash, sell_amount, sold_returns, sell_trades = self._sell_removed_positions(strategy_version, current_date, positions, target_codes, cash)
                total_sell_amount += sell_amount
                closed_returns.extend(sold_returns)
                cash, buy_amount, buy_trades = self._buy_missing_positions(strategy_version, current_date, positions, target_codes, cash, stock_count)
                total_buy_amount += buy_amount
                after_holdings = self._position_snapshots(positions, current_date)
                after_market_value = sum(item.market_value for item in after_holdings)
                rebalances.append(
                    SimulationRebalanceStep(
                        trade_date=current_date.isoformat(),
                        signal_date=signal.isoformat(),
                        before_cash=round(before_cash, 4),
                        before_market_value=round(before_market_value, 4),
                        before_total_value=round(before_cash + before_market_value, 4),
                        before_holdings=before_holdings,
                        sell_trades=sell_trades,
                        buy_trades=buy_trades,
                        after_cash=round(cash, 4),
                        after_market_value=round(after_market_value, 4),
                        after_total_value=round(cash + after_market_value, 4),
                        after_holdings=after_holdings,
                    )
                )

            total_value = cash + self._positions_market_value(positions, current_date)
            equity_curve.append((current_date, total_value))

        final_date = trading_dates[-1]
        final_value = cash + self._positions_market_value(positions, final_date)
        holdings = self._final_holdings(positions, final_date, final_value)
        self._write_position_snapshots(strategy_version, positions, final_date)
        self.db.commit()

        cumulative_return = final_value / initial_cash - 1
        annual_return = self._annual_return(cumulative_return, len(equity_curve))
        max_drawdown = self._max_drawdown([value for _, value in equity_curve])
        win_rate = self._win_rate(closed_returns, holdings)
        avg_holding_days = self._average_holding_days(positions, final_date)
        turnover_rate = (total_buy_amount + total_sell_amount) / initial_cash
        benchmark_return = self._benchmark_return(signal_date, review_end)
        excess_return = cumulative_return - benchmark_return
        rank_ic_5d = self._rank_ic(signal_date, 5)
        rank_ic_10d = self._rank_ic(signal_date, 10)
        rank_ic_20d = self._rank_ic(signal_date, 20)

        metrics = [
            SimulationMetric(name="累计收益率", value=round(cumulative_return * 100, 4), description="模拟组合从买入到结束日期的总收益率。"),
            SimulationMetric(name="年化收益率", value=round(annual_return * 100, 4), description="按 252 个交易日折算的年化收益率，便于不同区间比较。"),
            SimulationMetric(name="最大回撤", value=round(max_drawdown * 100, 4), description="净值从阶段高点回落到低点的最大跌幅，衡量风险暴露。"),
            SimulationMetric(name="胜率", value=round(win_rate * 100, 4), description="盈利交易或当前盈利持仓占总样本比例。"),
            SimulationMetric(name="平均持仓天数", value=round(avg_holding_days, 2), description="当前持仓平均持有交易日近似值，用于观察调仓周期。"),
            SimulationMetric(name="换手率", value=round(turnover_rate, 4), description="买入和卖出成交额相对初始资金的比例，衡量交易活跃度。"),
            SimulationMetric(name="超额收益", value=round(excess_return * 100, 4), description="组合收益率减去股票池等权基准收益率。"),
            SimulationMetric(name="Rank IC 5D", value=round(rank_ic_5d, 4), description="起始日评分与未来 5 日收益的 Spearman 相关系数。"),
            SimulationMetric(name="Rank IC 10D", value=round(rank_ic_10d, 4), description="起始日评分与未来 10 日收益的 Spearman 相关系数。"),
            SimulationMetric(name="Rank IC 20D", value=round(rank_ic_20d, 4), description="起始日评分与未来 20 日收益的 Spearman 相关系数。"),
        ]
        result = SimulationReviewResult(
            strategy_version=strategy_version,
            start_date=signal_date.isoformat(),
            end_date=review_end.isoformat(),
            stock_count=stock_count,
            initial_cash=initial_cash,
            final_value=round(final_value, 4),
            metrics=metrics,
            holdings=holdings,
            rebalances=rebalances,
            conclusion=self._conclusion(cumulative_return, excess_return, max_drawdown),
            time_requirement=self._time_requirement(review_mode),
        )
        self._save_review_result(result)
        return result

    def list_recent_runs(self, limit: int = 20) -> tuple[list[dict[str, Any]], int]:
        statement = select(SimulationReview).order_by(SimulationReview.created_at.desc()).limit(limit)
        items = [self._review_summary(row).model_dump(mode="json") for row in self.db.scalars(statement)]
        return items, len(items)

    def get_review(self, strategy_version: str) -> SimulationReviewResult:
        review = self.db.get(SimulationReview, strategy_version)
        if review is None:
            raise AppException("未找到该历史复盘记录。", code="SIMULATION_REVIEW_NOT_FOUND", status_code=404)
        return self._review_result(review)

    def _target_codes(self, signal_date: date, stock_count: int, min_score: float) -> list[str]:
        statement = (
            select(StockFactorScore)
            .where(StockFactorScore.trade_date == signal_date, StockFactorScore.final_score >= min_score, StockFactorScore.recommendation_level.in_(["S", "A", "B"]))
            .order_by(StockFactorScore.final_score.desc(), StockFactorScore.rank_in_universe.asc())
            .limit(stock_count)
        )
        return [row.ts_code for row in self.db.scalars(statement)]

    def _buy_missing_positions(
        self,
        strategy_version: str,
        trade_date: date,
        positions: dict[str, PositionState],
        target_codes: list[str],
        cash: float,
        stock_count: int,
    ) -> tuple[float, float, list[SimulationTradeDetail]]:
        missing = [code for code in target_codes if code not in positions]
        if not missing:
            return cash, 0.0, []
        target_weight = min(0.10, 1 / max(stock_count, 1))
        buy_amount = 0.0
        trades: list[SimulationTradeDetail] = []
        for code in missing:
            meta = self._stock_meta(code)
            open_price = self._open_price(code, trade_date)
            if open_price is None or open_price <= 0:
                continue
            allocation = min(cash, target_weight * (cash + self._positions_market_value(positions, trade_date)))
            if allocation <= 0:
                continue
            execution_price = open_price * (1 + SLIPPAGE_RATE)
            cost = allocation * (1 + COMMISSION_RATE + TRANSFER_FEE_RATE)
            quantity = allocation / execution_price
            cash -= cost
            buy_amount += allocation
            positions[code] = PositionState(ts_code=code, quantity=quantity, cost_price=execution_price, buy_date=trade_date)
            reason = "T日评分入选，T+1开盘模拟买入"
            trades.append(
                SimulationTradeDetail(
                    ts_code=code,
                    name=meta["name"],
                    industry=meta["industry"],
                    market=meta["market"],
                    side="buy",
                    price=round(execution_price, 4),
                    quantity=round(quantity, 4),
                    amount=round(allocation, 4),
                    reason=reason,
                )
            )
            self._add_trade(strategy_version, code, trade_date, "buy", execution_price, quantity, allocation, reason)
        return cash, buy_amount, trades

    def _sell_removed_positions(
        self,
        strategy_version: str,
        trade_date: date,
        positions: dict[str, PositionState],
        target_codes: list[str],
        cash: float,
    ) -> tuple[float, float, list[float], list[SimulationTradeDetail]]:
        sell_amount = 0.0
        returns: list[float] = []
        trades: list[SimulationTradeDetail] = []
        for code in list(positions):
            if code in target_codes:
                continue
            position = positions.pop(code)
            meta = self._stock_meta(code)
            open_price = self._open_price(code, trade_date)
            if open_price is None:
                positions[code] = position
                continue
            execution_price = open_price * (1 - SLIPPAGE_RATE)
            gross_amount = execution_price * position.quantity
            net_amount = gross_amount * (1 - COMMISSION_RATE - STAMP_DUTY_RATE - TRANSFER_FEE_RATE)
            cost_basis = position.cost_price * position.quantity
            cash += net_amount
            sell_amount += gross_amount
            realized_return = net_amount / cost_basis - 1 if cost_basis else 0
            returns.append(realized_return)
            reason = "调仓移出或等级不足，T+1开盘模拟卖出"
            trades.append(
                SimulationTradeDetail(
                    ts_code=code,
                    name=meta["name"],
                    industry=meta["industry"],
                    market=meta["market"],
                    side="sell",
                    price=round(execution_price, 4),
                    quantity=round(position.quantity, 4),
                    amount=round(gross_amount, 4),
                    profit_loss=round(net_amount - cost_basis, 4),
                    return_rate=round(realized_return * 100, 4),
                    reason=reason,
                )
            )
            self._add_trade(strategy_version, code, trade_date, "sell", execution_price, position.quantity, gross_amount, reason)
        return cash, sell_amount, returns, trades

    def _add_trade(self, strategy_version: str, ts_code: str, trade_date: date, side: str, price: float, quantity: float, amount: float, reason: str) -> None:
        self.db.add(
            SimulationTrade(
                strategy_version=strategy_version,
                ts_code=ts_code,
                trade_date=trade_date,
                side=side,
                price=Decimal(str(round(price, 4))),
                quantity=Decimal(str(round(quantity, 4))),
                amount=Decimal(str(round(amount, 4))),
                reason=reason,
            )
        )

    def _write_position_snapshots(self, strategy_version: str, positions: dict[str, PositionState], trade_date: date) -> None:
        for position in positions.values():
            close_price = self._close_price(position.ts_code, trade_date) or position.cost_price
            self.db.add(
                SimulationPosition(
                    strategy_version=strategy_version,
                    ts_code=position.ts_code,
                    trade_date=trade_date,
                    quantity=Decimal(str(round(position.quantity, 4))),
                    cost_price=Decimal(str(round(position.cost_price, 4))),
                    market_value=Decimal(str(round(position.quantity * close_price, 4))),
                )
            )

    def _final_holdings(self, positions: dict[str, PositionState], trade_date: date, final_value: float) -> list[SimulationHolding]:
        holdings: list[SimulationHolding] = []
        for position in positions.values():
            meta = self._stock_meta(position.ts_code)
            end_price = self._close_price(position.ts_code, trade_date) or position.cost_price
            market_value = end_price * position.quantity
            holdings.append(
                SimulationHolding(
                    ts_code=position.ts_code,
                    name=meta["name"],
                    industry=meta["industry"],
                    market=meta["market"],
                    buy_date=position.buy_date.isoformat(),
                    weight=round(market_value / final_value, 4) if final_value else 0,
                    allocated_cash=round(position.cost_price * position.quantity, 4),
                    buy_price=round(position.cost_price, 4),
                    end_price=round(end_price, 4),
                    return_rate=round((end_price / position.cost_price - 1) * 100, 4),
                )
            )
        return sorted(holdings, key=lambda item: item.weight, reverse=True)

    def _positions_market_value(self, positions: dict[str, PositionState], trade_date: date) -> float:
        total = 0.0
        for position in positions.values():
            close_price = self._close_price(position.ts_code, trade_date) or position.cost_price
            total += close_price * position.quantity
        return total

    def _position_snapshots(self, positions: dict[str, PositionState], trade_date: date) -> list[SimulationPositionSnapshot]:
        snapshots: list[SimulationPositionSnapshot] = []
        for position in positions.values():
            meta = self._stock_meta(position.ts_code)
            current_price = self._close_price(position.ts_code, trade_date) or position.cost_price
            market_value = current_price * position.quantity
            snapshots.append(
                SimulationPositionSnapshot(
                    ts_code=position.ts_code,
                    name=meta["name"],
                    industry=meta["industry"],
                    market=meta["market"],
                    buy_date=position.buy_date.isoformat(),
                    quantity=round(position.quantity, 4),
                    cost_price=round(position.cost_price, 4),
                    current_price=round(current_price, 4),
                    market_value=round(market_value, 4),
                    return_rate=round((current_price / position.cost_price - 1) * 100, 4) if position.cost_price else 0,
                )
            )
        return snapshots

    def _stock_meta(self, ts_code: str) -> dict[str, str]:
        stock = self.db.get(StockBasic, ts_code)
        if stock is None:
            return {"name": "", "industry": "", "market": ""}
        return {"name": stock.name or "", "industry": stock.industry or "", "market": stock.market or ""}

    def _benchmark_return(self, start_date: date, end_date: date) -> float:
        rows = self.db.execute(
            select(StockDaily.ts_code, StockDaily.trade_date, StockDaily.close_price).where(StockDaily.trade_date.in_([start_date, end_date]))
        ).all()
        grouped: dict[str, dict[date, float]] = {}
        for code, row_date, close in rows:
            grouped.setdefault(code, {})[row_date] = to_float(close) or 0
        returns = [prices[end_date] / prices[start_date] - 1 for prices in grouped.values() if prices.get(start_date) and prices.get(end_date)]
        return 0.0 if not returns else sum(returns) / len(returns)

    def _rank_ic(self, signal_date: date, forward_days: int) -> float:
        signal_rows = list(self.db.scalars(select(StockFactorScore).where(StockFactorScore.trade_date == signal_date)))
        future_date = self._nth_trading_date_after(signal_date, forward_days)
        if future_date is None or not signal_rows:
            return 0.0
        records = []
        for score in signal_rows:
            start_price = self._close_price(score.ts_code, signal_date)
            end_price = self._close_price(score.ts_code, future_date)
            if start_price and end_price:
                records.append({"score": to_float(score.final_score), "return": end_price / start_price - 1})
        if len(records) < 3:
            return 0.0
        frame = pd.DataFrame(records)
        return float(frame["score"].rank().corr(frame["return"].rank()) or 0.0)

    def _trading_dates(self, start_date: date, end_date: date) -> list[date]:
        return list(self.db.scalars(select(StockDaily.trade_date).where(StockDaily.trade_date >= start_date, StockDaily.trade_date <= end_date).distinct().order_by(StockDaily.trade_date)))

    def _previous_signal_date(self, trade_date: date) -> date:
        return self.db.scalar(select(StockFactorScore.trade_date).where(StockFactorScore.trade_date < trade_date).order_by(StockFactorScore.trade_date.desc()).limit(1)) or trade_date

    def _nth_trading_date_after(self, start_date: date, n: int) -> date | None:
        dates = list(self.db.scalars(select(StockDaily.trade_date).where(StockDaily.trade_date > start_date).distinct().order_by(StockDaily.trade_date).limit(n)))
        return dates[-1] if len(dates) == n else None

    def _open_price(self, ts_code: str, trade_date: date) -> float | None:
        return to_float(self.db.scalar(select(StockDaily.open_price).where(StockDaily.ts_code == ts_code, StockDaily.trade_date == trade_date)))

    def _close_price(self, ts_code: str, trade_date: date) -> float | None:
        return to_float(self.db.scalar(select(StockDaily.close_price).where(StockDaily.ts_code == ts_code, StockDaily.trade_date == trade_date)))

    def _clear_previous_run(self, strategy_version: str) -> None:
        self.db.execute(delete(SimulationTrade).where(SimulationTrade.strategy_version == strategy_version))
        self.db.execute(delete(SimulationPosition).where(SimulationPosition.strategy_version == strategy_version))
        self.db.execute(delete(SimulationReview).where(SimulationReview.strategy_version == strategy_version))
        self.db.commit()

    def _save_review_result(self, result: SimulationReviewResult) -> None:
        metric_map = {metric.name: self._metric_number(metric.value) for metric in result.metrics}
        review = SimulationReview(
            strategy_version=result.strategy_version,
            start_date=self._parse_date(result.start_date),
            end_date=self._parse_date(result.end_date),
            stock_count=result.stock_count,
            initial_cash=Decimal(str(round(result.initial_cash, 4))),
            final_value=Decimal(str(round(result.final_value, 4))),
            cumulative_return=Decimal(str(round((metric_map.get("累计收益率") or 0) / 100, 6))),
            max_drawdown=Decimal(str(round((metric_map.get("最大回撤") or 0) / 100, 6))),
            win_rate=Decimal(str(round((metric_map.get("胜率") or 0) / 100, 6))),
            metrics_json=json.dumps([metric.model_dump() for metric in result.metrics], ensure_ascii=False),
            holdings_json=json.dumps([holding.model_dump() for holding in result.holdings], ensure_ascii=False),
            rebalances_json=json.dumps([rebalance.model_dump() for rebalance in result.rebalances], ensure_ascii=False),
            conclusion=result.conclusion,
            time_requirement=result.time_requirement,
        )
        self.db.add(review)
        self.db.commit()

    @staticmethod
    def _review_summary(review: SimulationReview) -> SimulationRunSummary:
        return SimulationRunSummary(
            strategy_version=review.strategy_version,
            start_date=review.start_date.isoformat(),
            end_date=review.end_date.isoformat(),
            stock_count=review.stock_count,
            initial_cash=float(review.initial_cash or 0),
            final_value=float(review.final_value or 0),
            cumulative_return=float(review.cumulative_return or 0),
            max_drawdown=float(review.max_drawdown or 0),
            win_rate=float(review.win_rate or 0),
            conclusion=review.conclusion or "",
            created_at=review.created_at.isoformat(),
        )

    def _review_result(self, review: SimulationReview) -> SimulationReviewResult:
        metrics = [SimulationMetric(**item) for item in json.loads(review.metrics_json or "[]")]
        holdings = [SimulationHolding(**item) for item in json.loads(review.holdings_json or "[]")]
        rebalances = [SimulationRebalanceStep(**item) for item in json.loads(review.rebalances_json or "[]")]
        buy_dates = self._latest_buy_dates(review.strategy_version)
        for holding in holdings:
            if not holding.buy_date:
                holding.buy_date = buy_dates.get(holding.ts_code, "")
        return SimulationReviewResult(
            strategy_version=review.strategy_version,
            start_date=review.start_date.isoformat(),
            end_date=review.end_date.isoformat(),
            stock_count=review.stock_count,
            initial_cash=float(review.initial_cash or 0),
            final_value=float(review.final_value or 0),
            metrics=metrics,
            holdings=holdings,
            rebalances=rebalances,
            conclusion=review.conclusion or "",
            time_requirement=review.time_requirement or "",
        )

    def _latest_buy_dates(self, strategy_version: str) -> dict[str, str]:
        rows = self.db.execute(
            select(SimulationTrade.ts_code, func.max(SimulationTrade.trade_date))
            .where(SimulationTrade.strategy_version == strategy_version, SimulationTrade.side == "buy")
            .group_by(SimulationTrade.ts_code)
        ).all()
        return {code: trade_date.isoformat() for code, trade_date in rows if trade_date}

    @staticmethod
    def _metric_number(value: float | int | str) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _time_requirement(review_mode: str) -> str:
        if review_mode == "rebalance":
            return "复盘开始日必须已有评分；定期调仓会使用区间内最近评分结果，交易按T日盘后信号、T+1开盘价成交；结束日之后行情越完整，Rank IC 5/10/20D 越可靠。"
        return "复盘开始日必须已有评分；固定信号持有只使用开始信号日推荐列表，T+1开盘价买入后持有到结束估值日；结束日之后行情越完整，Rank IC 5/10/20D 越可靠。"

    @staticmethod
    def _annual_return(cumulative_return: float, trading_days: int) -> float:
        if trading_days <= 0:
            return 0.0
        return (1 + cumulative_return) ** (252 / trading_days) - 1

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
    def _win_rate(closed_returns: list[float], holdings: list[SimulationHolding]) -> float:
        current_returns = [holding.return_rate / 100 for holding in holdings]
        all_returns = closed_returns + current_returns
        if not all_returns:
            return 0.0
        return sum(1 for item in all_returns if item > 0) / len(all_returns)

    @staticmethod
    def _average_holding_days(positions: dict[str, PositionState], end_date: date) -> float:
        if not positions:
            return 0.0
        return sum((end_date - position.buy_date).days for position in positions.values()) / len(positions)

    @staticmethod
    def _conclusion(cumulative_return: float, excess_return: float, max_drawdown: float) -> str:
        if cumulative_return > 0 and excess_return > 0 and abs(max_drawdown) <= 0.15:
            return "组合取得正收益并跑赢股票池等权基准，阶段5评分在该区间具备一定有效性。"
        if cumulative_return > 0 and excess_return <= 0:
            return "组合取得正收益但未跑赢股票池等权基准，需要继续观察权重和行业暴露。"
        return "组合收益或回撤表现不佳，需要复核因子权重、风险扣分和调仓规则。"

    @staticmethod
    def _parse_date(value: str | date) -> date:
        if isinstance(value, date):
            return value
        return datetime.strptime(value.replace("-", ""), "%Y%m%d").date()
