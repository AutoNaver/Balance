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


def _fx_curve() -> DeterministicFXCurve:
    return DeterministicFXCurve(
        tenors=np.array([0.5, 1.0, 2.0]),
        fx_forwards=np.array([1.10, 1.11, 1.12]),
    )


def test_fx_forward_pay_receive_symmetry():
    curve = _curve(0.02)
    fx = _fx_curve()
    pay_foreign = FXForward(notional_foreign=1_000_000.0, strike=1.10, maturity_years=1.0, pay_foreign_receive_domestic=True)
    receive_foreign = FXForward(notional_foreign=1_000_000.0, strike=1.10, maturity_years=1.0, pay_foreign_receive_domestic=False)
    pv1 = pay_foreign.present_value({"model": curve, "fx_curve": fx})
    pv2 = receive_foreign.present_value({"model": curve, "fx_curve": fx})
    assert pv1 == pytest.approx(-pv2, rel=1e-12)


def test_fx_swap_pay_receive_symmetry():
    curve = _curve(0.02)
    pay_foreign = FXSwap(notional_foreign=1_000_000.0, near_rate=1.10, far_rate=1.11, near_maturity_years=0.25, far_maturity_years=1.0, pay_foreign_receive_domestic=True)
    receive_foreign = FXSwap(notional_foreign=1_000_000.0, near_rate=1.10, far_rate=1.11, near_maturity_years=0.25, far_maturity_years=1.0, pay_foreign_receive_domestic=False)
    pv1 = pay_foreign.present_value({"model": curve})
    pv2 = receive_foreign.present_value({"model": curve})
    assert pv1 == pytest.approx(-pv2, rel=1e-12)


def test_ccs_pay_receive_symmetry():
    domestic = _curve(0.02)
    foreign = _curve(0.015)
    fx = _fx_curve()
    pay_dom = CrossCurrencySwap(
        domestic_notional=1_000_000.0,
        foreign_notional=900_000.0,
        maturity_years=2.0,
        domestic_frequency=2,
        foreign_frequency=2,
        domestic_fixed_rate=0.024,
        foreign_fixed_rate=0.018,
        pay_domestic_receive_foreign=True,
        exchange_notionals=True,
        mark_to_market=False,
    )
    recv_dom = CrossCurrencySwap(
        domestic_notional=1_000_000.0,
        foreign_notional=900_000.0,
        maturity_years=2.0,
        domestic_frequency=2,
        foreign_frequency=2,
        domestic_fixed_rate=0.024,
        foreign_fixed_rate=0.018,
        pay_domestic_receive_foreign=False,
        exchange_notionals=True,
        mark_to_market=False,
    )
    pv1 = pay_dom.present_value({"model": domestic, "foreign_model": foreign, "fx_curve": fx})
    pv2 = recv_dom.present_value({"model": domestic, "foreign_model": foreign, "fx_curve": fx})
    assert pv1 == pytest.approx(-pv2, rel=1e-12)
