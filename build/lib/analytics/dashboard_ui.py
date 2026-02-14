from __future__ import annotations

from collections import defaultdict

from analytics.dashboard import DashboardInstrument


def build_portfolio_tree(instruments: list[DashboardInstrument]) -> dict[str, list[DashboardInstrument]]:
    tree: dict[str, list[DashboardInstrument]] = defaultdict(list)
    for item in instruments:
        tree[item.sub_portfolio].append(item)
    return {k: sorted(v, key=lambda x: x.instrument_id) for k, v in sorted(tree.items())}


def scenario_metric_rows(comparison: dict) -> list[dict[str, float | str]]:
    base = comparison["base_metrics"]
    shocked = comparison["shocked_metrics"]
    delta = comparison["delta_metrics"]
    keys = ["total_pv", "duration", "convexity", "prepayment_adjusted_rate"]
    rows: list[dict[str, float | str]] = []
    for k in keys:
        rows.append(
            {
                "metric": k,
                "base": float(base[k]),
                "shocked": float(shocked[k]),
                "delta": float(delta[k]),
            }
        )
    return rows


def ladder_rows(maturity_ladder: dict[str, float]) -> list[dict[str, float | str]]:
    return [{"bucket": k, "exposure": v} for k, v in sorted(maturity_ladder.items())]

