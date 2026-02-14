from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from io_layer.loaders import _parse_product_row
from models.curve import DeterministicZeroCurve
from models.market import DeterministicForwardCurve
from products.base import Product
from products.corporate_bond import CorporateBond
from products.mortgage import GermanFixedRateMortgageLoan


_MORTGAGE_FREQ_TO_MONTHS = {"monthly": 1, "quarterly": 3, "annual": 12}
_BOND_FREQ_TO_YEARS = {
    "monthly": 1.0 / 12.0,
    "quarterly": 0.25,
    "semi_annual": 0.5,
    "annual": 1.0,
}


@dataclass(frozen=True)
class DashboardInstrument:
    instrument_id: str
    product_type: str
    product: Product
    sub_portfolio: str = "root"
    currency: str = "NA"
    rating_segment: str = "NA"
    metadata: dict[str, str] = field(default_factory=dict)


def load_dashboard_portfolio_csv(path: str | Path) -> list[DashboardInstrument]:
    items: list[DashboardInstrument] = []
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            product_type = str(row.get("product_type", "")).strip().lower()
            if not product_type:
                continue
            instrument_id = str(row.get("instrument_id", "")).strip()
            if not instrument_id:
                raise ValueError("instrument_id is required for dashboard portfolio rows")
            product = _parse_product_row(row, product_type)
            metadata = {
                k: v
                for k, v in row.items()
                if k not in {"instrument_id", "product_type", "sub_portfolio", "currency", "rating_segment"} and v is not None and str(v).strip() != ""
            }
            items.append(
                DashboardInstrument(
                    instrument_id=instrument_id,
                    product_type=product_type,
                    product=product,
                    sub_portfolio=str(row.get("sub_portfolio", "root") or "root"),
                    currency=str(row.get("currency", "NA") or "NA"),
                    rating_segment=str(row.get("rating_segment", "NA") or "NA"),
                    metadata=metadata,
                )
            )
    return items


def make_parallel_shift_scenario(
    base_curve: DeterministicZeroCurve,
    shift_bps: float = 0.0,
    name: str | None = None,
    forward_curve: DeterministicForwardCurve | None = None,
) -> dict:
    shifted = DeterministicZeroCurve(
        tenors=np.array(base_curve.tenors, dtype=float),
        zero_rates=np.array(base_curve.zero_rates, dtype=float) + float(shift_bps) / 10_000.0,
    )
    scenario_name = name or f"parallel_shift_{shift_bps:+.0f}bps"
    scenario = {"name": scenario_name, "model": shifted}
    if forward_curve is not None:
        scenario["forward_model"] = forward_curve
    return scenario


def maturity_bucket(maturity_years: float) -> str:
    if maturity_years < 1.0:
        return "<1Y"
    if maturity_years < 3.0:
        return "1-3Y"
    if maturity_years < 5.0:
        return "3-5Y"
    if maturity_years < 10.0:
        return "5-10Y"
    return "10Y+"


def filter_instruments(
    instruments: list[DashboardInstrument],
    product_types: list[str] | None = None,
    maturity_buckets: list[str] | None = None,
    currencies: list[str] | None = None,
    ratings: list[str] | None = None,
    query: str = "",
) -> list[DashboardInstrument]:
    query_l = query.strip().lower()
    pset = set(product_types or [])
    mset = set(maturity_buckets or [])
    cset = set(currencies or [])
    rset = set(ratings or [])
    out: list[DashboardInstrument] = []
    for item in instruments:
        maturity = instrument_maturity(item)
        bucket = maturity_bucket(maturity)
        if pset and item.product_type not in pset:
            continue
        if mset and bucket not in mset:
            continue
        if cset and item.currency not in cset:
            continue
        if rset and item.rating_segment not in rset:
            continue
        if query_l:
            haystack = " ".join(
                [
                    item.instrument_id,
                    item.sub_portfolio,
                    item.product_type,
                    item.currency,
                    item.rating_segment,
                    " ".join(f"{k}:{v}" for k, v in item.metadata.items()),
                ]
            ).lower()
            if query_l not in haystack:
                continue
        out.append(item)
    return out


def instrument_notional(item: DashboardInstrument) -> float:
    product = item.product
    for name in ("notional", "domestic_notional", "notional_foreign"):
        value = getattr(product, name, None)
        if value is not None:
            return float(value)
    return 0.0


def instrument_coupon(item: DashboardInstrument) -> float:
    product = item.product
    for name in ("fixed_rate", "coupon_rate", "spread"):
        value = getattr(product, name, None)
        if value is not None:
            return float(value)
    return 0.0


def instrument_maturity(item: DashboardInstrument) -> float:
    product = item.product
    for name in ("maturity_years", "far_maturity_years"):
        value = getattr(product, name, None)
        if value is not None:
            return float(value)
    return 0.0


