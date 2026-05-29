from app.formulas.common import clamp_score, weighted_score


def valuation_reasonableness_score(percentile: float | None, quality_score: float | None, growth_score: float | None) -> float:
    """
    估值合理性分：不是简单越低越好。

    V1.2 第 10.6 节要求避免价值陷阱：低估值但基本面差不直接加满分；
    高估值若质量和成长较强，可保留部分分数。
    """

    if percentile is None:
        return 0.0
    base = 100 - percentile
    quality = quality_score or 0.0
    growth = growth_score or 0.0
    if percentile <= 30 and quality < 50:
        base *= 0.75
    if percentile >= 80 and quality >= 75 and growth >= 75:
        base = max(base, 55.0)
    if percentile >= 80 and growth < 55:
        base *= 0.70
    return clamp_score(base)


def calculate_valuation_score(
    pe_ttm_percentile: float | None,
    pb_percentile: float | None,
    ps_ttm_percentile: float | None,
    historical_valuation_percentile: float | None,
    quality_score: float | None,
    growth_score: float | None,
) -> float:
    """
    计算估值合理性评分。

    公式来源：V1.2 第 10.6 节。
    Valuation = 30% PE_TTM合理性 + 25% PB合理性
              + 25% PS_TTM合理性 + 20%个股历史估值合理性。
    """

    return weighted_score(
        [
            (valuation_reasonableness_score(pe_ttm_percentile, quality_score, growth_score), 0.30),
            (valuation_reasonableness_score(pb_percentile, quality_score, growth_score), 0.25),
            (valuation_reasonableness_score(ps_ttm_percentile, quality_score, growth_score), 0.25),
            (valuation_reasonableness_score(historical_valuation_percentile, quality_score, growth_score), 0.20),
        ]
    )
