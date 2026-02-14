import numpy as np
import pytest

from models.curve import DeterministicZeroCurve
from models.market import DeterministicFXCurve
from products.derivatives import FXForward


def test_generic_valuation_breakdown_available_for_derivative_products():
    curve = DeterministicZeroCurve(
        tenors=np.array([0.5, 1.0, 2.0]),
        zero_rates=np.array([0.02, 0.02, 0.02]),
    )
    fx_curve = DeterministicFXCurve(
        tenors=np.array([0.5, 1.0, 2.0]),
        fx_forwards=np.array([1.10, 1.12, 1.14]),
    )
    trade = FXForward(notional_foreign=1_000_000.0, strike=1.10, maturity_years=1.0)
    out = trade.valuation_breakdown({"model": curve, "fx_curve": fx_curve}, accrued_interest=250.0)
    assert out["dirty_pv"] - out["clean_pv"] == pytest.approx(250.0)
