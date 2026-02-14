from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from models.base import InterestRateModel


@dataclass(frozen=True)
class DeterministicZeroCurve(InterestRateModel):
    """Piecewise-linear zero curve with continuous compounding."""

    tenors: np.ndarray
    zero_rates: np.ndarray

    def __post_init__(self) -> None:
        if self.tenors.ndim != 1 or self.zero_rates.ndim != 1:
            raise ValueError("tenors and zero_rates must be one-dimensional arrays")
        if len(self.tenors) != len(self.zero_rates):
            raise ValueError("tenors and zero_rates must have equal length")
        if len(self.tenors) < 2:
            raise ValueError("curve must contain at least two tenor points")
        if np.any(np.diff(self.tenors) <= 0):
            raise ValueError("tenors must be strictly increasing")

    def _interp_zero_rate(self, t: float) -> float:
        if t <= 0.0:
            return float(self.zero_rates[0])
        if t <= float(self.tenors[0]):
            return float(self.zero_rates[0])
        if t >= float(self.tenors[-1]):
            return float(self.zero_rates[-1])
        return float(np.interp(t, self.tenors, self.zero_rates))

    def discount_factor(self, t: float) -> float:
        if t < 0.0:
            raise ValueError("t must be non-negative")
        r = self._interp_zero_rate(t)
        return float(np.exp(-r * t))

    def short_rate(self, t: float) -> float:
        if t < 0.0:
            raise ValueError("t must be non-negative")
        return self._interp_zero_rate(t)

    def df(self, t: float) -> float:
        return self.discount_factor(t)

    def fwd_rate(self, t: float, dt: float = 1e-4) -> float:
        if t < 0.0:
            raise ValueError("t must be non-negative")
        if dt <= 0.0:
            raise ValueError("dt must be positive")
        df_t = self.discount_factor(t)
        df_tp = self.discount_factor(t + dt)
        return float((np.log(df_t) - np.log(df_tp)) / dt)
