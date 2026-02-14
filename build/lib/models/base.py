from __future__ import annotations

from abc import ABC, abstractmethod
import math


class InterestRateModel(ABC):
    """Abstract rate model used by product pricers."""

    @abstractmethod
    def discount_factor(self, t: float) -> float:
        """Return the discount factor from valuation time 0 to time t in years."""

    @abstractmethod
    def short_rate(self, t: float) -> float:
        """Return the instantaneous short rate at time t."""

    def forward_rate(self, t0: float, t1: float) -> float:
        """Implied simple forward rate between t0 and t1 from discount factors."""
        if t0 < 0.0 or t1 <= t0:
            raise ValueError("require t0 >= 0 and t1 > t0")
        df0 = self.discount_factor(t0)
        df1 = self.discount_factor(t1)
        if df1 <= 0.0 or df0 <= 0.0:
            raise ValueError("discount factors must be positive")
        return (df0 / df1 - 1.0) / (t1 - t0)

    def continuous_forward_rate(self, t: float, dt: float = 1e-4) -> float:
        """Approximate instantaneous forward rate at t."""
        if t < 0.0 or dt <= 0.0:
            raise ValueError("require t >= 0 and dt > 0")
        df_t = self.discount_factor(t)
        df_tp = self.discount_factor(t + dt)
        if df_t <= 0.0 or df_tp <= 0.0:
            raise ValueError("discount factors must be positive")
        return (math.log(df_t) - math.log(df_tp)) / dt
