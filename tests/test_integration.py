import json
from pathlib import Path

from engine.scenario import DeterministicScenarioGenerator, HullWhiteMonteCarloScenarioGenerator
from engine.valuation import ValuationEngine
from io_layer.loaders import load_mixed_portfolio_csv, load_zero_curve_csv
from models.hullwhite import HullWhiteModel


def test_end_to_end_portfolio_valuation_and_export(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    curve = load_zero_curve_csv(root / "data" / "market" / "zero_curve.csv")
    portfolio = load_mixed_portfolio_csv(root / "data" / "portfolio" / "sample_mixed_portfolio_extended.csv")
    config = json.loads((root / "config" / "scenarios.json").read_text(encoding="utf-8"))

    scenarios = DeterministicScenarioGenerator(curve, config["deterministic_parallel_shifts_bps"]).generate()
    result = ValuationEngine(portfolio).value(scenarios)

    csv_path = tmp_path / "deterministic.csv"
    json_path = tmp_path / "deterministic.json"
    result.to_csv(csv_path)
    result.to_json(json_path, confidence=0.99)

    assert len(result.scenario_pv) == len(config["deterministic_parallel_shifts_bps"])
    assert result.pvat_risk(0.99) >= 0.0
    assert csv_path.exists()
    assert json_path.exists()


def test_end_to_end_hull_white_mc_scenarios():
    root = Path(__file__).resolve().parents[1]
    curve = load_zero_curve_csv(root / "data" / "market" / "zero_curve.csv")
    portfolio = load_mixed_portfolio_csv(root / "data" / "portfolio" / "sample_mixed_portfolio_extended.csv")
    config = json.loads((root / "config" / "scenarios.json").read_text(encoding="utf-8"))

    hw_cfg = config["hull_white"]
    hw_model = HullWhiteModel(a=float(hw_cfg["a"]), sigma=float(hw_cfg["sigma"]), initial_curve=curve)
    mc_generator = HullWhiteMonteCarloScenarioGenerator(
        base_curve=curve,
        model=hw_model,
        horizon_years=float(hw_cfg["mc_horizon_years"]),
        n_steps=int(hw_cfg["mc_steps"]),
        n_paths=10,
        seed=int(hw_cfg["seed"]),
    )

    scenarios = mc_generator.generate()
    result = ValuationEngine(portfolio).value(scenarios)

    assert len(scenarios) == 10
    assert len(result.scenario_pv) == 10
    assert result.pvat_risk(0.99) >= 0.0
