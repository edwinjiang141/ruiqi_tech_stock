from app.formulas.common import clamp_score

FORMULA_VERSION = "v1.2.0"


def calculate_final_score(
    quality_score: float,
    growth_score: float,
    valuation_score: float,
    momentum_score: float,
    capital_flow_score: float,
    leadership_score: float,
    risk_penalty: float,
) -> float:
    """
    计算综合评分。

    公式来源：V1.2 第 10.2 节。
    Final = 0.23质量 + 0.20成长 + 0.14估值 + 0.20动量
          + 0.15资金 + 0.08龙头 - 风险扣分。
    """

    return clamp_score(
        0.23 * quality_score
        + 0.20 * growth_score
        + 0.14 * valuation_score
        + 0.20 * momentum_score
        + 0.15 * capital_flow_score
        + 0.08 * leadership_score
        - risk_penalty
    )


def recommendation_level(final_score: float) -> str:
    """按 V1.2 第 10.3 节输出 S/A/B/C/D 推荐等级。"""

    if final_score >= 85:
        return "S"
    if final_score >= 75:
        return "A"
    if final_score >= 65:
        return "B"
    if final_score >= 55:
        return "C"
    return "D"
