import numpy as np
import pytest

from models.curve import DeterministicZeroCurve
from products.bond import FixedRateBond
from products.callable_bond import CallableFixedRateBond


def _curve(rate: float = 0.02) -> DeterministicZeroCurve:
    return DeterministicZeroCurve(
        tenors=np.array([0.5, 1.0, 2.0, 5.0, 10.0]),
        zero_rates=np.array([rate, rate, rate, rate, rate]),
    )


def test_non_callable_case_tracks_fixed_bond_price():
    curve = _curve(0.02)
    vanilla = FixedRateBond(notional=1_000_000.0, coupon_rate=0.03, maturity_years=5.0, coupon_frequency=1)
    callable_bond = CallableFixedRateBond(
        notional=1_000_000.0,
        coupon_rate=0.03,
        maturity_years=5.0,
        coupon_frequency=1,
        call_schedule=(),
        short_rate_volatility=0.0,
    )
    pv_vanilla = vanilla.present_value({"model": curve})
    pv_callable = callable_bond.present_value({"model": curve})
    assert pv_callable == pytest.approx(pv_vanilla, rel=5e-3)


def test_deep_itm_call_reduces_value_vs_non_callable():
    curve = _curve(0.01)
    non_callable = CallableFixedRateBond(
        notional=1_000_000.0,
        coupon_rate=0.06,
        maturity_years=5.0,
        coupon_frequency=1,
        call_schedule=(),
        short_rate_volatility=0.01,
    )
    callable_bond = CallableFixedRateBond(
        notional=1_000_000.0,
        coupon_rate=0.06,
        maturity_years=5.0,
        coupon_frequency=1,
        call_schedule=((2.0, 1_000_000.0), (3.0, 1_000_000.0), (4.0, 1_000_000.0)),
        short_rate_volatility=0.01,
    )
    pv_nc = non_callable.present_value({"model": curve})
    pv_c = callable_bond.present_value({"model": curve})
    assert pv_c < pv_nc


def test_oas_solver_round_trip_and_monotonicity():
    curve = _curve(0.02)
    bond = CallableFixedRateBond(
        notional=1_000_000.0,
        coupon_rate=0.04,
        maturity_years=5.0,
        coupon_frequency=1,
        call_schedule=((3.0, 1_000_000.0),),
    )
    p0 = bond.price_with_oas(0.0, {"model": curve})
    p_up = bond.price_with_oas(0.01, {"model": curve})
    assert p_up < p0

    solved = bond.option_adjusted_spread(target_dirty_price=p0, scenario={"model": curve})
    assert solved == pytest.approx(0.0, abs=1e-6)
