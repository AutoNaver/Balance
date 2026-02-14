import numpy as np

from models.curve import DeterministicZeroCurve
from products.derivatives import InterestRateCapFloor


def _curve(rate: float) -> DeterministicZeroCurve:
    return DeterministicZeroCurve(
        tenors=np.array([0.5, 1.0, 2.0, 5.0]),
        zero_rates=np.array([rate, rate, rate, rate]),
    )


def test_cap_has_positive_value_when_strike_below_forward():
    curve = _curve(0.03)
    cap = InterestRateCapFloor(
        notional=1_000_000.0,
        strike=0.015,
        maturity_years=2.0,
        payment_frequency=4,
        volatility=0.20,
        is_cap=True,
    )
    assert cap.present_value({"model": curve}) > 0.0


def test_floor_has_positive_value_when_strike_above_forward():
    curve = _curve(0.01)
    floor = InterestRateCapFloor(
        notional=1_000_000.0,
        strike=0.03,
        maturity_years=2.0,
        payment_frequency=4,
        volatility=0.20,
        is_cap=False,
    )
    assert floor.present_value({"model": curve}) > 0.0
