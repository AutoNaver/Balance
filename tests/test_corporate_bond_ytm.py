import numpy as np
import pytest

from models.curve import DeterministicZeroCurve
from products.corporate_bond import CorporateBond


def _curve(rate: float = 0.03) -> DeterministicZeroCurve:
    return DeterministicZeroCurve(
        tenors=np.array([0.5, 1.0, 2.0, 5.0, 10.0]),
        zero_rates=np.array([rate, rate, rate, rate, rate]),
    )


def test_ytm_round_trip_from_price_continuous():
    curve = _curve(0.025)
    bond = CorporateBond(
        notional=1_000_000.0,
        maturity_years=5.0,
        coupon_type="fixed",
        fixed_rate=0.04,
        frequency="semi_annual",
        amortization_mode="bullet",
        annual_cpr=0.0,
    )
    target_price = bond.present_value({"model": curve})
    ytm = bond.yield_to_maturity(target_price, {"model": curve}, compounding="continuous")
    price_back = bond.price_from_yield(ytm, {"model": curve}, compounding="continuous")
    assert price_back == pytest.approx(target_price, rel=1e-10)


def test_price_decreases_with_higher_yield():
    curve = _curve(0.02)
    bond = CorporateBond(
        notional=500_000.0,
        maturity_years=4.0,
        coupon_type="fixed",
        fixed_rate=0.03,
        frequency="annual",
        amortization_mode="bullet",
    )
    low_y = bond.price_from_yield(0.01, {"model": curve})
    high_y = bond.price_from_yield(0.06, {"model": curve})
    assert high_y < low_y
