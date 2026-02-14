import numpy as np

from models.curve import DeterministicZeroCurve
from products.corporate_bond import CorporateBond


def _flat_curve(rate: float) -> DeterministicZeroCurve:
    return DeterministicZeroCurve(
        tenors=np.array([0.5, 1.0, 2.0, 5.0, 10.0]),
        zero_rates=np.array([rate, rate, rate, rate, rate]),
    )


def test_bullet_bond_has_principal_at_maturity():
    bond = CorporateBond(
        notional=1_000_000.0,
        maturity_years=2.0,
        coupon_type="fixed",
        fixed_rate=0.04,
        frequency="semi_annual",
        amortization_mode="bullet",
        annual_cpr=0.0,
    )
    cfs = bond.get_cashflows({"model": _flat_curve(0.02)})
    assert len(cfs) == 4
    assert cfs[-1].amount > cfs[0].amount


def test_linear_amortization_reduces_outstanding_over_time():
    bond = CorporateBond(
        notional=120_000.0,
        maturity_years=1.0,
        coupon_type="fixed",
        fixed_rate=0.03,
        frequency="quarterly",
        amortization_mode="linear",
    )
    cfs = bond.get_cashflows({"model": _flat_curve(0.02)})
    assert len(cfs) == 4
    assert cfs[0].amount > cfs[-1].amount


def test_floating_coupon_uses_forward_plus_spread():
    curve = _flat_curve(0.02)
    floater = CorporateBond(
        notional=500_000.0,
        maturity_years=1.0,
        coupon_type="floating",
        spread=0.01,
        frequency="quarterly",
        amortization_mode="bullet",
    )
    cfs = floater.get_cashflows({"model": curve})
    assert cfs[0].amount > 0.0


def test_constant_prepayment_reduces_pv_for_lender():
    curve = _flat_curve(0.02)
    no_pp = CorporateBond(
        notional=800_000.0,
        maturity_years=3.0,
        coupon_type="fixed",
        fixed_rate=0.05,
        frequency="semi_annual",
        amortization_mode="bullet",
        annual_cpr=0.0,
    )
    with_pp = CorporateBond(
        notional=800_000.0,
        maturity_years=3.0,
        coupon_type="fixed",
        fixed_rate=0.05,
        frequency="semi_annual",
        amortization_mode="bullet",
        annual_cpr=0.15,
    )
    assert with_pp.present_value({"model": curve}) < no_pp.present_value({"model": curve})
