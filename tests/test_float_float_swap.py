import numpy as np
import pytest

from models.curve import DeterministicZeroCurve
from products.swap import FloatFloatSwap


def test_float_float_swap_zero_spread_same_freq_near_zero():
    curve = DeterministicZeroCurve(
        tenors=np.array([1.0, 3.0, 5.0]),
        zero_rates=np.array([0.02, 0.02, 0.02]),
    )
    swap = FloatFloatSwap(
        notional=1_000_000.0,
        maturity_years=3.0,
        pay_leg_frequency=4,
        receive_leg_frequency=4,
        pay_spread=0.0,
        receive_spread=0.0,
        pay_leg_sign=-1,
    )
    assert swap.present_value({"model": curve}) == pytest.approx(0.0, abs=1e-6)


def test_float_float_swap_spread_changes_sign():
    curve = DeterministicZeroCurve(
        tenors=np.array([1.0, 3.0, 5.0]),
        zero_rates=np.array([0.025, 0.025, 0.025]),
    )
    pay_high_spread = FloatFloatSwap(
        notional=1_000_000.0,
        maturity_years=3.0,
        pay_leg_frequency=4,
        receive_leg_frequency=4,
        pay_spread=0.005,
        receive_spread=0.0,
        pay_leg_sign=-1,
    )
    assert pay_high_spread.present_value({"model": curve}) < 0.0
