import numpy as np

from engine.sensitivity import DeterministicSensitivityEngine
from models.curve import DeterministicZeroCurve
from models.market import DeterministicFXCurve, DeterministicHazardCurve
from products.bond import FixedRateBond
from products.derivatives import CreditDefaultSwap, FXForward


def _curve(rate: float) -> DeterministicZeroCurve:
    return DeterministicZeroCurve(
        tenors=np.array([0.5, 1.0, 2.0, 5.0]),
        zero_rates=np.array([rate, rate, rate, rate]),
    )


def test_dv01_for_fixed_rate_bond_is_negative():
    product = FixedRateBond(notional=1_000_000.0, coupon_rate=0.03, maturity_years=3.0, coupon_frequency=2)
    engine = DeterministicSensitivityEngine([product])

    result = engine.compute({"model": _curve(0.02)})
    assert "DV01" in result.portfolio_sensitivities
    assert result.portfolio_sensitivities["DV01"] < 0.0


def test_fx_delta_for_forward_sign_matches_direction():
    product = FXForward(
        notional_foreign=1_000_000.0,
        strike=1.08,
        maturity_years=1.0,
        pay_foreign_receive_domestic=True,
    )
    engine = DeterministicSensitivityEngine([product])
    scenario = {
        "model": _curve(0.02),
        "fx_curve": DeterministicFXCurve(
            tenors=np.array([0.5, 1.0, 2.0]),
            fx_forwards=np.array([1.10, 1.12, 1.15]),
        ),
    }
    result = engine.compute(scenario)
    assert result.portfolio_sensitivities["FX_DELTA_1PCT"] > 0.0


def test_cs01_for_protection_buyer_is_positive_when_hazard_increases():
    cds = CreditDefaultSwap(notional=1_000_000.0, spread_bps=100.0, maturity_years=5.0)
    engine = DeterministicSensitivityEngine([cds])
    scenario = {
        "model": _curve(0.02),
        "hazard_curve": DeterministicHazardCurve(
            tenors=np.array([1.0, 3.0, 5.0, 10.0]),
            hazard_rates=np.array([0.01, 0.012, 0.014, 0.016]),
        ),
    }
    result = engine.compute(scenario)
    assert result.portfolio_sensitivities["CS01"] > 0.0


def test_product_sensitivities_reconcile_to_portfolio_sum():
    products = [
        FixedRateBond(notional=500_000.0, coupon_rate=0.025, maturity_years=2.0, coupon_frequency=2),
        FXForward(notional_foreign=250_000.0, strike=1.07, maturity_years=1.0),
    ]
    scenario = {
        "model": _curve(0.02),
        "fx_curve": DeterministicFXCurve(
            tenors=np.array([0.5, 1.0, 2.0]),
            fx_forwards=np.array([1.10, 1.11, 1.12]),
        ),
    }
    engine = DeterministicSensitivityEngine(products)
    result = engine.compute(scenario)

    dv01_sum = sum(v.get("DV01", 0.0) for v in result.product_sensitivities.values())
    fx_sum = sum(v.get("FX_DELTA_1PCT", 0.0) for v in result.product_sensitivities.values())

    assert result.portfolio_sensitivities["DV01"] == dv01_sum
    assert result.portfolio_sensitivities["FX_DELTA_1PCT"] == fx_sum
