import numpy as np

from models.curve import DeterministicZeroCurve
from models.market import DeterministicFXCurve
from products.derivatives import CrossCurrencySwap


def _curve(rate: float) -> DeterministicZeroCurve:
    return DeterministicZeroCurve(
        tenors=np.array([0.5, 1.0, 2.0, 5.0]),
        zero_rates=np.array([rate, rate, rate, rate]),
    )


def _fx() -> DeterministicFXCurve:
    return DeterministicFXCurve(
        tenors=np.array([0.5, 1.0, 2.0, 3.0, 5.0]),
        fx_forwards=np.array([1.10, 1.11, 1.12, 1.13, 1.14]),
    )


def test_mark_to_market_ccs_changes_pv():
    domestic = _curve(0.02)
    foreign = _curve(0.015)
    fx = _fx()

    base = CrossCurrencySwap(
        domestic_notional=1_000_000.0,
        foreign_notional=900_000.0,
        maturity_years=3.0,
        domestic_frequency=2,
        foreign_frequency=2,
        domestic_fixed_rate=0.024,
        foreign_fixed_rate=0.018,
        mark_to_market=False,
    )
    mtm = CrossCurrencySwap(
        domestic_notional=1_000_000.0,
        foreign_notional=900_000.0,
        maturity_years=3.0,
        domestic_frequency=2,
        foreign_frequency=2,
        domestic_fixed_rate=0.024,
        foreign_fixed_rate=0.018,
        mark_to_market=True,
    )

    pv_base = base.present_value({"model": domestic, "foreign_model": foreign, "fx_curve": fx})
    pv_mtm = mtm.present_value({"model": domestic, "foreign_model": foreign, "fx_curve": fx})
    assert pv_base != pv_mtm


def test_mark_to_market_ccs_has_intermediate_notional_reset_flows():
    domestic = _curve(0.02)
    foreign = _curve(0.015)
    fx = _fx()
    mtm = CrossCurrencySwap(
        domestic_notional=1_000_000.0,
        foreign_notional=900_000.0,
        maturity_years=3.0,
        domestic_frequency=2,
        foreign_frequency=2,
        domestic_fixed_rate=0.024,
        foreign_fixed_rate=0.018,
        mark_to_market=True,
    )
    cashflows = mtm.get_cashflows({"model": domestic, "foreign_model": foreign, "fx_curve": fx})
    times = [cf.time for cf in cashflows]
    # With semi-annual resets over 3y, MTM should add reset exchanges at intermediate dates.
    assert any(t in {0.5, 1.0, 1.5, 2.0, 2.5} for t in times)
