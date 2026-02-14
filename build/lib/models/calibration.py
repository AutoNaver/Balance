from __future__ import annotations

from dataclasses import dataclass
import csv
from pathlib import Path

import numpy as np

from models.curve import DeterministicZeroCurve


@dataclass(frozen=True)
class DepositQuote:
    tenor_years: float
    simple_rate: float


@dataclass(frozen=True)
class SwapQuote:
    maturity_years: float
    par_rate: float
    fixed_frequency: int = 1


@dataclass(frozen=True)
class CalibrationDiagnostics:
    monotonic_discount_factors: bool
    non_negative_forwards: bool
    max_abs_fit_error: float


def load_curve_quotes_csv(path: str | Path) -> tuple[list[DepositQuote], list[SwapQuote]]:
    """Load deposit/swap quotes from CSV.

    Expected columns:
    - instrument_type: deposit|swap
    - tenor_years
    - rate
    - fixed_frequency (optional for swaps, default=1)
    """
    deposits: list[DepositQuote] = []
    swaps: list[SwapQuote] = []
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            typ = str(row.get("instrument_type", "")).strip().lower()
            tenor = float(row["tenor_years"])
            rate = float(row["rate"])
            if typ == "deposit":
                deposits.append(DepositQuote(tenor_years=tenor, simple_rate=rate))
            elif typ == "swap":
                freq_raw = row.get("fixed_frequency", "")
                freq = int(freq_raw) if str(freq_raw).strip() else 1
                swaps.append(SwapQuote(maturity_years=tenor, par_rate=rate, fixed_frequency=freq))
            else:
                raise ValueError(f"unsupported instrument_type: {typ}")
    return deposits, swaps


def bootstrap_zero_curve(
    deposits: list[DepositQuote],
    swaps: list[SwapQuote],
    interpolation: str = "linear_zero",
) -> tuple[DeterministicZeroCurve, CalibrationDiagnostics]:
    """Bootstrap deterministic zero curve from deposits and par swaps.

    Notes:
    - v1 assumes par swap maturities align to fixed-payment grid.
    - v1 supports interpolation policy labels for governance; bootstrap is node-based.
    """
    if interpolation not in {"linear_zero", "log_df"}:
        raise ValueError("interpolation must be one of: linear_zero, log_df")

    dep_sorted = sorted(deposits, key=lambda d: d.tenor_years)
    sw_sorted = sorted(swaps, key=lambda s: s.maturity_years)
    if not dep_sorted and not sw_sorted:
        raise ValueError("at least one deposit or swap quote is required")

    dfs: dict[float, float] = {}

    # Deposit DF from simple-interest quote: DF(T)=1/(1+r*T)
    for d in dep_sorted:
        if d.tenor_years <= 0.0:
            raise ValueError("deposit tenor must be positive")
        if d.simple_rate < -0.99:
            raise ValueError("deposit simple_rate is unrealistically low")
        dfs[float(d.tenor_years)] = 1.0 / (1.0 + d.simple_rate * d.tenor_years)

    # Bootstrap from fixed-leg par swap equation:
    # 1 - DF(T) = K * sum_i alpha_i DF(t_i)
    # => DF(T) = (1 - K * sum_{i=1..n-1} alpha_i DF(t_i)) / (1 + K * alpha_n)
    for s in sw_sorted:
        if s.maturity_years <= 0.0:
            raise ValueError("swap maturity must be positive")
        if s.fixed_frequency <= 0:
            raise ValueError("fixed_frequency must be positive")

        dt = 1.0 / s.fixed_frequency
        n = int(round(s.maturity_years * s.fixed_frequency))
        if n <= 0:
            raise ValueError("invalid swap maturity/frequency combination")
        pay_times = [i * dt for i in range(1, n + 1)]

        known_leg = 0.0
        for t in pay_times[:-1]:
            if t not in dfs:
                raise ValueError(
                    f"missing earlier discount factor at t={t:g} for swap maturity {s.maturity_years:g}; "
                    "provide deposits/swaps on required grid"
                )
            known_leg += dt * dfs[t]

        numerator = 1.0 - s.par_rate * known_leg
        denominator = 1.0 + s.par_rate * dt
        df_T = numerator / denominator
        if df_T <= 0.0:
            raise ValueError("bootstrapped discount factor is non-positive; inconsistent market quotes")
        dfs[float(s.maturity_years)] = df_T

    tenors = np.array(sorted(dfs.keys()), dtype=float)
    discount_factors = np.array([dfs[t] for t in tenors], dtype=float)
    zero_rates = -np.log(np.maximum(discount_factors, 1e-16)) / np.maximum(tenors, 1e-16)

    curve = DeterministicZeroCurve(tenors=tenors, zero_rates=zero_rates)
    diagnostics = _diagnostics(curve, dep_sorted, sw_sorted)
    return curve, diagnostics


def _diagnostics(
    curve: DeterministicZeroCurve,
    deposits: list[DepositQuote],
    swaps: list[SwapQuote],
) -> CalibrationDiagnostics:
    df_nodes = np.array([curve.discount_factor(float(t)) for t in curve.tenors], dtype=float)
    monotonic_df = bool(np.all(np.diff(df_nodes) <= 1e-12))

    forwards = []
    for i in range(1, len(curve.tenors)):
        t0 = float(curve.tenors[i - 1])
        t1 = float(curve.tenors[i])
        forwards.append(curve.forward_rate(t0, t1))
    non_negative_forwards = bool(np.all(np.array(forwards, dtype=float) >= -1e-10)) if forwards else True

    errors: list[float] = []
    for d in deposits:
        model_df = curve.discount_factor(d.tenor_years)
        mkt_df = 1.0 / (1.0 + d.simple_rate * d.tenor_years)
        errors.append(model_df - mkt_df)

    for s in swaps:
        dt = 1.0 / s.fixed_frequency
        n = int(round(s.maturity_years * s.fixed_frequency))
        pay_times = [i * dt for i in range(1, n + 1)]
        annuity = sum(dt * curve.discount_factor(t) for t in pay_times)
        if annuity <= 0.0:
            continue
        model_par = (1.0 - curve.discount_factor(s.maturity_years)) / annuity
        errors.append(model_par - s.par_rate)

    max_abs_fit_error = float(np.max(np.abs(np.array(errors, dtype=float)))) if errors else 0.0
    return CalibrationDiagnostics(
        monotonic_discount_factors=monotonic_df,
        non_negative_forwards=non_negative_forwards,
        max_abs_fit_error=max_abs_fit_error,
    )
