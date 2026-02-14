from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from models.base import InterestRateModel
from models.curve import DeterministicZeroCurve


@dataclass(frozen=True)
class HullWhiteModel(InterestRateModel):
    """One-factor Hull-White short-rate model around an initial zero curve."""

    a: float
    sigma: float
    initial_curve: DeterministicZeroCurve

    def __post_init__(self) -> None:
        if self.a <= 0.0:
            raise ValueError("a must be > 0")
        if self.sigma < 0.0:
            raise ValueError("sigma must be >= 0")

    def discount_factor(self, t: float) -> float:
        # Deterministic discounting anchored to the initial market curve.
        return self.initial_curve.discount_factor(t)

    def short_rate(self, t: float) -> float:
        return self.initial_curve.short_rate(t)

    def zcb_price(self, t: float, T: float, r_t: float | None = None) -> float:
        """Closed-form P(t, T) under Hull-White with curve-fitted theta."""
        if T < t or t < 0.0:
            raise ValueError("require 0 <= t <= T")
        if T == t:
            return 1.0

        a = self.a
        sigma = self.sigma
        rt = self.short_rate(t) if r_t is None else r_t

        B = (1.0 - np.exp(-a * (T - t))) / a
        p0t = self.initial_curve.discount_factor(t)
        p0T = self.initial_curve.discount_factor(T)
        f0t = self.initial_curve.continuous_forward_rate(t)
        sigma_term = (sigma**2 / (4.0 * a**3)) * (1.0 - np.exp(-a * (T - t))) ** 2 * (1.0 - np.exp(-2.0 * a * t))
        A = (p0T / p0t) * np.exp(B * f0t - sigma_term)
        return float(A * np.exp(-B * rt))

    def simulate_short_rate_paths(
        self,
        horizon_years: float,
        n_steps: int,
        n_paths: int,
        seed: int | None = None,
    ) -> np.ndarray:
        """Euler simulation of short-rate paths r(t)."""
        if horizon_years <= 0.0 or n_steps <= 0 or n_paths <= 0:
            raise ValueError("horizon_years, n_steps, and n_paths must be positive")

        dt = horizon_years / n_steps
        times = np.linspace(0.0, horizon_years, n_steps + 1)
        rng = np.random.default_rng(seed)
        rates = np.zeros((n_paths, n_steps + 1), dtype=float)
        rates[:, 0] = self.short_rate(0.0)

        for i in range(n_steps):
            t = times[i]
            theta = self._theta(t)
            z = rng.standard_normal(n_paths)
            dr = (theta - self.a * rates[:, i]) * dt + self.sigma * np.sqrt(dt) * z
            rates[:, i + 1] = rates[:, i] + dr

        return rates

    def _theta(self, t: float) -> float:
        # Drift term that matches initial term structure.
        dt = 1e-4
        f_t = self.initial_curve.continuous_forward_rate(t, dt=dt)
        f_tp = self.initial_curve.continuous_forward_rate(t + dt, dt=dt)
        dfd_t = (f_tp - f_t) / dt
        return dfd_t + self.a * f_t + (self.sigma**2 / (2.0 * self.a)) * (1.0 - np.exp(-2.0 * self.a * t))
