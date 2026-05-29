from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import StockBasic, StockFactorScore, StockRecommendation


class RecommendationService:
    """推荐查询服务：推荐结果由 ScoringService 生成，本服务负责 API 展示。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_recommendations(
        self,
        trade_date: str | date | None = None,
        level: str | None = None,
        min_score: float | None = None,
        limit: int = 50,
    ) -> tuple[list[dict[str, object]], int]:
        statement = (
            select(StockRecommendation, StockFactorScore, StockBasic)
            .join(StockFactorScore, (StockFactorScore.ts_code == StockRecommendation.ts_code) & (StockFactorScore.trade_date == StockRecommendation.trade_date))
            .join(StockBasic, StockBasic.ts_code == StockRecommendation.ts_code)
        )
        if trade_date:
            statement = statement.where(StockRecommendation.trade_date == self._parse_date(trade_date))
        if level:
            statement = statement.where(StockRecommendation.recommendation_level == level)
        if min_score is not None:
            statement = statement.where(StockRecommendation.final_score >= min_score)
        statement = statement.order_by(StockRecommendation.trade_date.desc(), StockFactorScore.rank_in_universe.asc()).limit(limit)
        rows = self.db.execute(statement).all()
        return [self._payload(recommendation, score, stock) for recommendation, score, stock in rows], len(rows)

    @staticmethod
    def _payload(recommendation: StockRecommendation, score: StockFactorScore, stock: StockBasic) -> dict[str, object]:
        return {
            "ts_code": recommendation.ts_code,
            "name": stock.name,
            "industry": stock.industry,
            "market": stock.market,
            "trade_date": recommendation.trade_date.isoformat(),
            "final_score": recommendation.final_score,
            "recommendation_level": recommendation.recommendation_level,
            "rank_no": score.rank_in_universe,
            "quality_score": score.quality_score,
            "growth_score": score.growth_score,
            "valuation_score": score.valuation_score,
            "momentum_score": score.momentum_score,
            "capital_flow_score": score.capital_flow_score,
            "leadership_score": score.leadership_score,
            "risk_penalty": score.risk_penalty,
            "summary": recommendation.recommendation_reason,
            "risk_warning": recommendation.risk_warning,
            "formula_version": recommendation.formula_version,
        }

    @staticmethod
    def _parse_date(value: str | date) -> date:
        if isinstance(value, date):
            return value
        return datetime.strptime(value.replace("-", ""), "%Y%m%d").date()
