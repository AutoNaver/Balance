import numpy as np
import pytest

from models.curve import DeterministicZeroCurve
from products.corporate_bond import CorporateBond


def test_corporate_bond_clean_dirty_breakdown():
    curve = DeterministicZeroCurve(
        tenors=np.array([1.0, 3.0, 5.0]),
        zero_rates=np.array([0.02, 0.021, 0.022]),
    )
    bond = CorporateBond(
        notional=1_000_000.0,
        maturity_years=5.0,
        coupon_type="fixed",
        fixed_rate=0.04,
        frequency="semi_annual",
        amortization_mode="bullet",
    )
    out = bond.valuation_breakdown({"model": curve}, accrued_interest=1_250.0)
    assert out["dirty_pv"] > out["clean_pv"]
    assert out["dirty_pv"] - out["clean_pv"] == pytest.approx(1_250.0)
    assert out["dirty_price_pct"] > out["clean_price_pct"]
