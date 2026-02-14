import numpy as np

from models.curve import DeterministicZeroCurve
from models.market import DeterministicForwardCurve
from products.corporate_bond import CorporateBond


def _discount_curve(rate: float) -> DeterministicZeroCurve:
    return DeterministicZeroCurve(
        tenors=np.array([0.5, 1.0, 2.0, 5.0]),
        zero_rates=np.array([rate, rate, rate, rate]),
    )


def test_floating_corporate_bond_can_use_separate_forward_curve():
    discount = _discount_curve(0.02)
    forward = DeterministicForwardCurve(
        tenors=np.array([0.5, 1.0, 2.0, 5.0]),
        forward_rates=np.array([0.03, 0.03, 0.03, 0.03]),
    )
    bond = CorporateBond(
        notional=1_000_000.0,
        maturity_years=2.0,
        coupon_type="floating",
        spread=0.002,
        frequency="semi_annual",
        amortization_mode="bullet",
    )
    pv_with_forward = bond.present_value({"model": discount, "forward_model": forward})
    pv_without_forward = bond.present_value({"model": discount})
    assert pv_with_forward != pv_without_forward
