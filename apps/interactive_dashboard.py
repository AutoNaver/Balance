from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from analytics.dashboard import (  # noqa: E402
    aggregate_portfolio,
    compare_scenarios,
    filter_instruments,
    instrument_cashflow_rows,
    instrument_metadata,
    instrument_maturity,
    load_dashboard_portfolio_csv,
    make_parallel_shift_scenario,
    maturity_bucket,
    rows_to_csv,
    rows_to_json,
)
from analytics.dashboard_ui import build_portfolio_tree, ladder_rows, scenario_metric_rows  # noqa: E402
from io_layer.loaders import load_zero_curve_csv  # noqa: E402


@st.cache_data
def _load_inputs(curve_path: str, portfolio_path: str):
    curve = load_zero_curve_csv(curve_path)
    instruments = load_dashboard_portfolio_csv(portfolio_path)
    return curve, instruments


def _plot_cashflow(rows: list[dict], title: str):
    times = [r["time"] for r in rows]
    interest = [r["interest"] for r in rows]
    scheduled = [r["scheduled_amortization"] for r in rows]
    prepay = [r["prepayment"] for r in rows]
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(times, interest, label="Interest")
    ax.bar(times, scheduled, bottom=interest, label="Scheduled")
    top = [interest[i] + scheduled[i] for i in range(len(times))]
    ax.bar(times, prepay, bottom=top, label="Prepayment")
    ax.set_title(title)
    ax.set_xlabel("Time (years)")
    ax.set_ylabel("Cashflow")
    ax.legend()
    return fig


def _plot_outstanding(rows: list[dict], title: str):
    times = [r["time"] for r in rows]
    outstanding = [r["outstanding_balance"] for r in rows]
    fig, ax = plt.subplots(figsize=(9, 3.5))
    ax.plot(times, outstanding, marker="o")
    ax.set_title(title)
    ax.set_xlabel("Time (years)")
    ax.set_ylabel("Outstanding Balance")
    return fig


def _download_figure(fig, label: str, filename: str):
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    st.download_button(label, buffer.getvalue(), file_name=filename, mime="image/png")


def _plot_prepayment_distribution(rows: list[dict], title: str):
    ids = [str(r["instrument_id"]) for r in rows[:10]]
    values = [float(r["prepayment_amount"]) for r in rows[:10]]
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(ids, values)
    ax.set_title(title)
    ax.set_xlabel("Instrument")
    ax.set_ylabel("Prepayment Amount")
    ax.tick_params(axis="x", rotation=45)
    return fig


