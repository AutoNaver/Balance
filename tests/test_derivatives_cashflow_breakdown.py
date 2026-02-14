import numpy as np
import pytest

from models.curve import DeterministicZeroCurve
from models.market import DeterministicFXCurve
from products.derivatives import CrossCurrencySwap, FXForward, FXSwap


def _curve(rate: float) -> DeterministicZeroCurve:
    return DeterministicZeroCurve(
        tenors=np.array([0.5, 1.0, 2.0, 5.0]),
        zero_rates=np.array([rate, rate, rate, rate]),
    )


def test_fx_forward_leg_cashflow_matches_get_cashflows():
    curve = _curve(0.02)
    fx_curve = DeterministicFXCurve(
        tenors=np.array([0.5, 1.0, 2.0]),
        fx_forwards=np.array([1.10, 1.12, 1.15]),
    )
    trade = FXForward(notional_foreign=1_000_000.0, strike=1.08, maturity_years=1.0)
    legs = trade.leg_cashflows({"model": curve, "fx_curve": fx_curve})
    assert legs["net_cashflows"] == trade.get_cashflows({"model": curve, "fx_curve": fx_curve})


def test_fx_swap_leg_cashflows_reconcile_to_net():
    domestic = _curve(0.03)
    foreign = _curve(0.01)
    swap = FXSwap(
        notional_foreign=1_000_000.0,
        near_rate=1.10,
        far_rate=None,
        near_maturity_years=0.0,
        far_maturity_years=1.0,
        pay_foreign_receive_domestic=True,
    )
    legs = swap.leg_cashflows({"model": domestic, "foreign_model": foreign})
    net = legs["near_leg_cashflows"] + legs["far_leg_cashflows"]
    assert legs["net_cashflows"] == net
    assert swap.get_cashflows({"model": domestic, "foreign_model": foreign}) == net


def test_ccs_leg_cashflows_reconcile_to_total_and_pv():
    domestic = _curve(0.02)
    foreign = _curve(0.015)
    fx = DeterministicFXCurve(
        tenors=np.array([0.5, 1.0, 2.0]),
        fx_forwards=np.array([1.10, 1.11, 1.12]),
    )
    trade = CrossCurrencySwap(
        domestic_notional=1_000_000.0,
        foreign_notional=900_000.0,
        maturity_years=2.0,
        domestic_frequency=2,
        foreign_frequency=2,
        domestic_fixed_rate=0.025,
        foreign_fixed_rate=0.02,
        pay_domestic_receive_foreign=True,
        mark_to_market=True,
    )

    scenario = {"model": domestic, "foreign_model": foreign, "fx_curve": fx}
    legs = trade.leg_cashflows(scenario)

    rebuilt = (
        legs["notional_exchange_cashflows"]
        + legs["domestic_leg_cashflows"]
        + legs["foreign_leg_cashflows"]
        + legs["reset_exchange_cashflows"]
    )
    assert legs["net_cashflows"] == rebuilt
    assert trade.get_cashflows(scenario) == rebuilt

    pv_from_legs = sum(cf.amount * domestic.discount_factor(cf.time) for cf in rebuilt)
    assert trade.present_value(scenario) == pytest.approx(pv_from_legs, rel=1e-12)
