import numpy as np
import pytest

from models.curve import DeterministicZeroCurve
from models.market import DeterministicFXCurve, DeterministicHazardCurve
from products.derivatives import CreditDefaultSwap, EuropeanSwaption, FXForward, FXSwap


def _curve(rate: float = 0.02) -> DeterministicZeroCurve:
    return DeterministicZeroCurve(
        tenors=np.array([0.5, 1.0, 2.0, 5.0, 10.0]),
        zero_rates=np.array([rate, rate, rate, rate, rate]),
    )


def test_fx_forward_positive_when_forward_above_strike():
    curve = _curve(0.02)
    fx_curve = DeterministicFXCurve(
        tenors=np.array([0.5, 1.0, 2.0]),
        fx_forwards=np.array([1.10, 1.12, 1.15]),
    )
    trade = FXForward(notional_foreign=1_000_000.0, strike=1.08, maturity_years=1.0)
    assert trade.present_value({"model": curve, "fx_curve": fx_curve}) > 0.0


def test_fx_swap_valued_as_discounted_leg_difference():
    curve = _curve(0.02)
    swap = FXSwap(
        notional_foreign=1_000_000.0,
        near_rate=1.10,
        far_rate=1.11,
        near_maturity_years=0.25,
        far_maturity_years=1.0,
    )
    pv = swap.present_value({"model": curve})
    assert pv != 0.0


def test_swaption_payer_and_receiver_have_positive_values():
    curve = _curve(0.025)
    payer = EuropeanSwaption(
        notional=2_000_000.0,
        strike=0.025,
        option_maturity_years=1.0,
        swap_tenor_years=5.0,
        fixed_leg_frequency=1,
        volatility=0.20,
        is_payer=True,
    )
    receiver = EuropeanSwaption(
        notional=2_000_000.0,
        strike=0.025,
        option_maturity_years=1.0,
        swap_tenor_years=5.0,
        fixed_leg_frequency=1,
        volatility=0.20,
        is_payer=False,
    )
    assert payer.present_value({"model": curve}) >= 0.0
    assert receiver.present_value({"model": curve}) >= 0.0


def test_cds_value_decreases_when_spread_is_high_for_protection_buyer():
    curve = _curve(0.02)
    hazard = DeterministicHazardCurve(
        tenors=np.array([1.0, 3.0, 5.0, 10.0]),
        hazard_rates=np.array([0.01, 0.012, 0.014, 0.016]),
    )
    low_spread = CreditDefaultSwap(notional=1_000_000.0, spread_bps=50.0, maturity_years=5.0)
    high_spread = CreditDefaultSwap(notional=1_000_000.0, spread_bps=300.0, maturity_years=5.0)
    pv_low = low_spread.present_value({"model": curve, "hazard_curve": hazard})
    pv_high = high_spread.present_value({"model": curve, "hazard_curve": hazard})
    assert pv_high < pv_low


def test_cds_leg_decomposition_reconciles_total_pv():
    curve = _curve(0.02)
    hazard = DeterministicHazardCurve(
        tenors=np.array([1.0, 3.0, 5.0, 10.0]),
        hazard_rates=np.array([0.01, 0.012, 0.014, 0.016]),
    )
    cds = CreditDefaultSwap(notional=1_000_000.0, spread_bps=150.0, maturity_years=5.0)
    legs = cds.leg_present_values({"model": curve, "hazard_curve": hazard})
    total = cds.present_value({"model": curve, "hazard_curve": hazard})
    assert total == pytest.approx(legs["protection_leg_pv"] - legs["premium_leg_pv"], rel=1e-12)
