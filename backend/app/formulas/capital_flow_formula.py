from app.formulas.common import band_health_score, clamp_score, weighted_score


def turnover_health_score(turnover_rate: float | None) -> float:
    """换手率健康分：适度活跃最好，过低流动性差，过高说明短线拥挤。"""

    return band_health_score(turnover_rate, ideal_low=2.0, ideal_high=8.0, hard_low=0.2, hard_high=25.0)


def amount_expansion_health_score(amount_ratio: float | None) -> float:
    """成交额放大健康分：温和放量最好，极端放量容易对应情绪拥挤。"""

    return band_health_score(amount_ratio, ideal_low=1.1, ideal_high=2.5, hard_low=0.3, hard_high=6.0)


def calculate_capital_flow_score(
    net_moneyflow_5d_percentile: float | None,
    net_moneyflow_20d_percentile: float | None,
    large_order_percentile: float | None,
    amount_ratio: float | None,
    turnover_rate: float | None,
    price_return_20d: float | None = None,
    net_moneyflow_20d: float | None = None,
) -> float:
    """
    计算资金行为评分。

    公式来源：V1.2 第 10.8 节。
    CapitalFlow = 30%五日主力净流入 + 25%二十日主力净流入
                + 20%大单/特大单净买入 + 15%成交额放大健康分 + 10%换手率健康分。
    """

    score = weighted_score(
        [
            (net_moneyflow_5d_percentile, 0.30),
            (net_moneyflow_20d_percentile, 0.25),
            (large_order_percentile, 0.20),
            (amount_expansion_health_score(amount_ratio), 0.15),
            (turnover_health_score(turnover_rate), 0.10),
        ]
    )
    if price_return_20d is not None and price_return_20d > 25 and net_moneyflow_20d is not None and net_moneyflow_20d < 0:
        score -= 12.0
    return clamp_score(score)
