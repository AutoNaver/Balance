import numpy as np
import pytest

from models.curve import DeterministicZeroCurve
from products.mortgage import BehaviouralPrepaymentModel, GermanFixedRateMortgageLoan
from products.mortgage_integration import (
    CleanRoomBehaviouralPrepayment,
    ConstantCPRPrepayment,
    IntegratedGermanFixedRateMortgageLoan,
    IntegratedMortgageLoan,
    MortgageCashflowGenerator,
    MortgageConfig,
)


def _curve(rate: float = 0.02) -> DeterministicZeroCurve:
    return DeterministicZeroCurve(
        tenors=np.array([1.0, 5.0, 10.0, 20.0]),
        zero_rates=np.array([rate, rate, rate, rate]),
    )


def test_integrated_mortgage_matches_existing_annuity_without_prepayment():
    curve = _curve(0.02)
    existing = GermanFixedRateMortgageLoan(
        notional=200000.0,
        fixed_rate=0.035,
        maturity_years=10.0,
        repayment_type="annuity",
        payment_frequency="monthly",
        prepayment_model=None,
    )
    integrated = IntegratedMortgageLoan(
        cashflow_generator=MortgageCashflowGenerator(
            MortgageConfig(
                notional=200000.0,
                fixed_rate=0.035,
                maturity_years=10.0,
                repayment_type="annuity",
                payment_frequency="monthly",
            ),
            prepayment_model=ConstantCPRPrepayment(cpr=0.0),
        )
    )
    assert integrated.present_value({"model": curve}) == pytest.approx(existing.present_value({"model": curve}), rel=1e-8)


@pytest.mark.parametrize(
    ("repayment_type", "interest_only_years"),
    [
        ("annuity", 0.0),
        ("constant_repayment", 0.0),
        ("interest_only_then_amortizing", 1.0),
    ],
)
def test_integrated_mortgage_cashflow_parity_across_repayment_types(repayment_type: str, interest_only_years: float):
    curve = _curve(0.02)
    existing = GermanFixedRateMortgageLoan(
        notional=250000.0,
        fixed_rate=0.033,
        maturity_years=8.0,
        repayment_type=repayment_type,
        payment_frequency="monthly",
        interest_only_years=interest_only_years,
        prepayment_model=None,
    )
    integrated = IntegratedMortgageLoan(
        cashflow_generator=MortgageCashflowGenerator(
            MortgageConfig(
                notional=250000.0,
                fixed_rate=0.033,
                maturity_years=8.0,
                repayment_type=repayment_type,
                payment_frequency="monthly",
                interest_only_years=interest_only_years,
            ),
            prepayment_model=ConstantCPRPrepayment(cpr=0.0),
        )
    )
    existing_cfs = existing.get_cashflows({"model": curve})
    integrated_cfs = integrated.get_cashflows({"model": curve})
    assert len(existing_cfs) == len(integrated_cfs)
    for e, i in zip(existing_cfs, integrated_cfs):
        assert i.time == pytest.approx(e.time, rel=1e-12)
        assert i.amount == pytest.approx(e.amount, rel=1e-8)
    assert integrated.present_value({"model": curve}) == pytest.approx(existing.present_value({"model": curve}), rel=1e-8)


def test_integrated_cleanroom_behavioural_prepayment_matches_german_model():
    curve = _curve(0.02)
    params = dict(
        base_cpr=0.015,
        incentive_weight=0.60,
        age_weight=0.25,
        seasonality_weight=0.15,
        incentive_slope=12.0,
        age_slope=1.0,
        seasonality_factors=(1.10, 1.10, 1.00, 0.98, 0.98, 1.00, 1.02, 1.02, 1.00, 1.00, 1.08, 1.12),
        min_cpr=0.0,
        max_cpr=0.30,
    )
    existing = GermanFixedRateMortgageLoan(
        notional=350_000.0,
        fixed_rate=0.037,
        maturity_years=15.0,
        repayment_type="annuity",
        payment_frequency="monthly",
        day_count="30/360",
        prepayment_model=BehaviouralPrepaymentModel(**params),
        start_month=1,
    )
    integrated = IntegratedMortgageLoan(
        cashflow_generator=MortgageCashflowGenerator(
            MortgageConfig(
                notional=350_000.0,
                fixed_rate=0.037,
                maturity_years=15.0,
                repayment_type="annuity",
                payment_frequency="monthly",
                day_count="30/360",
                start_month=1,
            ),
            prepayment_model=CleanRoomBehaviouralPrepayment(**params),
        )
    )
    assert integrated.present_value({"model": curve}) == pytest.approx(existing.present_value({"model": curve}), rel=1e-8)


def test_integrated_german_mortgage_wrapper_matches_existing_model():
    curve = _curve(0.02)
    params = dict(
        base_cpr=0.02,
        incentive_weight=0.6,
        age_weight=0.25,
        seasonality_weight=0.15,
        incentive_slope=12.0,
        age_slope=1.0,
        seasonality_factors=(1.10, 1.10, 1.00, 0.98, 0.98, 1.00, 1.02, 1.02, 1.00, 1.00, 1.08, 1.12),
        min_cpr=0.0,
        max_cpr=0.30,
    )
    existing = GermanFixedRateMortgageLoan(
        notional=300_000.0,
        fixed_rate=0.036,
        maturity_years=12.0,
        repayment_type="interest_only_then_amortizing",
        payment_frequency="monthly",
        interest_only_years=1.0,
        day_count="30/360",
        prepayment_model=BehaviouralPrepaymentModel(**params),
        start_month=2,
    )
    replicated = IntegratedGermanFixedRateMortgageLoan(
        notional=300_000.0,
        fixed_rate=0.036,
        maturity_years=12.0,
        repayment_type="interest_only_then_amortizing",
        payment_frequency="monthly",
        interest_only_years=1.0,
        day_count="30/360",
        prepayment_model=CleanRoomBehaviouralPrepayment(**params),
        start_month=2,
    )
    assert replicated.present_value({"model": curve}) == pytest.approx(existing.present_value({"model": curve}), rel=1e-8)
