from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.scenario import Scenario
from engine.valuation import ValuationEngine
from io_layer.loaders import load_mixed_portfolio_csv
from models.curve import DeterministicZeroCurve
from models.market import DeterministicFXCurve, DeterministicHazardCurve


def main() -> None:
    products = load_mixed_portfolio_csv(ROOT / "data" / "portfolio" / "sample_derivatives_suite.csv")

    ir_curve = DeterministicZeroCurve(
        tenors=np.array([0.5, 1.0, 2.0, 5.0, 10.0]),
        zero_rates=np.array([0.02, 0.021, 0.022, 0.024, 0.025]),
    )
    foreign_curve = DeterministicZeroCurve(
        tenors=np.array([0.5, 1.0, 2.0, 5.0, 10.0]),
        zero_rates=np.array([0.015, 0.016, 0.017, 0.019, 0.020]),
    )
    fx_curve = DeterministicFXCurve(
        tenors=np.array([0.25, 0.5, 1.0, 2.0]),
        fx_forwards=np.array([1.10, 1.105, 1.115, 1.13]),
    )
    hazard_curve = DeterministicHazardCurve(
        tenors=np.array([1.0, 3.0, 5.0, 10.0]),
        hazard_rates=np.array([0.01, 0.012, 0.013, 0.015]),
    )

    scenario = Scenario(
        name="base",
        model=ir_curve,
        data={"fx_curve": fx_curve, "hazard_curve": hazard_curve, "foreign_model": foreign_curve},
    )
    result = ValuationEngine(products).value([scenario])

    print("Derivatives suite PV:")
    for name, pv in result.scenario_pv.items():
        print(f"  {name}: {pv:,.2f}")


if __name__ == "__main__":
    main()
