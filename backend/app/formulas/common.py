from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from math import isfinite
from typing import Any


def to_float(value: Any) -> float | None:
    """把数据库 Decimal、字符串等安全转换为 float；缺失或非法值返回 None。"""

    if value is None:
        return None
    if isinstance(value, Decimal):
        value = float(value)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def clamp_score(value: float | None, min_value: float = 0.0, max_value: float = 100.0) -> float:
    """所有公式最终统一限制在 0-100 分，避免极端值污染综合评分。"""

    if value is None or not isfinite(value):
        return 0.0
    return round(max(min_value, min(max_value, value)), 4)


def weighted_score(parts: Iterable[tuple[float | None, float]]) -> float:
    """按 V1.2 权重聚合子因子；缺失子项按 0 分处理，不把缺失误当优势。"""

    return clamp_score(sum(clamp_score(score) * weight for score, weight in parts))


def percentile_score(value: float | None, peers: Iterable[float | None], higher_is_better: bool = True) -> float:
    """计算截面分位分，行业内排名等场景使用；默认数值越高越好。"""

    number = to_float(value)
    peer_values = sorted(item for item in (to_float(peer) for peer in peers) if item is not None)
    if number is None or not peer_values:
        return 0.0

    less_or_equal = sum(1 for item in peer_values if item <= number)
    percentile = less_or_equal / len(peer_values) * 100
    return clamp_score(percentile if higher_is_better else 100 - percentile)


def band_health_score(value: float | None, ideal_low: float, ideal_high: float, hard_low: float, hard_high: float) -> float:
    """区间健康分：落在理想区间给满分，偏离越多分数越低。"""

    number = to_float(value)
    if number is None:
        return 0.0
    if ideal_low <= number <= ideal_high:
        return 100.0
    if number < hard_low or number > hard_high:
        return 0.0
    if number < ideal_low:
        return clamp_score((number - hard_low) / (ideal_low - hard_low) * 100)
    return clamp_score((hard_high - number) / (hard_high - ideal_high) * 100)
