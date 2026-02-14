import numpy as np
import pytest

from models.curve import DeterministicZeroCurve
from products.derivatives import FXSwap


def _curve(rate: float) -> DeterministicZeroCurve:
    return DeterministicZeroCurve(
        tenors=np.array([0.5, 1.0, 2.0, 5.0]),
        zero_rates=np.array([rate, rate, rate, rate]),
    )


def test_fx_swap_implied_far_rate_matches_interest_parity_formula():
    domestic = _curve(0.03)
    foreign = _curve(0.01)
    spot = 1.10
    swap = FXSwap(
        notional_foreign=1_000_000.0,
        near_rate=spot,
        far_rate=None,
        near_maturity_years=0.0,
        far_maturity_years=1.0,
        pay_foreign_receive_domestic=True,
    )
    cfs = swap.get_cashflows({"model": domestic, "foreign_model": foreign})
    implied_far = -cfs[1].amount / swap.notional_foreign
    expected_far = spot * foreign.discount_factor(1.0) / domestic.discount_factor(1.0)
    assert implied_far == pytest.approx(expected_far, rel=1e-12)


def test_fx_swap_requires_foreign_curve_if_far_rate_missing():
    domestic = _curve(0.02)
    swap = FXSwap(
        notional_foreign=1_000_000.0,
        near_rate=1.10,
        far_rate=None,
        near_maturity_years=0.0,
        far_maturity_years=1.0,
    )
    with pytest.raises(TypeError):
        swap.present_value({"model": domestic})


def test_fx_swap_implied_far_rate_supports_broken_dates():
    domestic = _curve(0.025)
    foreign = _curve(0.01)
    near = 0.30
    far = 1.10
    near_rate = 1.07
    swap = FXSwap(
        notional_foreign=1_000_000.0,
        near_rate=near_rate,
        far_rate=None,
        near_maturity_years=near,
        far_maturity_years=far,
    )
    cfs = swap.get_cashflows({"model": domestic, "foreign_model": foreign})
    implied_far = -cfs[1].amount / swap.notional_foreign
    expected_far = near_rate * (
        foreign.discount_factor(far) / foreign.discount_factor(near)
    ) / (
        domestic.discount_factor(far) / domestic.discount_factor(near)
    )
    assert implied_far == pytest.approx(expected_far, rel=1e-12)
