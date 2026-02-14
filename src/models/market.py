from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DeterministicFXCurve:
    """Deterministic FX forward curve, quoted as domestic per unit foreign."""

    tenors: np.ndarray
    fx_forwards: np.ndarray

    def __post_init__(self) -> None:
        if self.tenors.ndim != 1 or self.fx_forwards.ndim != 1:
            raise ValueError("tenors and fx_forwards must be one-dimensional arrays")
        if len(self.tenors) != len(self.fx_forwards):
            raise ValueError("tenors and fx_forwards must have equal length")
        if len(self.tenors) < 2:
            raise ValueError("curve must contain at least two tenor points")
        if np.any(np.diff(self.tenors) <= 0):
            raise ValueError("tenors must be strictly increasing")

    def fx_forward(self, t: float) -> float:
        if t <= 0.0:
            return float(self.fx_forwards[0])
        if t <= float(self.tenors[0]):
            return float(self.fx_forwards[0])
        if t >= float(self.tenors[-1]):
            return float(self.fx_forwards[-1])
        return float(np.interp(t, self.tenors, self.fx_forwards))


@dataclass(frozen=True)
class DeterministicHazardCurve:
    """Piecewise-constant default intensity curve."""

    tenors: np.ndarray
    hazard_rates: np.ndarray

    def __post_init__(self) -> None:
        if self.tenors.ndim != 1 or self.hazard_rates.ndim != 1:
            raise ValueError("tenors and hazard_rates must be one-dimensional arrays")
        if len(self.tenors) != len(self.hazard_rates):
            raise ValueError("tenors and hazard_rates must have equal length")
        if len(self.tenors) < 2:
            raise ValueError("curve must contain at least two tenor points")
        if np.any(np.diff(self.tenors) <= 0):
            raise ValueError("tenors must be strictly increasing")

    def hazard_rate(self, t: float) -> float:
        if t <= 0.0:
            return float(self.hazard_rates[0])
        if t <= float(self.tenors[0]):
            return float(self.hazard_rates[0])
        if t >= float(self.tenors[-1]):
            return float(self.hazard_rates[-1])
        return float(np.interp(t, self.tenors, self.hazard_rates))

    def survival_probability(self, t: float) -> float:
        if t < 0.0:
            raise ValueError("t must be non-negative")
        if t == 0.0:
            return 1.0
        # Simple approximation using local hazard at t.
        h = self.hazard_rate(t)
        return float(np.exp(-h * t))