def main() -> None:
    st.set_page_config(page_title="Balance Portfolio Dashboard", layout="wide")
    st.title("Balance Portfolio Cashflow Drill-Down Dashboard")

    default_curve = str(ROOT / "data" / "market" / "zero_curve.csv")
    default_portfolio = str(ROOT / "data" / "portfolio" / "sample_dashboard_portfolio.csv")

    st.sidebar.header("Data and Scenario")
    curve_path = st.sidebar.text_input("Zero curve CSV", value=default_curve)
    portfolio_path = st.sidebar.text_input("Dashboard portfolio CSV", value=default_portfolio)
    base_shift = st.sidebar.number_input("Base shift (bps)", value=0.0, step=25.0)
    shock_shift = st.sidebar.number_input("Shock shift (bps)", value=100.0, step=25.0)

    curve, all_instruments = _load_inputs(curve_path, portfolio_path)
    base_scenario = make_parallel_shift_scenario(curve, base_shift, name="base")
    shocked_scenario = make_parallel_shift_scenario(curve, shock_shift, name="shock")

    st.sidebar.header("Filters")
    query = st.sidebar.text_input("Search instrument or attribute")
    product_types = sorted({i.product_type for i in all_instruments})
    currencies = sorted({i.currency for i in all_instruments})
    ratings = sorted({i.rating_segment for i in all_instruments})
    buckets = sorted({maturity_bucket(instrument_maturity(i)) for i in all_instruments})

    selected_types = st.sidebar.multiselect("Product type", options=product_types, default=product_types)
    selected_currencies = st.sidebar.multiselect("Currency", options=currencies, default=currencies)
    selected_ratings = st.sidebar.multiselect("Rating segment", options=ratings, default=ratings)
    selected_buckets = st.sidebar.multiselect("Maturity bucket", options=buckets, default=buckets)

    filtered = filter_instruments(
        all_instruments,
        product_types=selected_types,
        maturity_buckets=selected_buckets,
        currencies=selected_currencies,
        ratings=selected_ratings,
        query=query,
    )
    st.caption(f"Filtered instruments: {len(filtered)} / {len(all_instruments)}")
    if not filtered:
        st.warning("No instruments match current filters.")
        return

    portfolio = aggregate_portfolio(filtered, base_scenario)
    cmp = compare_scenarios(filtered, base_scenario, shocked_scenario)
    metrics = portfolio["metrics"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Exposure", f"{metrics['total_exposure']:,.2f}")
    m2.metric("Total PV (Base)", f"{metrics['total_pv']:,.2f}")
    m3.metric("WAC", f"{100.0 * metrics['weighted_average_coupon']:.2f}%")
    m4.metric("WAM", f"{metrics['weighted_average_maturity']:.2f}y")
    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Duration", f"{metrics['duration']:.3f}")
    m6.metric("Convexity", f"{metrics['convexity']:.3f}")
    m7.metric("Prepayment Adjusted Rate", f"{100.0 * metrics['prepayment_adjusted_rate']:.2f}%")
    m8.metric("PV Delta (Shock-Base)", f"{cmp['delta_metrics']['total_pv']:,.2f}")

    st.subheader("Portfolio Charts")
    c1, c2, c3 = st.columns(3)
    with c1:
        fig = _plot_cashflow(portfolio["cashflow_projection"], "Portfolio Cashflow Waterfall")
        st.pyplot(fig)
        _download_figure(fig, "Download waterfall PNG", "portfolio_waterfall.png")
        plt.close(fig)
    with c2:
        maturity_rows = ladder_rows(portfolio["maturity_ladder"])
        fig2, ax2 = plt.subplots(figsize=(8, 4))
        ax2.bar([r["bucket"] for r in maturity_rows], [r["exposure"] for r in maturity_rows])
        ax2.set_title("Maturity Ladder")
        ax2.set_xlabel("Bucket")
        ax2.set_ylabel("Exposure")
        st.pyplot(fig2)
        _download_figure(fig2, "Download ladder PNG", "maturity_ladder.png")
        plt.close(fig2)
    with c3:
        fig6 = _plot_prepayment_distribution(portfolio["prepayment_distribution"], "Prepayment Distribution (Top 10)")
        st.pyplot(fig6)
        _download_figure(fig6, "Download prepayment PNG", "prepayment_distribution.png")
        plt.close(fig6)

    st.download_button(
        "Export portfolio cashflow projection CSV",
        rows_to_csv(portfolio["cashflow_projection"]),
        file_name="portfolio_cashflow_projection.csv",
        mime="text/csv",
    )
    st.download_button(
        "Export prepayment distribution CSV",
        rows_to_csv(portfolio["prepayment_distribution"]),
        file_name="portfolio_prepayment_distribution.csv",
        mime="text/csv",
    )

    st.subheader("Portfolio Tree View")
    grouped = build_portfolio_tree(filtered)
    for sub_portfolio in sorted(grouped):
        with st.expander(f"{sub_portfolio} ({len(grouped[sub_portfolio])} instruments)"):
            for item in grouped[sub_portfolio]:
                if st.button(f"{item.instrument_id} - {item.product_type}", key=f"pick_{item.instrument_id}"):
                    st.session_state["selected_instrument_id"] = item.instrument_id

    options = [i.instrument_id for i in filtered]
    selected_id = st.selectbox(
        "Instrument Drill-Down",
        options=options,
        index=max(0, options.index(st.session_state.get("selected_instrument_id", options[0]))),
    )
    st.session_state["selected_instrument_id"] = selected_id
    selected = next(i for i in filtered if i.instrument_id == selected_id)

    st.subheader(f"Instrument: {selected.instrument_id}")
    metadata = instrument_metadata(selected, base_scenario)
    st.json(metadata)
    rows = instrument_cashflow_rows(selected, base_scenario)

    i1, i2 = st.columns(2)
    with i1:
        fig3 = _plot_cashflow(rows, "Instrument Cashflow Timeline")
        st.pyplot(fig3)
        _download_figure(fig3, "Download instrument timeline PNG", f"{selected.instrument_id}_timeline.png")
        plt.close(fig3)
    with i2:
        fig4 = _plot_outstanding(rows, "Outstanding Balance Curve")
        st.pyplot(fig4)
        _download_figure(fig4, "Download outstanding PNG", f"{selected.instrument_id}_outstanding.png")
        plt.close(fig4)

    st.markdown("Cashflow Table")
    st.dataframe(rows, use_container_width=True)
    st.download_button(
        "Export instrument cashflows CSV",
        rows_to_csv(rows),
        file_name=f"{selected.instrument_id}_cashflows.csv",
        mime="text/csv",
    )
    st.download_button(
        "Export instrument drill-down JSON",
        rows_to_json({"metadata": metadata, "cashflows": rows}),
        file_name=f"{selected.instrument_id}_drilldown.json",
        mime="application/json",
    )

    st.subheader("Scenario Comparison (Base vs Shock)")
    st.dataframe(scenario_metric_rows(cmp), use_container_width=True)
    st.dataframe(cmp["instrument_deltas"], use_container_width=True)
    st.download_button(
        "Export scenario instrument deltas CSV",
        rows_to_csv(cmp["instrument_deltas"]),
        file_name="scenario_instrument_deltas.csv",
        mime="text/csv",
    )
    fig5, ax5 = plt.subplots(figsize=(10, 4))
    ax5.bar([r["time"] for r in cmp["cashflow_delta"]], [r["delta_total_cashflow"] for r in cmp["cashflow_delta"]])
    ax5.set_title("Delta Cashflow Bars (Shock - Base)")
    ax5.set_xlabel("Time (years)")
    ax5.set_ylabel("Delta Total Cashflow")
    st.pyplot(fig5)
    _download_figure(fig5, "Download delta cashflow PNG", "delta_cashflow.png")
    plt.close(fig5)


if __name__ == "__main__":
    main()
