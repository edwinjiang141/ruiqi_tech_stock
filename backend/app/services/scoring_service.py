from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pandas as pd
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.formulas.capital_flow_formula import calculate_capital_flow_score
from app.formulas.common import band_health_score, percentile_score, to_float
from app.formulas.final_score_formula import FORMULA_VERSION, calculate_final_score, recommendation_level
from app.formulas.growth_formula import calculate_growth_score
from app.formulas.leadership_formula import calculate_leadership_score
from app.formulas.momentum_formula import calculate_momentum_score
from app.formulas.quality_formula import calculate_quality_score
from app.formulas.risk_formula import calculate_risk_result
from app.models import (
    IndexWeight,
    StockBalanceSheet,
    StockBasic,
    StockDaily,
    StockDailyBasic,
    StockFactorScore,
    StockFinancialIndicator,
    StockIncome,
    StockMoneyflow,
    StockPledgeStat,
    StockRecommendation,
)
from app.schemas import CollectionResult


@dataclass
class FactorCandidate:
    """单只股票的评分输入，服务层负责从 DWD 数据聚合，公式层只负责计算。"""

    ts_code: str
    name: str | None
    industry: str
    market: str | None
    list_date: date | None
    list_status: str | None
    daily_rows: list[StockDaily] = field(default_factory=list)
    basic_rows: list[StockDailyBasic] = field(default_factory=list)
    moneyflow_rows: list[StockMoneyflow] = field(default_factory=list)
    financial: StockFinancialIndicator | None = None
    cashflows: list[Any] = field(default_factory=list)
    incomes: list[StockIncome] = field(default_factory=list)
    balance: StockBalanceSheet | None = None
    pledge: StockPledgeStat | None = None
    index_weight: IndexWeight | None = None
    metrics: dict[str, float | None] = field(default_factory=dict)


