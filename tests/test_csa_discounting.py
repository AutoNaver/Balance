import numpy as np

from engine.collateral import CSAConfig, CSADiscountingEngine
from engine.scenario import Scenario
from models.curve import DeterministicZeroCurve
from products.swap import FixedFloatSwap


def _curve(rate: float) -> DeterministicZeroCurve:
    return DeterministicZeroCurve(
        tenors=np.array([0.5, 1.0, 2.0, 5.0]),
        zero_rates=np.array([rate, rate, rate, rate]),
    )


def test_csa_engine_reports_unsecured_and_secured_values():
    products = [
        FixedFloatSwap(notional=1_000_000.0, fixed_rate=0.03, maturity_years=3.0, fixed_frequency=2, float_frequency=2),
        FixedFloatSwap(notional=800_000.0, fixed_rate=0.025, maturity_years=2.0, fixed_frequency=2, float_frequency=2),
    ]
    scenarios = [Scenario(name="base", model=_curve(0.03))]
    engine = CSADiscountingEngine(products)

    results = engine.value(
        scenarios=scenarios,
        product_to_netting_set={0: "ns_usd", 1: "ns_usd"},
        csa_configs={"ns_usd": CSAConfig(netting_set_id="ns_usd", discount_model=_curve(0.01))},
    )

    assert "base" in results
    r = results["base"]
    assert r.secured_pv != r.unsecured_pv
    assert "ns_usd" in r.netting_set_secured_pv


def test_csa_summary_contains_collateral_impact():
    products = [FixedFloatSwap(notional=1_000_000.0, fixed_rate=0.03, maturity_years=3.0, fixed_frequency=1, float_frequency=1)]
    scenarios = [
        Scenario(name="s1", model=_curve(0.02)),
        Scenario(name="s2", model=_curve(0.03)),
    ]
    engine = CSADiscountingEngine(products)
    results = engine.value(
        scenarios=scenarios,
        product_to_netting_set={0: "ns1"},
        csa_configs={"ns1": CSAConfig(netting_set_id="ns1", discount_model=_curve(0.01))},
    )
    summary = engine.summarize(results)
    assert set(summary) == {"mean_unsecured_pv", "mean_secured_pv", "mean_collateral_impact"}
