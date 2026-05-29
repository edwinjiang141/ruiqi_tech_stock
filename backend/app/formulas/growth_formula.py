from app.formulas.common import clamp_score, weighted_score


def calculate_growth_score(
    revenue_yoy_percentile: float | None,
    netprofit_yoy_percentile: float | None,
    revenue_cagr_percentile: float | None,
    quarter_improvement_score: float | None,
    revenue_yoy: float | None = None,
    netprofit_yoy: float | None = None,
    negative_ocf_periods: int = 0,
) -> float:
    """
    计算成长性评分。

    公式来源：V1.2 第 10.5 节。
    Growth = 30%营收同比分位 + 30%净利同比分位
           + 20%三年营收CAGR分位 + 20%最近季度环比改善。
    约束：经营现金流连续为负、营收负增长、利润增长但收入不增长时限制上限或打折。
    """

    score = weighted_score(
        [
            (revenue_yoy_percentile, 0.30),
            (netprofit_yoy_percentile, 0.30),
            (revenue_cagr_percentile, 0.20),
            (quarter_improvement_score, 0.20),
        ]
    )
    if negative_ocf_periods >= 2:
        score = min(score, 75.0)
    if revenue_yoy is not None and revenue_yoy < 0:
        score = min(score, 60.0)
    if revenue_yoy is not None and netprofit_yoy is not None and revenue_yoy <= 0 and netprofit_yoy >= 30:
        score *= 0.85
    return clamp_score(score)