class ScoringService:
    """阶段5核心评分服务：构建因子输入、执行风险过滤、写入评分和推荐结果。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def calculate_for_date(self, trade_date: str | date, top_n: int = 50) -> CollectionResult:
        target_date = self._parse_trade_date(trade_date)
        candidates = self._build_candidates(target_date)
        scored_rows: list[dict[str, Any]] = []
        excluded_count = 0

        for candidate in candidates:
            self._calculate_candidate_metrics(candidate)

        industry_groups: dict[str, list[FactorCandidate]] = defaultdict(list)
        for candidate in candidates:
            industry_groups[candidate.industry].append(candidate)

        for candidate in candidates:
            result = self._score_candidate(candidate, industry_groups[candidate.industry])
            if result is None:
                excluded_count += 1
                continue
            scored_rows.append(result)

        scored_rows.sort(key=lambda item: item["final_score"], reverse=True)
        industry_rank_counter: dict[str, int] = defaultdict(int)
        for rank, row in enumerate(scored_rows, start=1):
            row["rank_in_universe"] = rank
            industry_rank_counter[row["industry"]] += 1
            row["rank_in_industry"] = industry_rank_counter[row["industry"]]

        self._upsert_factor_scores(scored_rows, target_date)
        self._replace_recommendations(scored_rows[:top_n], target_date)

        status = "warning" if excluded_count else "success"
        return CollectionResult(
            task_name="calculate_factor_scores",
            source="dwd_market,dwd_financial,dwd_moneyflow,dwd_risk",
            fetched_count=len(candidates),
            inserted_or_updated_count=len(scored_rows),
            status=status,
            message=f"{target_date:%Y%m%d} 因子评分完成，生成 {len(scored_rows)} 只股票评分，过滤 {excluded_count} 只，推荐 Top {min(top_n, len(scored_rows))}",
        )

    def list_factor_scores(self, trade_date: str | None = None, limit: int = 50) -> tuple[list[dict[str, Any]], int]:
        statement = select(StockFactorScore, StockBasic).join(StockBasic, StockBasic.ts_code == StockFactorScore.ts_code)
        if trade_date:
            statement = statement.where(StockFactorScore.trade_date == self._parse_trade_date(trade_date))
        statement = statement.order_by(StockFactorScore.trade_date.desc(), StockFactorScore.rank_in_universe.asc()).limit(limit)
        rows = self.db.execute(statement).all()
        items = [self._factor_payload(score, stock) for score, stock in rows]
        return items, len(items)

    def list_score_history(self, limit: int = 10, offset: int = 0) -> tuple[list[dict[str, Any]], int]:
        total = self.db.scalar(select(func.count()).select_from(select(StockFactorScore.trade_date).distinct().subquery())) or 0
        rows = self.db.execute(
            select(StockFactorScore.trade_date, func.count().label("factor_score_count"))
            .group_by(StockFactorScore.trade_date)
            .order_by(StockFactorScore.trade_date.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        dates = [row.trade_date for row in rows]
        recommendation_counts = {
            trade_date: count
            for trade_date, count in self.db.execute(
                select(StockRecommendation.trade_date, func.count())
                .where(StockRecommendation.trade_date.in_(dates))
                .group_by(StockRecommendation.trade_date)
            ).all()
        }
        items = [
            {
                "trade_date": trade_date.isoformat(),
                "factor_score_count": factor_score_count,
                "recommendation_count": recommendation_counts.get(trade_date, 0),
            }
            for trade_date, factor_score_count in rows
        ]
        return items, total

    def _build_candidates(self, target_date: date) -> list[FactorCandidate]:
        stocks = list(
            self.db.scalars(
                select(StockBasic)
                .where(StockBasic.list_status == "L")
                .where((StockBasic.is_gem.is_(True)) | (StockBasic.is_star.is_(True)) | (StockBasic.is_tech_industry.is_(True)))
                .order_by(StockBasic.ts_code)
            )
        )
        codes = [stock.ts_code for stock in stocks]
        candidates = {
            stock.ts_code: FactorCandidate(
                ts_code=stock.ts_code,
                name=stock.name,
                industry=stock.industry or "未分类",
                market=stock.market,
                list_date=stock.list_date,
                list_status=stock.list_status,
            )
            for stock in stocks
        }
        if not codes:
            return []

        start_date = target_date - timedelta(days=260)
        for row in self.db.scalars(select(StockDaily).where(StockDaily.ts_code.in_(codes), StockDaily.trade_date <= target_date, StockDaily.trade_date >= start_date)):
            candidates[row.ts_code].daily_rows.append(row)
        for row in self.db.scalars(select(StockDailyBasic).where(StockDailyBasic.ts_code.in_(codes), StockDailyBasic.trade_date <= target_date, StockDailyBasic.trade_date >= start_date)):
            candidates[row.ts_code].basic_rows.append(row)
        for row in self.db.scalars(select(StockMoneyflow).where(StockMoneyflow.ts_code.in_(codes), StockMoneyflow.trade_date <= target_date, StockMoneyflow.trade_date >= target_date - timedelta(days=45))):
            candidates[row.ts_code].moneyflow_rows.append(row)
        for row in self.db.scalars(select(StockFinancialIndicator).where(StockFinancialIndicator.ts_code.in_(codes), StockFinancialIndicator.ann_date <= target_date)):
            self._set_latest(candidates[row.ts_code], "financial", row, row.ann_date or row.end_date)
        for row in self.db.scalars(select(StockIncome).where(StockIncome.ts_code.in_(codes), StockIncome.ann_date <= target_date)):
            candidates[row.ts_code].incomes.append(row)
        for row in self.db.scalars(select(StockBalanceSheet).where(StockBalanceSheet.ts_code.in_(codes), StockBalanceSheet.ann_date <= target_date)):
            self._set_latest(candidates[row.ts_code], "balance", row, row.ann_date or row.end_date)
        for row in self.db.scalars(select(StockPledgeStat).where(StockPledgeStat.ts_code.in_(codes), StockPledgeStat.end_date <= target_date)):
            self._set_latest(candidates[row.ts_code], "pledge", row, row.end_date)
        for row in self.db.scalars(select(IndexWeight).where(IndexWeight.con_code.in_(codes), IndexWeight.trade_date <= target_date)):
            current = candidates[row.con_code].index_weight
            if current is None or row.trade_date > current.trade_date:
                candidates[row.con_code].index_weight = row

        return list(candidates.values())

    @staticmethod
    def _set_latest(candidate: FactorCandidate, attr: str, row: Any, row_date: date) -> None:
        current = getattr(candidate, attr)
        current_date = getattr(current, "ann_date", None) or getattr(current, "end_date", date.min) if current else date.min
        if row_date >= current_date:
            setattr(candidate, attr, row)

    def _calculate_candidate_metrics(self, candidate: FactorCandidate) -> None:
        candidate.daily_rows.sort(key=lambda item: item.trade_date)
        candidate.basic_rows.sort(key=lambda item: item.trade_date)
        candidate.moneyflow_rows.sort(key=lambda item: item.trade_date)
        candidate.incomes.sort(key=lambda item: item.end_date)

        latest_basic = candidate.basic_rows[-1] if candidate.basic_rows else None
        latest_daily = candidate.daily_rows[-1] if candidate.daily_rows else None
        latest_income = candidate.incomes[-1] if candidate.incomes else None
        previous_income = candidate.incomes[-2] if len(candidate.incomes) >= 2 else None

        candidate.metrics = {
            "roe": to_float(getattr(candidate.financial, "roe", None)),
            "roa": to_float(getattr(candidate.financial, "roa", None)),
            "grossprofit_margin": to_float(getattr(candidate.financial, "grossprofit_margin", None)),
            "ocf_to_profit": to_float(getattr(candidate.financial, "ocf_to_profit", None)),
            "debt_to_assets": to_float(getattr(candidate.financial, "debt_to_assets", None)),
            "revenue_yoy": to_float(getattr(candidate.financial, "revenue_yoy", None)),
            "netprofit_yoy": to_float(getattr(candidate.financial, "netprofit_yoy", None)),
            "pe_ttm": to_float(getattr(latest_basic, "pe_ttm", None)),
            "pb": to_float(getattr(latest_basic, "pb", None)),
            "ps_ttm": to_float(getattr(latest_basic, "ps_ttm", None)),
            "total_mv": to_float(getattr(latest_basic, "total_mv", None)),
            "turnover_rate": to_float(getattr(latest_basic, "turnover_rate", None)),
            "amount": to_float(getattr(latest_daily, "amount", None)),
            "revenue": to_float(getattr(latest_income, "revenue", None) or getattr(latest_income, "total_revenue", None)),
            "quarter_improvement": self._quarter_improvement(latest_income, previous_income),
            "revenue_cagr": self._revenue_cagr(candidate.incomes),
            "return_5d": self._return_percent(candidate.daily_rows, 5),
            "return_20d": self._return_percent(candidate.daily_rows, 20),
            "return_60d": self._return_percent(candidate.daily_rows, 60),
            "return_120d": self._return_percent(candidate.daily_rows, 120),
            "volatility": self._volatility(candidate.daily_rows[-60:]),
            "net_moneyflow_5d": self._sum_moneyflow(candidate.moneyflow_rows[-5:]),
            "net_moneyflow_20d": self._sum_moneyflow(candidate.moneyflow_rows[-20:]),
            "large_order_net": self._sum_large_order(candidate.moneyflow_rows[-20:]),
            "amount_ratio": self._amount_ratio(candidate.daily_rows),
            "avg_amount_20d": self._avg_amount(candidate.daily_rows[-20:]),
            "max_drawdown_60d": self._max_drawdown(candidate.daily_rows[-60:]),
            "negative_ocf_periods": 0 if (candidate.metrics.get("ocf_to_profit") if candidate.metrics else None) is None else 0,
            "net_assets": self._net_assets(candidate.balance),
            "goodwill_to_net_assets": self._goodwill_to_net_assets(candidate.balance),
            "pledge_ratio": to_float(getattr(candidate.pledge, "pledge_ratio", None)),
            "index_weight": to_float(getattr(candidate.index_weight, "weight", None)),
        }

    def _score_candidate(self, candidate: FactorCandidate, peers: list[FactorCandidate]) -> dict[str, Any] | None:
        peer_values = {key: [peer.metrics.get(key) for peer in peers] for key in candidate.metrics}
        m = candidate.metrics
        quality = calculate_quality_score(
            percentile_score(m.get("roe"), peer_values["roe"]),
            percentile_score(m.get("roa"), peer_values["roa"]),
            percentile_score(m.get("grossprofit_margin"), peer_values["grossprofit_margin"]),
            percentile_score(m.get("ocf_to_profit"), peer_values["ocf_to_profit"]),
            m.get("debt_to_assets"),
        )
        growth = calculate_growth_score(
            percentile_score(m.get("revenue_yoy"), peer_values["revenue_yoy"]),
            percentile_score(m.get("netprofit_yoy"), peer_values["netprofit_yoy"]),
            percentile_score(m.get("revenue_cagr"), peer_values["revenue_cagr"]),
            m.get("quarter_improvement"),
            revenue_yoy=m.get("revenue_yoy"),
            netprofit_yoy=m.get("netprofit_yoy"),
        )
        valuation_percentile = percentile_score(m.get("pe_ttm"), peer_values["pe_ttm"])
        from app.formulas.valuation_formula import calculate_valuation_score

        valuation = calculate_valuation_score(
            valuation_percentile,
            percentile_score(m.get("pb"), peer_values["pb"]),
            percentile_score(m.get("ps_ttm"), peer_values["ps_ttm"]),
            valuation_percentile,
            quality,
            growth,
        )
        industry_avg_return_60d = self._average(peer.metrics.get("return_60d") for peer in peers)
        industry_excess = None if m.get("return_60d") is None or industry_avg_return_60d is None else m["return_60d"] - industry_avg_return_60d
        momentum = calculate_momentum_score(
            percentile_score(m.get("return_20d"), peer_values["return_20d"]),
            percentile_score(m.get("return_60d"), peer_values["return_60d"]),
            percentile_score(m.get("return_120d"), peer_values["return_120d"]),
            percentile_score(industry_excess, [peer.metrics.get("return_60d") for peer in peers]),
            percentile_score(m.get("volatility"), peer_values["volatility"], higher_is_better=False),
            return_5d=m.get("return_5d"),
            return_20d=m.get("return_20d"),
            turnover_ratio=m.get("amount_ratio"),
            net_moneyflow_5d=m.get("net_moneyflow_5d"),
        )
        capital_flow = calculate_capital_flow_score(
            percentile_score(m.get("net_moneyflow_5d"), peer_values["net_moneyflow_5d"]),
            percentile_score(m.get("net_moneyflow_20d"), peer_values["net_moneyflow_20d"]),
            percentile_score(m.get("large_order_net"), peer_values["large_order_net"]),
            m.get("amount_ratio"),
            m.get("turnover_rate"),
            price_return_20d=m.get("return_20d"),
            net_moneyflow_20d=m.get("net_moneyflow_20d"),
        )
        leadership = calculate_leadership_score(
            percentile_score(m.get("total_mv"), peer_values["total_mv"]),
            percentile_score(m.get("revenue"), peer_values["revenue"]),
            percentile_score(m.get("amount"), peer_values["amount"]),
            percentile_score(m.get("index_weight"), peer_values["index_weight"]),
            candidate.index_weight is not None,
        )
        risk = calculate_risk_result(
            is_st=bool(candidate.name and "ST" in candidate.name.upper()),
            is_delisting=candidate.list_status != "L",
            listed_trading_days=len(candidate.daily_rows),
            avg_amount_20d=m.get("avg_amount_20d"),
            valid_trading_days_20d=len(candidate.daily_rows[-20:]),
            net_assets=m.get("net_assets"),
            return_20d=m.get("return_20d"),
            max_drawdown_60d=m.get("max_drawdown_60d"),
            valuation_percentile=valuation_percentile,
            debt_to_assets=m.get("debt_to_assets"),
            goodwill_to_net_assets=m.get("goodwill_to_net_assets"),
            pledge_ratio=m.get("pledge_ratio"),
        )
        if risk.excluded:
            return None
        final = calculate_final_score(quality, growth, valuation, momentum, capital_flow, leadership, risk.penalty)
        return {
            "ts_code": candidate.ts_code,
            "trade_date": None,
            "industry": candidate.industry,
            "quality_score": quality,
            "growth_score": growth,
            "valuation_score": valuation,
            "momentum_score": momentum,
            "capital_flow_score": capital_flow,
            "leadership_score": leadership,
            "risk_penalty": risk.penalty,
            "final_score": final,
            "rank_in_universe": None,
            "rank_in_industry": None,
            "recommendation_level": recommendation_level(final),
            "formula_version": FORMULA_VERSION,
            "risk_reasons": risk.reasons,
            "strengths": self._strengths(quality, growth, valuation, momentum, capital_flow, leadership),
        }

    def _upsert_factor_scores(self, rows: list[dict[str, Any]], trade_date: date) -> None:
        if not rows:
            return
        payload = [
            {
                key: self._decimalize(value) if key.endswith("_score") or key == "risk_penalty" else value
                for key, value in row.items()
                if key in {column.name for column in StockFactorScore.__table__.columns}
            }
            | {"trade_date": trade_date}
            for row in rows
        ]
        statement = insert(StockFactorScore).values(payload)
        update_columns = {
            column.name: getattr(statement.excluded, column.name)
            for column in StockFactorScore.__table__.columns
            if column.name not in {"ts_code", "trade_date", "created_at"}
        }
        self.db.execute(statement.on_conflict_do_update(index_elements=["ts_code", "trade_date"], set_=update_columns))
        self.db.commit()

    def _replace_recommendations(self, rows: list[dict[str, Any]], trade_date: date) -> None:
        self.db.execute(delete(StockRecommendation).where(StockRecommendation.trade_date == trade_date, StockRecommendation.formula_version == FORMULA_VERSION))
        for row in rows:
            self.db.add(
                StockRecommendation(
                    ts_code=row["ts_code"],
                    trade_date=trade_date,
                    recommendation_level=row["recommendation_level"],
                    final_score=self._decimalize(row["final_score"]),
                    recommendation_reason="；".join(row["strengths"]) or "综合评分进入推荐池。",
                    risk_warning="；".join(row["risk_reasons"]) or "暂无显著量化风险项。",
                    formula_version=FORMULA_VERSION,
                )
            )
        self.db.commit()

    @staticmethod
    def _factor_payload(score: StockFactorScore, stock: StockBasic) -> dict[str, Any]:
        return {
            "ts_code": score.ts_code,
            "name": stock.name,
            "industry": stock.industry,
            "market": stock.market,
            "trade_date": score.trade_date.isoformat(),
            "quality_score": score.quality_score,
            "growth_score": score.growth_score,
            "valuation_score": score.valuation_score,
            "momentum_score": score.momentum_score,
            "capital_flow_score": score.capital_flow_score,
            "leadership_score": score.leadership_score,
            "risk_penalty": score.risk_penalty,
            "final_score": score.final_score,
            "rank_in_universe": score.rank_in_universe,
            "rank_in_industry": score.rank_in_industry,
            "recommendation_level": score.recommendation_level,
            "formula_version": score.formula_version,
        }

    @staticmethod
    def _parse_trade_date(value: str | date) -> date:
        if isinstance(value, date):
            return value
        return datetime.strptime(value.replace("-", ""), "%Y%m%d").date()

    @staticmethod
    def _decimalize(value: Any) -> Decimal | None:
        number = to_float(value)
        return None if number is None else Decimal(str(round(number, 4)))

    @staticmethod
    def _return_percent(rows: list[StockDaily], window: int) -> float | None:
        if len(rows) <= window:
            return None
        latest = to_float(rows[-1].close_price)
        base = to_float(rows[-window - 1].close_price)
        if latest is None or base is None or base == 0:
            return None
        return (latest / base - 1) * 100

    @staticmethod
    def _volatility(rows: list[StockDaily]) -> float | None:
        closes = [to_float(row.close_price) for row in rows]
        closes = [item for item in closes if item is not None]
        if len(closes) < 2:
            return None
        return float(pd.Series(closes).pct_change().dropna().std() * 100)

    @staticmethod
    def _max_drawdown(rows: list[StockDaily]) -> float | None:
        closes = [to_float(row.close_price) for row in rows]
        closes = [item for item in closes if item is not None]
        if not closes:
            return None
        peak = closes[0]
        max_drawdown = 0.0
        for close in closes:
            peak = max(peak, close)
            if peak:
                max_drawdown = max(max_drawdown, (peak - close) / peak * 100)
        return max_drawdown

    @staticmethod
    def _sum_moneyflow(rows: list[StockMoneyflow]) -> float | None:
        if not rows:
            return None
        values = [to_float(row.net_mf_amount) for row in rows]
        return sum(item for item in values if item is not None)

    @staticmethod
    def _sum_large_order(rows: list[StockMoneyflow]) -> float | None:
        if not rows:
            return None
        total = 0.0
        for row in rows:
            buy = (to_float(row.buy_lg_amount) or 0) + (to_float(row.buy_elg_amount) or 0)
            sell = (to_float(row.sell_lg_amount) or 0) + (to_float(row.sell_elg_amount) or 0)
            total += buy - sell
        return total

    @staticmethod
    def _avg_amount(rows: list[StockDaily]) -> float | None:
        values = [to_float(row.amount) for row in rows]
        values = [item for item in values if item is not None]
        return None if not values else sum(values) / len(values)

    @classmethod
    def _amount_ratio(cls, rows: list[StockDaily]) -> float | None:
        if len(rows) < 25:
            return None
        recent = cls._avg_amount(rows[-5:])
        base = cls._avg_amount(rows[-25:-5])
        if recent is None or base in (None, 0):
            return None
        return recent / base

    @staticmethod
    def _quarter_improvement(latest: StockIncome | None, previous: StockIncome | None) -> float | None:
        latest_revenue = to_float(getattr(latest, "revenue", None) or getattr(latest, "total_revenue", None))
        previous_revenue = to_float(getattr(previous, "revenue", None) or getattr(previous, "total_revenue", None))
        if latest_revenue is None or previous_revenue is None or previous_revenue == 0:
            return None
        return band_health_score((latest_revenue / previous_revenue - 1) * 100, 0, 30, -30, 80)

    @staticmethod
    def _revenue_cagr(incomes: list[StockIncome]) -> float | None:
        valid = [row for row in incomes if to_float(row.revenue or row.total_revenue) not in (None, 0)]
        if len(valid) < 2:
            return None
        first, last = valid[0], valid[-1]
        first_revenue = to_float(first.revenue or first.total_revenue)
        last_revenue = to_float(last.revenue or last.total_revenue)
        years = max((last.end_date - first.end_date).days / 365.0, 1.0)
        if first_revenue is None or last_revenue is None or first_revenue <= 0:
            return None
        return ((last_revenue / first_revenue) ** (1 / years) - 1) * 100

    @staticmethod
    def _net_assets(balance: StockBalanceSheet | None) -> float | None:
        if balance is None:
            return None
        equity = to_float(balance.total_hldr_eqy_exc_min_int) or to_float(balance.total_hldr_eqy_inc_min_int)
        if equity is not None:
            return equity
        assets = to_float(balance.total_assets)
        liabilities = to_float(balance.total_liab)
        if assets is None or liabilities is None:
            return None
        return assets - liabilities

    @classmethod
    def _goodwill_to_net_assets(cls, balance: StockBalanceSheet | None) -> float | None:
        net_assets = cls._net_assets(balance)
        goodwill = to_float(getattr(balance, "goodwill", None))
        if net_assets in (None, 0) or goodwill is None:
            return None
        return goodwill / net_assets * 100

    @staticmethod
    def _average(values: Any) -> float | None:
        cleaned = [item for item in (to_float(value) for value in values) if item is not None]
        return None if not cleaned else sum(cleaned) / len(cleaned)

    @staticmethod
    def _strengths(quality: float, growth: float, valuation: float, momentum: float, capital_flow: float, leadership: float) -> list[str]:
        scores = [
            ("基本面质量较强", quality),
            ("成长性表现较好", growth),
            ("估值相对合理", valuation),
            ("趋势动量较强", momentum),
            ("资金行为改善", capital_flow),
            ("行业龙头特征较明显", leadership),
        ]
        return [name for name, _ in sorted(scores, key=lambda item: item[1], reverse=True)[:3]]
