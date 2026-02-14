from pathlib import Path

import numpy as np
import pytest

from models.curve import DeterministicZeroCurve
from products.mortgage import GermanFixedRateMortgageLoan
from products.mortgage_integration import (
    ConstantCPRPrepayment,
    IntegratedMortgageLoan,
    MortgageCashflowGenerator,
    MortgageConfig,
    load_zipper_mortgage_module,
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


def test_zipper_loader_imports_main_mortgage_if_present():
    zipper_root = Path(r"C:\Users\naver\OneDrive\Desktop\Zipper")
    if not (zipper_root / "main_mortgage.py").exists():
        pytest.skip("Local Zipper repository not present")
    module = load_zipper_mortgage_module(zipper_root)
    assert hasattr(module, "main")
