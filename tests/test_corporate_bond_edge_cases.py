import numpy as np

from models.curve import DeterministicZeroCurve
from products.corporate_bond import CorporateBond


def _curve(rate: float) -> DeterministicZeroCurve:
    return DeterministicZeroCurve(
        tenors=np.array([0.25, 0.5, 1.0, 2.0]),
        zero_rates=np.array([rate, rate, rate, rate]),
    )


def test_zero_coupon_zero_prepayment_bullet_matches_principal_discounted():
    curve = _curve(0.02)
    bond = CorporateBond(
        notional=100_000.0,
        maturity_years=1.0,
        coupon_type="fixed",
        fixed_rate=0.0,
        frequency="annual",
        amortization_mode="bullet",
        annual_cpr=0.0,
    )
    pv = bond.present_value({"model": curve})
    assert pv == curve.discount_factor(1.0) * 100_000.0


def test_very_short_maturity_quarterly_bond_has_single_period():
    curve = _curve(0.02)
    bond = CorporateBond(
        notional=50_000.0,
        maturity_years=0.25,
        coupon_type="fixed",
        fixed_rate=0.04,
        frequency="quarterly",
        amortization_mode="bullet",
    )
    cfs = bond.get_cashflows({"model": curve})
    assert len(cfs) == 1
    assert cfs[0].time == 0.25


def test_custom_amortization_schedule_applied():
    curve = _curve(0.02)
    custom = (20_000.0, 30_000.0, 50_000.0)
    bond = CorporateBond(
        notional=100_000.0,
        maturity_years=0.75,
        coupon_type="fixed",
        fixed_rate=0.0,
        frequency="quarterly",
        amortization_mode="custom",
        custom_amortization=custom,
        annual_cpr=0.0,
    )
    cfs = bond.get_cashflows({"model": curve})
    principals = [cf.amount for cf in cfs]
    assert principals == list(custom)