def instrument_cashflow_rows(item: DashboardInstrument, scenario: dict) -> list[dict[str, float]]:
    if isinstance(item.product, GermanFixedRateMortgageLoan):
        return _mortgage_rows(item.product, scenario)
    if isinstance(item.product, CorporateBond):
        return _corporate_bond_rows(item.product, scenario)
    generic = item.product.get_cashflows(scenario)
    return [
        {
            "time": float(cf.time),
            "interest": float(cf.amount),
            "scheduled_amortization": 0.0,
            "prepayment": 0.0,
            "total": float(cf.amount),
            "outstanding_balance": 0.0,
        }
        for cf in generic
    ]


def instrument_metadata(item: DashboardInstrument, scenario: dict) -> dict[str, str | float]:
    product = item.product
    details: dict[str, str | float] = {
        "instrument_id": item.instrument_id,
        "product_type": item.product_type,
        "sub_portfolio": item.sub_portfolio,
        "currency": item.currency,
        "rating_segment": item.rating_segment,
        "notional": instrument_notional(item),
        "coupon_or_rate": instrument_coupon(item),
        "maturity_years": instrument_maturity(item),
        "discount_curve": type(scenario.get("model")).__name__,
    }
    for key in (
        "repayment_type",
        "payment_frequency",
        "frequency",
        "annual_cpr",
        "periodic_prepayment_rate",
        "spread",
    ):
        value = getattr(product, key, None)
        if value is not None:
            details[key] = value
    details.update(item.metadata)
    return details


def aggregate_portfolio(instruments: list[DashboardInstrument], scenario: dict) -> dict:
    total_exposure = 0.0
    w_coupon = 0.0
    w_maturity = 0.0
    total_pv = 0.0
    duration_num = 0.0
    convexity_num = 0.0
    prepayment_total = 0.0

    cashflow_by_time: dict[float, dict[str, float]] = {}
    prepayment_distribution: list[dict[str, float | str]] = []
    maturity_ladder: dict[str, float] = {}

    for item in instruments:
        notional = instrument_notional(item)
        coupon = instrument_coupon(item)
        maturity = instrument_maturity(item)
        bucket = maturity_bucket(maturity)
        rows = instrument_cashflow_rows(item, scenario)
        pv = float(item.product.present_value(scenario))
        total_pv += pv

        total_exposure += notional
        w_coupon += notional * coupon
        w_maturity += notional * maturity
        maturity_ladder[bucket] = maturity_ladder.get(bucket, 0.0) + notional

        model = scenario["model"]
        pv_item = 0.0
        d_item = 0.0
        c_item = 0.0
        prepay_item = 0.0
        for row in rows:
            t = float(row["time"])
            total = float(row["total"])
            prepay = float(row["prepayment"])
            df = float(model.discount_factor(t))
            pv_cf = total * df
            pv_item += pv_cf
            d_item += t * pv_cf
            c_item += t * t * pv_cf
            prepay_item += prepay

            rounded_t = round(t, 6)
            slot = cashflow_by_time.setdefault(
                rounded_t,
                {
                    "time": rounded_t,
                    "interest": 0.0,
                    "scheduled_amortization": 0.0,
                    "prepayment": 0.0,
                    "total": 0.0,
                },
            )
            slot["interest"] += float(row["interest"])
            slot["scheduled_amortization"] += float(row["scheduled_amortization"])
            slot["prepayment"] += prepay
            slot["total"] += total

        prepayment_total += prepay_item
        prepayment_distribution.append({"instrument_id": item.instrument_id, "prepayment_amount": prepay_item})
        if abs(pv_item) > 1e-12:
            duration_num += d_item
            convexity_num += c_item

    duration = duration_num / total_pv if abs(total_pv) > 1e-12 else 0.0
    convexity = convexity_num / total_pv if abs(total_pv) > 1e-12 else 0.0
    prepay_rate = prepayment_total / total_exposure if total_exposure > 1e-12 else 0.0

    return {
        "metrics": {
            "total_exposure": total_exposure,
            "weighted_average_coupon": (w_coupon / total_exposure if total_exposure > 1e-12 else 0.0),
            "weighted_average_maturity": (w_maturity / total_exposure if total_exposure > 1e-12 else 0.0),
            "duration": duration,
            "convexity": convexity,
            "prepayment_adjusted_rate": prepay_rate,
            "total_pv": total_pv,
        },
        "cashflow_projection": sorted(cashflow_by_time.values(), key=lambda x: float(x["time"])),
        "maturity_ladder": maturity_ladder,
        "prepayment_distribution": sorted(prepayment_distribution, key=lambda x: float(x["prepayment_amount"]), reverse=True),
    }


