from app.formulas.common import clamp_score, weighted_score


def debt_to_assets_health_score(debt_to_assets: float | None) -> float:
    """资产负债率健康分：负债率越低越稳健，超过 80% 视为高财务风险。"""

    if debt_to_assets is None:
        return 0.0
    if debt_to_assets <= 30:
        return 100.0
    if debt_to_assets >= 80:
        return 0.0
    return clamp_score((80 - debt_to_assets) / 50 * 100)


def calculate_quality_score(
    roe_percentile: float | None,
    roa_percentile: float | None,
    gross_margin_percentile: float | None,
    cashflow_quality_percentile: float | None,
    debt_to_assets: float | None,
) -> float:
    """
    计算基本面质量评分。

    公式来源：V1.2 第 10.4 节。
    Quality = 25% ROE分位 + 20% ROA分位 + 20% 毛利率分位
            + 20% 经营现金流质量分位 + 15% 资产负债率健康分。
    """

    return weighted_score(
        [
            (roe_percentile, 0.25),
            (roa_percentile, 0.20),
            (gross_margin_percentile, 0.20),
            (cashflow_quality_percentile, 0.20),
            (debt_to_assets_health_score(debt_to_assets), 0.15),
        ]
    )
