from pathlib import Path

import pytest

from analytics.dashboard import (
    aggregate_portfolio,
    compare_scenarios,
    filter_instruments,
    instrument_cashflow_rows,
    load_dashboard_portfolio_csv,
    make_parallel_shift_scenario,
    maturity_bucket,
)
from io_layer.loaders import load_zero_curve_csv


def _load_inputs():
    root = Path(__file__).resolve().parents[1]
    curve = load_zero_curve_csv(root / "data" / "market" / "zero_curve.csv")
    instruments = load_dashboard_portfolio_csv(root / "data" / "portfolio" / "sample_dashboard_portfolio.csv")
    return curve, instruments


def test_dashboard_portfolio_loader_returns_ids_and_metadata():
    _, instruments = _load_inputs()
    assert len(instruments) >= 6
    ids = {i.instrument_id for i in instruments}
    assert "MORT-DE-001" in ids
    assert "BOND-CORP-001" in ids


def test_instrument_cashflow_drilldown_contains_components():
    curve, instruments = _load_inputs()
    scenario = make_parallel_shift_scenario(curve, 0.0)
    mort = next(i for i in instruments if i.instrument_id == "MORT-DE-001")
    rows = instrument_cashflow_rows(mort, scenario)
    assert len(rows) > 0
    assert set(rows[0].keys()) == {
        "time",
        "interest",
        "scheduled_amortization",
        "prepayment",
        "total",
        "outstanding_balance",
    }
    assert rows[0]["outstanding_balance"] < mort.product.notional


def test_filter_instruments_supports_product_currency_bucket_and_query():
    _, instruments = _load_inputs()
    filtered = filter_instruments(
        instruments,
        product_types=["corporate_bond"],
        maturity_buckets=["5-10Y"],
        currencies=["USD"],
        ratings=["BBB", "A"],
        query="corp-001",
    )
    assert len(filtered) == 1
    assert filtered[0].instrument_id == "BOND-CORP-001"


@pytest.mark.parametrize(
    "maturity, expected",
    [(0.5, "<1Y"), (2.0, "1-3Y"), (4.0, "3-5Y"), (8.0, "5-10Y"), (12.0, "10Y+")],
)
def test_maturity_bucket(maturity: float, expected: str):
    assert maturity_bucket(maturity) == expected


def test_scenario_comparison_has_nonzero_delta_for_rate_shock():
    curve, instruments = _load_inputs()
    base = make_parallel_shift_scenario(curve, 0.0, name="base")
    shock = make_parallel_shift_scenario(curve, 100.0, name="shock")
    comparison = compare_scenarios(instruments, base, shock)
    assert "delta_metrics" in comparison
    assert comparison["delta_metrics"]["total_pv"] != 0.0
    assert len(comparison["instrument_deltas"]) == len(instruments)


def test_portfolio_aggregate_includes_required_metrics():
    curve, instruments = _load_inputs()
    scenario = make_parallel_shift_scenario(curve, 0.0)
    agg = aggregate_portfolio(instruments, scenario)
    metrics = agg["metrics"]
    assert metrics["total_exposure"] > 0.0
    assert "weighted_average_coupon" in metrics
    assert "weighted_average_maturity" in metrics
    assert "duration" in metrics
    assert "convexity" in metrics
