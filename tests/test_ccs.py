import numpy as np

from models.curve import DeterministicZeroCurve
from models.market import DeterministicFXCurve
from products.derivatives import CrossCurrencySwap


def _curve(rate: float) -> DeterministicZeroCurve:
    return DeterministicZeroCurve(
        tenors=np.array([0.5, 1.0, 2.0, 5.0]),
        zero_rates=np.array([rate, rate, rate, rate]),
    )


def test_ccs_pv_changes_with_fx_level():
    domestic = _curve(0.02)
    foreign = _curve(0.01)
    trade = CrossCurrencySwap(
        domestic_notional=1_000_000.0,
        foreign_notional=900_000.0,
        maturity_years=3.0,
        domestic_frequency=2,
        foreign_frequency=2,
        domestic_fixed_rate=0.023,
        foreign_fixed_rate=0.018,
        pay_domestic_receive_foreign=True,
    )
    low_fx = DeterministicFXCurve(
        tenors=np.array([0.5, 1.0, 2.0, 3.0]),
        fx_forwards=np.array([1.05, 1.06, 1.07, 1.08]),
    )
    high_fx = DeterministicFXCurve(
        tenors=np.array([0.5, 1.0, 2.0, 3.0]),
        fx_forwards=np.array([1.15, 1.16, 1.17, 1.18]),
    )
    pv_low = trade.present_value({"model": domestic, "foreign_model": foreign, "fx_curve": low_fx})
    pv_high = trade.present_value({"model": domestic, "foreign_model": foreign, "fx_curve": high_fx})
    assert pv_high != pv_low


def test_ccs_returns_cashflows_with_notional_exchanges():
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
    )
    cfs = trade.get_cashflows({"model": domestic, "foreign_model": foreign, "fx_curve": fx})
    assert len(cfs) > 4
    assert any(cf.time == 0.0 for cf in cfs)
