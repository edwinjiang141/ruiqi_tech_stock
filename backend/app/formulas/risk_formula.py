from dataclasses import dataclass, field

from app.formulas.common import clamp_score


@dataclass
class RiskResult:
    """风险计算结果；硬过滤股票不进入推荐池，风险项用于解释和复盘。"""

    excluded: bool
    penalty: float
    reasons: list[str] = field(default_factory=list)


def calculate_risk_result(
    is_st: bool = False,
    is_delisting: bool = False,
    listed_trading_days: int | None = None,
    avg_amount_20d: float | None = None,
    valid_trading_days_20d: int | None = None,
    net_assets: float | None = None,
    return_20d: float | None = None,
    max_drawdown_60d: float | None = None,
    valuation_percentile: float | None = None,
    negative_ocf_periods: int = 0,
    debt_to_assets: float | None = None,
    goodwill_to_net_assets: float | None = None,
    pledge_ratio: float | None = None,
) -> RiskResult:
    """
    计算硬过滤和风险扣分。

    公式来源：V1.2 第 10.10 与 11.1 节。
    ST、退市整理、上市不足 120 交易日、流动性不足、净资产为负等直接剔除；
    短期涨幅、回撤、高估值、现金流、负债、商誉和质押按区间扣分。
    """

    hard_reasons: list[str] = []
    risk_reasons: list[str] = []
    penalty = 0.0

    if is_st:
        hard_reasons.append("ST或*ST股票")
    if is_delisting:
        hard_reasons.append("退市整理或非上市状态")
    if listed_trading_days is not None and listed_trading_days < 120:
        hard_reasons.append("上市交易不足120日")
    if valid_trading_days_20d is not None and valid_trading_days_20d < 15:
        hard_reasons.append("近20日有效交易天数不足")
    if avg_amount_20d is not None and avg_amount_20d < 30000:
        hard_reasons.append("近20日日均成交额过低")
    if net_assets is not None and net_assets <= 0:
        hard_reasons.append("最近可见财报净资产为负")
    if hard_reasons:
        return RiskResult(excluded=True, penalty=100.0, reasons=hard_reasons)

    if return_20d is not None and return_20d > 30:
        deduction = min(20.0, 5.0 + (return_20d - 30) * 0.5)
        penalty += deduction
        risk_reasons.append(f"近20日涨幅较大，扣{deduction:.1f}分")
    if max_drawdown_60d is not None and max_drawdown_60d > 20:
        deduction = min(15.0, 5.0 + (max_drawdown_60d - 20) * 0.4)
        penalty += deduction
        risk_reasons.append(f"近60日回撤较大，扣{deduction:.1f}分")
    if valuation_percentile is not None and valuation_percentile > 80:
        deduction = min(15.0, 5.0 + (valuation_percentile - 80) * 0.5)
        penalty += deduction
        risk_reasons.append(f"估值处于历史高分位，扣{deduction:.1f}分")
    if negative_ocf_periods >= 2:
        deduction = min(20.0, 5.0 + negative_ocf_periods * 5)
        penalty += deduction
        risk_reasons.append(f"经营现金流连续为负，扣{deduction:.1f}分")
    if debt_to_assets is not None and debt_to_assets > 70:
        deduction = min(20.0, 5.0 + (debt_to_assets - 70) * 0.5)
        penalty += deduction
        risk_reasons.append(f"资产负债率偏高，扣{deduction:.1f}分")
    if goodwill_to_net_assets is not None and goodwill_to_net_assets > 20:
        deduction = min(15.0, 5.0 + (goodwill_to_net_assets - 20) * 0.3)
        penalty += deduction
        risk_reasons.append(f"商誉占净资产比例偏高，扣{deduction:.1f}分")
    if pledge_ratio is not None and pledge_ratio > 30:
        deduction = min(20.0, 5.0 + (pledge_ratio - 30) * 0.4)
        penalty += deduction
        risk_reasons.append(f"股权质押比例偏高，扣{deduction:.1f}分")

    return RiskResult(excluded=False, penalty=clamp_score(penalty), reasons=risk_reasons)
