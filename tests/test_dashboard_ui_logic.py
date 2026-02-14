from pathlib import Path

from analytics.dashboard import compare_scenarios, load_dashboard_portfolio_csv, make_parallel_shift_scenario
from analytics.dashboard_ui import build_portfolio_tree, ladder_rows, scenario_metric_rows
from io_layer.loaders import load_zero_curve_csv


def _load_inputs():
    root = Path(__file__).resolve().parents[1]
    curve = load_zero_curve_csv(root / "data" / "market" / "zero_curve.csv")
    instruments = load_dashboard_portfolio_csv(root / "data" / "portfolio" / "sample_dashboard_portfolio.csv")
    return curve, instruments


def test_build_portfolio_tree_groups_and_sorts():
    _, instruments = _load_inputs()
    tree = build_portfolio_tree(instruments)
    assert "corp_credit" in tree
    ids = [i.instrument_id for i in tree["corp_credit"]]
    assert ids == sorted(ids)


def test_ladder_rows_sorted_by_bucket():
    rows = ladder_rows({"10Y+": 2.0, "1-3Y": 1.0, "3-5Y": 3.0})
    assert [r["bucket"] for r in rows] == ["1-3Y", "10Y+", "3-5Y"]


def test_scenario_metric_rows_structure():
    curve, instruments = _load_inputs()
    base = make_parallel_shift_scenario(curve, 0.0, name="base")
    shock = make_parallel_shift_scenario(curve, 100.0, name="shock")
    cmp = compare_scenarios(instruments, base, shock)
    rows = scenario_metric_rows(cmp)
    assert len(rows) == 4
    assert {r["metric"] for r in rows} == {"total_pv", "duration", "convexity", "prepayment_adjusted_rate"}
