import numpy as np

from engine.scenario import Scenario
from engine.valuation import ValuationEngine
from models.curve import DeterministicZeroCurve
from products.bond import FixedRateBond


def _curve(rate: float) -> DeterministicZeroCurve:
    return DeterministicZeroCurve(
        tenors=np.array([1.0, 3.0, 5.0]),
        zero_rates=np.array([rate, rate, rate]),
    )


def test_expected_shortfall_is_at_least_var():
    products = [FixedRateBond(notional=1_000_000.0, coupon_rate=0.03, maturity_years=3.0, coupon_frequency=2)]
    scenarios = [
        Scenario(name="parallel_shift_-100bps", model=_curve(0.01)),
        Scenario(name="parallel_shift_+0bps", model=_curve(0.02)),
        Scenario(name="parallel_shift_+100bps", model=_curve(0.03)),
    ]
    result = ValuationEngine(products).value(scenarios)
    var = result.pvat_risk(0.95)
    es = result.expected_shortfall(0.95)
    assert es >= var


def test_value_with_contributions_sums_to_total():
    products = [
        FixedRateBond(notional=800_000.0, coupon_rate=0.03, maturity_years=3.0, coupon_frequency=2),
        FixedRateBond(notional=200_000.0, coupon_rate=0.025, maturity_years=2.0, coupon_frequency=1),
    ]
    scenarios = [Scenario(name="parallel_shift_+0bps", model=_curve(0.02))]
    result, contrib = ValuationEngine(products).value_with_contributions(scenarios)
    total = result.scenario_pv["parallel_shift_+0bps"]
    assert abs(sum(contrib["parallel_shift_+0bps"].values()) - total) < 1e-8


def test_grouped_contributions_sums_to_total():
    products = [
        FixedRateBond(notional=500_000.0, coupon_rate=0.03, maturity_years=3.0, coupon_frequency=2),
        FixedRateBond(notional=300_000.0, coupon_rate=0.025, maturity_years=2.0, coupon_frequency=1),
    ]
    scenarios = [Scenario(name="parallel_shift_+0bps", model=_curve(0.02))]
    result, grouped = ValuationEngine(products).value_with_grouped_contributions(scenarios)
    total = result.scenario_pv["parallel_shift_+0bps"]
    assert abs(sum(grouped["parallel_shift_+0bps"].values()) - total) < 1e-8
    assert "FixedRateBond" in grouped["parallel_shift_+0bps"]


def test_risk_profile_contains_requested_confidences():
    products = [FixedRateBond(notional=1_000_000.0, coupon_rate=0.03, maturity_years=3.0, coupon_frequency=2)]
    scenarios = [
        Scenario(name="parallel_shift_-100bps", model=_curve(0.01)),
        Scenario(name="parallel_shift_+0bps", model=_curve(0.02)),
        Scenario(name="parallel_shift_+100bps", model=_curve(0.03)),
    ]
    result = ValuationEngine(products).value(scenarios)
    profile = result.risk_profile([0.95, 0.99])
    assert "0.9500" in profile
    assert "0.9900" in profile
    assert profile["0.9900"]["expected_shortfall"] >= profile["0.9900"]["pvat_risk"]
