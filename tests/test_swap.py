import numpy as np
import pytest

from models.curve import DeterministicZeroCurve
from products.swap import FixedFloatSwap


def test_par_swap_near_zero_pv():
    curve = DeterministicZeroCurve(
        tenors=np.array([1.0, 3.0, 5.0]),
        zero_rates=np.array([0.02, 0.02, 0.02]),
    )
    swap = FixedFloatSwap(
        notional=1_000_000.0,
        fixed_rate=0.02,
        maturity_years=5.0,
        fixed_frequency=1,
        float_frequency=1,
        pay_fixed=True,
    )
    pv = swap.present_value({"model": curve})
    assert abs(pv) < 1_500.0


def test_pay_fixed_benefits_from_lower_rates_less_than_receive_fixed():
    curve = DeterministicZeroCurve(
        tenors=np.array([1.0, 3.0, 5.0]),
        zero_rates=np.array([0.03, 0.03, 0.03]),
    )
    pay_fixed = FixedFloatSwap(
        notional=1_000_000.0,
        fixed_rate=0.025,
        maturity_years=3.0,
        fixed_frequency=2,
        float_frequency=4,
        pay_fixed=True,
    )
    receive_fixed = FixedFloatSwap(
        notional=1_000_000.0,
        fixed_rate=0.025,
        maturity_years=3.0,
        fixed_frequency=2,
        float_frequency=4,
        pay_fixed=False,
    )
    assert pay_fixed.present_value({"model": curve}) == pytest.approx(
        -receive_fixed.present_value({"model": curve})
    )
