from app.formulas.final_score_formula import calculate_final_score, recommendation_level
from app.formulas.growth_formula import calculate_growth_score
from app.formulas.quality_formula import calculate_quality_score
from app.formulas.risk_formula import calculate_risk_result


def test_final_score_uses_v12_weights_and_level() -> None:
    score = calculate_final_score(
        quality_score=80,
        growth_score=70,
        valuation_score=60,
        momentum_score=90,
        capital_flow_score=75,
        leadership_score=50,
        risk_penalty=5,
    )

    assert score == 69.05
    assert recommendation_level(score) == "B"


def test_quality_score_matches_document_weights() -> None:
    score = calculate_quality_score(
        roe_percentile=80,
        roa_percentile=70,
        gross_margin_percentile=60,
        cashflow_quality_percentile=90,
        debt_to_assets=40,
    )

    assert score == 76.0


def test_growth_score_applies_v12_caps() -> None:
    score = calculate_growth_score(
        revenue_yoy_percentile=90,
        netprofit_yoy_percentile=90,
        revenue_cagr_percentile=90,
        quarter_improvement_score=90,
        revenue_yoy=-5,
        netprofit_yoy=40,
        negative_ocf_periods=2,
    )

    assert score == 51.0


def test_risk_formula_hard_filter_and_penalty() -> None:
    hard_filter = calculate_risk_result(is_st=True, listed_trading_days=200)
    penalty = calculate_risk_result(return_20d=50, debt_to_assets=85, pledge_ratio=45)

    assert hard_filter.excluded is True
    assert hard_filter.penalty == 100
    assert penalty.excluded is False
    assert penalty.penalty > 0
    assert len(penalty.reasons) == 3
