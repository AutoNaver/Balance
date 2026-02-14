import numpy as np

from models.curve import DeterministicZeroCurve
from products.bond import FixedRateBond


def test_bond_pv_positive():
    curve = DeterministicZeroCurve(
        tenors=np.array([1.0, 3.0, 5.0]),
        zero_rates=np.array([0.02, 0.022, 0.025]),
    )
    bond = FixedRateBond(notional=1_000_000.0, coupon_rate=0.03, maturity_years=3.0, coupon_frequency=2)
    pv = bond.present_value({"model": curve})
    assert pv > 0.0


def test_higher_rates_reduce_bond_pv():
    low_curve = DeterministicZeroCurve(
        tenors=np.array([1.0, 3.0, 5.0]),
        zero_rates=np.array([0.015, 0.02, 0.022]),
    )
    high_curve = DeterministicZeroCurve(
        tenors=np.array([1.0, 3.0, 5.0]),
        zero_rates=np.array([0.03, 0.035, 0.038]),
    )
    bond = FixedRateBond(notional=500_000.0, coupon_rate=0.025, maturity_years=5.0, coupon_frequency=1)

    assert bond.present_value({"model": high_curve}) < bond.present_value({"model": low_curve})
