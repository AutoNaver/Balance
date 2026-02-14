from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.scenario import (
    DeterministicStressScenarioGenerator,
    HullWhiteMonteCarloScenarioGenerator,
)
from engine.valuation import ValuationEngine
from io_layer.loaders import load_mixed_portfolio_csv, load_zero_curve_csv
from models.hullwhite import HullWhiteModel


def main() -> None:
    curve = load_zero_curve_csv(ROOT / "data" / "market" / "zero_curve.csv")
    portfolio = load_mixed_portfolio_csv(ROOT / "data" / "portfolio" / "sample_mixed_portfolio_extended.csv")

    config_path = ROOT / "config" / "scenarios.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    det_scenario_gen = DeterministicStressScenarioGenerator(
        base_curve=curve,
        parallel_shifts_bps=config["deterministic_parallel_shifts_bps"],
        twist_shifts_bps=config.get("deterministic_twist_shifts_bps", []),
        twist_pivot_year=float(config.get("twist_pivot_year", 5.0)),
    )

    engine = ValuationEngine(portfolio)
    det_result, det_grouped = engine.value_with_grouped_contributions(det_scenario_gen.generate())

    print("Deterministic Scenario PVs:")
    for name, pv in det_result.scenario_pv.items():
        print(f"  {name}: {pv:,.2f}")

    confidence = float(config.get("pvat_risk_confidence", 0.99))
    print(f"Deterministic PVatRisk ({confidence:.0%}): {det_result.pvat_risk(confidence):,.2f}")
    print(f"Deterministic Expected Shortfall ({confidence:.0%}): {det_result.expected_shortfall(confidence):,.2f}")

    print("Deterministic Risk Profile:")
    for c, metrics in det_result.risk_profile([0.95, confidence]).items():
        print(f"  conf={c}: VaR={metrics['pvat_risk']:,.2f}, ES={metrics['expected_shortfall']:,.2f}")

    base_contrib = det_grouped.get("parallel_shift_+0bps", {})
    if base_contrib:
        print("Base Scenario Grouped Contributions:")
        for label, pv in sorted(base_contrib.items(), key=lambda x: abs(x[1]), reverse=True)[:6]:
            print(f"  {label}: {pv:,.2f}")

    hw_cfg = config["hull_white"]
    hw_model = HullWhiteModel(a=float(hw_cfg["a"]), sigma=float(hw_cfg["sigma"]), initial_curve=curve)
    mc_scenario_gen = HullWhiteMonteCarloScenarioGenerator(
        base_curve=curve,
        model=hw_model,
        horizon_years=float(hw_cfg["mc_horizon_years"]),
        n_steps=int(hw_cfg["mc_steps"]),
        n_paths=int(hw_cfg["mc_paths"]),
        seed=int(hw_cfg["seed"]),
    )
    mc_result = engine.value(mc_scenario_gen.generate())
    print(f"Hull-White MC PVatRisk ({confidence:.0%}): {mc_result.pvat_risk(confidence):,.2f}")

    out_dir = ROOT / "data" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    det_result.to_csv(out_dir / "deterministic_pv.csv")
    mc_result.to_json(out_dir / "hull_white_mc_result.json", confidence=confidence)
    print(f"Results exported to {out_dir}")


if __name__ == "__main__":
    main()
