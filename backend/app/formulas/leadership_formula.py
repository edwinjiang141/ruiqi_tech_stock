from app.formulas.common import clamp_score, weighted_score


def index_weight_score(index_weight_percentile: float | None, is_index_member: bool) -> float:
    """指数成分/权重分：核心指数成分给基础分，权重越高龙头地位越强。"""

    if not is_index_member:
        return 0.0
    return clamp_score(max(60.0, index_weight_percentile or 0.0))


def calculate_leadership_score(
    market_value_percentile: float | None,
    revenue_percentile: float | None,
    amount_percentile: float | None,
    index_weight_percentile: float | None,
    is_index_member: bool,
) -> float:
    """
    计算龙头地位评分。

    公式来源：V1.2 第 10.9 节。
    Leadership = 40%行业内总市值排名 + 25%行业内营收排名
               + 20%行业内成交额排名 + 15%指数成分/权重分。
    """

    return weighted_score(
        [
            (market_value_percentile, 0.40),
            (revenue_percentile, 0.25),
            (amount_percentile, 0.20),
            (index_weight_score(index_weight_percentile, is_index_member), 0.15),
        ]
    )