def compare_scenarios(
    instruments: list[DashboardInstrument],
    base_scenario: dict,
    shocked_scenario: dict,
) -> dict:
    base = aggregate_portfolio(instruments, base_scenario)
    shocked = aggregate_portfolio(instruments, shocked_scenario)
    instrument_deltas: list[dict[str, float | str]] = []
    for item in instruments:
        base_pv = float(item.product.present_value(base_scenario))
        shocked_pv = float(item.product.present_value(shocked_scenario))
        base_prepay = sum(float(r["prepayment"]) for r in instrument_cashflow_rows(item, base_scenario))
        shocked_prepay = sum(float(r["prepayment"]) for r in instrument_cashflow_rows(item, shocked_scenario))
        instrument_deltas.append(
            {
                "instrument_id": item.instrument_id,
                "product_type": item.product_type,
                "base_pv": base_pv,
                "shocked_pv": shocked_pv,
                "delta_pv": shocked_pv - base_pv,
                "base_prepayment": base_prepay,
                "shocked_prepayment": shocked_prepay,
                "delta_prepayment": shocked_prepay - base_prepay,
            }
        )

    base_cf = {round(float(r["time"]), 6): float(r["total"]) for r in base["cashflow_projection"]}
    shocked_cf = {round(float(r["time"]), 6): float(r["total"]) for r in shocked["cashflow_projection"]}
    all_times = sorted(set(base_cf) | set(shocked_cf))
    cashflow_delta = [{"time": t, "delta_total_cashflow": shocked_cf.get(t, 0.0) - base_cf.get(t, 0.0)} for t in all_times]

    return {
        "base_metrics": base["metrics"],
        "shocked_metrics": shocked["metrics"],
        "delta_metrics": {
            "total_pv": shocked["metrics"]["total_pv"] - base["metrics"]["total_pv"],
            "duration": shocked["metrics"]["duration"] - base["metrics"]["duration"],
            "convexity": shocked["metrics"]["convexity"] - base["metrics"]["convexity"],
            "prepayment_adjusted_rate": shocked["metrics"]["prepayment_adjusted_rate"] - base["metrics"]["prepayment_adjusted_rate"],
        },
        "instrument_deltas": sorted(instrument_deltas, key=lambda x: abs(float(x["delta_pv"])), reverse=True),
        "cashflow_delta": cashflow_delta,
    }


def rows_to_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def rows_to_json(rows: list[dict]) -> str:
    return json.dumps(rows, indent=2)


def _mortgage_rows(loan: GermanFixedRateMortgageLoan, scenario: dict) -> list[dict[str, float]]:
    model = scenario.get("model")
    months_per_period = _MORTGAGE_FREQ_TO_MONTHS[loan.payment_frequency]
    periods = int(round(loan.maturity_years * 12 / months_per_period))
    dt = months_per_period / 12.0
    rate_per_period = loan.fixed_rate * loan._day_count_factor(dt)
    interest_only_periods = int(round(loan.interest_only_years * 12 / months_per_period))
    annuity_payment = loan._annuity_payment(rate_per_period, periods, interest_only_periods)
    const_principal = 0.0
    if loan.repayment_type == "constant_repayment":
        amort_periods = max(1, periods - interest_only_periods)
        const_principal = loan.notional / amort_periods

    rows: list[dict[str, float]] = []
    balance = loan.notional
    for i in range(1, periods + 1):
        if balance <= 1e-8:
            break
        t0 = (i - 1) * dt
        t1 = i * dt
        interest = balance * rate_per_period

        if i <= interest_only_periods:
            scheduled = 0.0
        elif loan.repayment_type == "annuity":
            scheduled = max(0.0, annuity_payment - interest)
        elif loan.repayment_type == "constant_repayment":
            scheduled = const_principal
        else:
            remaining_periods = max(1, periods - i + 1)
            scheduled = balance / remaining_periods
        scheduled = min(balance, scheduled)
        post_sched = balance - scheduled
        prepay = loan._prepayment_amount(model, t0, t1, i, post_sched)
        prepay = min(post_sched, prepay)
        end_balance = post_sched - prepay

        rows.append(
            {
                "time": float(t1),
                "interest": float(interest),
                "scheduled_amortization": float(scheduled),
                "prepayment": float(prepay),
                "total": float(interest + scheduled + prepay),
                "outstanding_balance": float(max(end_balance, 0.0)),
            }
        )
        balance = end_balance
    return rows


def _corporate_bond_rows(bond: CorporateBond, scenario: dict) -> list[dict[str, float]]:
    discount_model = scenario["model"]
    forward_model = scenario.get("forward_model")
    dt = _BOND_FREQ_TO_YEARS[bond.frequency]
    periods = int(round(bond.maturity_years / dt))
    schedule = bond._scheduled_principal(periods)

    rows: list[dict[str, float]] = []
    outstanding = bond.notional
    for i in range(1, periods + 1):
        t0 = (i - 1) * dt
        t1 = i * dt
        prepay = bond._prepayment_amount(outstanding, dt)
        outstanding_after_prepay = max(0.0, outstanding - prepay)
        coupon_rate = bond._coupon_rate(discount_model, t0, t1, forward_model=forward_model)
        interest = outstanding_after_prepay * coupon_rate * bond._accrual_factor(dt)
        scheduled = 0.0
        if i > bond.interest_only_periods:
            scheduled = min(outstanding_after_prepay, schedule[i - 1])
        end_balance = max(0.0, outstanding_after_prepay - scheduled)

        rows.append(
            {
                "time": float(t1),
                "interest": float(interest),
                "scheduled_amortization": float(scheduled),
                "prepayment": float(prepay),
                "total": float(interest + prepay + scheduled),
                "outstanding_balance": float(end_balance),
            }
        )
        outstanding = end_balance
    return rows
