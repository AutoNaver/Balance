import json
from pathlib import Path

import numpy as np
import pytest

from models.curve import DeterministicZeroCurve
from models.market import DeterministicHazardCurve
from products.corporate_bond import CorporateBond
from products.derivatives import CreditDefaultSwap, EuropeanSwaption, InterestRateCapFloor
from products.mortgage import BehaviouralPrepaymentModel, GermanFixedRateMortgageLoan
from products.mortgage_integration import ConstantCPRPrepayment, IntegratedMortgageLoan, MortgageCashflowGenerator, MortgageConfig
from products.swap import FixedFloatSwap, FloatFloatSwap


def _curve() -> DeterministicZeroCurve:
    return DeterministicZeroCurve(
        tenors=np.array([0.5, 1.0, 2.0, 5.0, 10.0]),
        zero_rates=np.array([0.02, 0.021, 0.022, 0.024, 0.025]),
    )


def _hazard() -> DeterministicHazardCurve:
    return DeterministicHazardCurve(
        tenors=np.array([1.0, 3.0, 5.0, 10.0]),
        hazard_rates=np.array([0.01, 0.012, 0.013, 0.015]),
    )


def test_deterministic_benchmarks_match_targets():
    root = Path(__file__).resolve().parents[1]
    targets = json.loads((root / "data" / "benchmarks" / "deterministic_valuation_targets.json").read_text(encoding="utf-8"))

    curve = _curve()
    hazard = _hazard()

    corporate = CorporateBond(
        notional=500_000.0,
        maturity_years=5.0,
        coupon_type="fixed",
        fixed_rate=0.045,
        frequency="semi_annual",
        amortization_mode="linear",
        annual_cpr=0.03,
    )
    mortgage = IntegratedMortgageLoan(
        cashflow_generator=MortgageCashflowGenerator(
            MortgageConfig(
                notional=280_000.0,
                fixed_rate=0.034,
                maturity_years=12.0,
                repayment_type="annuity",
                payment_frequency="monthly",
            ),
            prepayment_model=ConstantCPRPrepayment(cpr=0.01),
        )
    )
    fixed_swap = FixedFloatSwap(
        notional=2_000_000.0,
        fixed_rate=0.029,
        maturity_years=4.0,
        fixed_frequency=2,
        float_frequency=4,
        pay_fixed=True,
    )
    float_float = FloatFloatSwap(
        notional=1_000_000.0,
        maturity_years=4.0,
        pay_leg_frequency=4,
        receive_leg_frequency=2,
        pay_spread=0.001,
        receive_spread=0.0,
        pay_leg_sign=-1,
    )
    cds = CreditDefaultSwap(notional=1_000_000.0, spread_bps=150.0, maturity_years=5.0, payment_frequency=4, recovery_rate=0.4)
    swaption_payer = EuropeanSwaption(
        notional=2_000_000.0,
        strike=0.025,
        option_maturity_years=1.0,
        swap_tenor_years=5.0,
        fixed_leg_frequency=1,
        volatility=0.20,
        is_payer=True,
    )
    swaption_receiver = EuropeanSwaption(
        notional=2_000_000.0,
        strike=0.025,
        option_maturity_years=1.0,
        swap_tenor_years=5.0,
        fixed_leg_frequency=1,
        volatility=0.20,
        is_payer=False,
    )
    cap = InterestRateCapFloor(notional=1_000_000.0, strike=0.025, maturity_years=3.0, payment_frequency=4, volatility=0.2, is_cap=True)

    assert corporate.present_value({"model": curve}) == pytest.approx(targets["corporate_bond_linear_cpr3"], rel=1e-10)
    ytm = corporate.yield_to_maturity(targets["corporate_bond_linear_cpr3"], {"model": curve}, compounding="continuous")
    assert ytm == pytest.approx(targets["corporate_bond_linear_cpr3_ytm_cont"], rel=1e-10)
    assert mortgage.present_value({"model": curve}) == pytest.approx(targets["integrated_mortgage_annuity_cpr1"], rel=1e-10)
    assert fixed_swap.present_value({"model": curve}) == pytest.approx(targets["fixed_float_swap"], rel=1e-10)
    assert float_float.present_value({"model": curve}) == pytest.approx(targets["float_float_swap"], rel=1e-10)
    legs = cds.leg_present_values({"model": curve, "hazard_curve": hazard})
    assert cds.present_value({"model": curve, "hazard_curve": hazard}) == pytest.approx(targets["cds_ref"], rel=1e-10)
    assert legs["premium_leg_pv"] == pytest.approx(targets["cds_premium_leg_ref"], rel=1e-10)
    assert legs["protection_leg_pv"] == pytest.approx(targets["cds_protection_leg_ref"], rel=1e-10)
    assert swaption_payer.present_value({"model": curve}) == pytest.approx(targets["swaption_payer_ref"], rel=1e-10)
    assert swaption_receiver.present_value({"model": curve}) == pytest.approx(targets["swaption_receiver_ref"], rel=1e-10)
    assert cap.present_value({"model": curve}) == pytest.approx(targets["cap"], rel=1e-10)

    german_loan = GermanFixedRateMortgageLoan(
        notional=350_000.0,
        fixed_rate=0.037,
        maturity_years=15.0,
        repayment_type="annuity",
        payment_frequency="monthly",
        interest_only_years=0.0,
        day_count="30/360",
        prepayment_model=BehaviouralPrepaymentModel(
            base_cpr=0.015,
            incentive_weight=0.60,
            age_weight=0.25,
            seasonality_weight=0.15,
            incentive_slope=12.0,
            age_slope=1.0,
            seasonality_factors=(1.10, 1.10, 1.00, 0.98, 0.98, 1.00, 1.02, 1.02, 1.00, 1.00, 1.08, 1.12),
            min_cpr=0.0,
            max_cpr=0.30,
        ),
        start_month=1,
    )
    assert german_loan.present_value({"model": curve}) == pytest.approx(targets["german_mortgage_annuity_behavioural"], rel=1e-10)

    german_const = GermanFixedRateMortgageLoan(
        notional=250_000.0,
        fixed_rate=0.033,
        maturity_years=8.0,
        repayment_type="constant_repayment",
        payment_frequency="monthly",
        interest_only_years=0.0,
        day_count="30/360",
        prepayment_model=None,
    )
    german_io = GermanFixedRateMortgageLoan(
        notional=250_000.0,
        fixed_rate=0.033,
        maturity_years=8.0,
        repayment_type="interest_only_then_amortizing",
        payment_frequency="monthly",
        interest_only_years=1.0,
        day_count="30/360",
        prepayment_model=None,
    )
    assert german_const.present_value({"model": curve}) == pytest.approx(targets["german_mortgage_constant_repayment"], rel=1e-10)
    assert german_io.present_value({"model": curve}) == pytest.approx(
        targets["german_mortgage_interest_only_then_amortizing"], rel=1e-10
    )
