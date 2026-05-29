from app.formulas.common import clamp_score, weighted_score


def calculate_momentum_score(
    return_20d_percentile: float | None,
    return_60d_percentile: float | None,
    return_120d_percentile: float | None,
    industry_excess_score: float | None,
    volatility_health_score: float | None,
    return_5d: float | None = None,
    return_20d: float | None = None,
    turnover_ratio: float | None = None,
    net_moneyflow_5d: float | None = None,
) -> float:
    """
    计算趋势动量评分。

    公式来源：V1.2 第 10.7 节。
    Momentum = 25%二十日收益 + 30%六十日收益 + 20%一百二十日收益
             + 15%行业相对超额收益 + 10%波动率健康分。
    短期涨幅过快、换手拥挤或资金流出时执行过热惩罚。
    """

    score = weighted_score(
        [
            (return_20d_percentile, 0.25),
            (return_60d_percentile, 0.30),
            (return_120d_percentile, 0.20),
            (industry_excess_score, 0.15),
            (volatility_health_score, 0.10),
        ]
    )
    if return_20d is not None and turnover_ratio is not None and return_20d > 40 and turnover_ratio > 2:
        score -= min(15.0, (return_20d - 40) * 0.5)
    if return_5d is not None and net_moneyflow_5d is not None and return_5d > 20 and net_moneyflow_5d < 0:
        score -= min(20.0, return_5d - 20 + 5)
    return clamp_score(score)
