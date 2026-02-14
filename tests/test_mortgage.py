import numpy as np
import pytest

from models.curve import DeterministicZeroCurve
from products.mortgage import BehaviouralPrepaymentModel, GermanFixedRateMortgageLoan


def _flat_curve(rate: float = 0.02) -> DeterministicZeroCurve:
    return DeterministicZeroCurve(
        tenors=np.array([1.0, 5.0, 10.0, 20.0, 30.0]),
        zero_rates=np.array([rate, rate, rate, rate, rate]),
    )


def test_annuity_cashflows_decline_with_amortization():
    loan = GermanFixedRateMortgageLoan(
        notional=100_000.0,
        fixed_rate=0.03,
        maturity_years=2.0,
        repayment_type="annuity",
        payment_frequency="monthly",
    )
    cfs = loan.get_cashflows({"model": _flat_curve(0.02)})
    assert len(cfs) == 24
    assert cfs[0].amount == pytest.approx(cfs[-1].amount, rel=1e-3)


def test_constant_repayment_principal_component_is_constant():
    loan = GermanFixedRateMortgageLoan(
        notional=120_000.0,
        fixed_rate=0.03,
        maturity_years=1.0,
        repayment_type="constant_repayment",
        payment_frequency="monthly",
    )
    model = _flat_curve(0.02)
    cfs = loan.get_cashflows({"model": model})
    # Remove interest component to infer principal pattern.
    # With constant-repayment, monthly principal is near-constant except final rounding.
    inferred_principal = []
    balance = 120_000.0
    for cf in cfs:
        interest = balance * 0.03 / 12.0
        principal = max(0.0, cf.amount - interest)
        inferred_principal.append(principal)
        balance -= principal
    assert np.std(inferred_principal[:-1]) < 1e-2


def test_interest_only_then_amortizing_has_zero_principal_during_io_phase():
    loan = GermanFixedRateMortgageLoan(
        notional=200_000.0,
        fixed_rate=0.04,
        maturity_years=3.0,
        repayment_type="interest_only_then_amortizing",
        payment_frequency="monthly",
        interest_only_years=1.0,
    )
    cfs = loan.get_cashflows({"model": _flat_curve(0.03)})
    # First year should be close to interest-only coupon.
    first_coupon = 200_000.0 * 0.04 / 12.0
    assert cfs[0].amount == pytest.approx(first_coupon, rel=1e-3)
    assert cfs[11].amount == pytest.approx(first_coupon, rel=1e-3)
    assert cfs[12].amount > first_coupon


def test_prepayment_model_increases_with_incentive_age_and_seasonality():
    model = BehaviouralPrepaymentModel()
    base = model.cpr(
        fixed_rate=0.03,
        refinance_rate=0.03,
        age_years=0.0,
        maturity_years=10.0,
        month_index=6,
    )
    high_incentive = model.cpr(
        fixed_rate=0.05,
        refinance_rate=0.02,
        age_years=0.0,
        maturity_years=10.0,
        month_index=6,
    )
    older = model.cpr(
        fixed_rate=0.03,
        refinance_rate=0.03,
        age_years=8.0,
        maturity_years=10.0,
        month_index=6,
    )
    winter = model.cpr(
        fixed_rate=0.03,
        refinance_rate=0.03,
        age_years=0.0,
        maturity_years=10.0,
        month_index=12,
    )
    assert high_incentive > base
    assert older > base
    assert winter > base


def test_prepayments_reduce_total_pv_for_lender():
    no_prepay = GermanFixedRateMortgageLoan(
        notional=250_000.0,
        fixed_rate=0.045,
        maturity_years=10.0,
        repayment_type="annuity",
        payment_frequency="monthly",
        prepayment_model=None,
    )
    with_prepay = GermanFixedRateMortgageLoan(
        notional=250_000.0,
        fixed_rate=0.045,
        maturity_years=10.0,
        repayment_type="annuity",
        payment_frequency="monthly",
        prepayment_model=BehaviouralPrepaymentModel(base_cpr=0.05, max_cpr=0.35),
    )
    curve = _flat_curve(0.02)
    assert with_prepay.present_value({"model": curve}) < no_prepay.present_value({"model": curve})
