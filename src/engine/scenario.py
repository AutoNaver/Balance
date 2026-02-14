from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np

from models.base import InterestRateModel
from models.curve import DeterministicZeroCurve
from models.hullwhite import HullWhiteModel


@dataclass(frozen=True)
class Scenario:
    name: str
    model: InterestRateModel
    data: dict = field(default_factory=dict)


class ScenarioGenerator(ABC):
    """Produces valuation scenarios for the engine."""

    @abstractmethod
    def generate(self) -> list[Scenario]:
        """Return scenarios for valuation."""


@dataclass(frozen=True)
class DeterministicScenarioGenerator(ScenarioGenerator):
    base_curve: DeterministicZeroCurve
    shifts_bps: list[float]

    def generate(self) -> list[Scenario]:
        scenarios: list[Scenario] = []
        for shift in self.shifts_bps:
            shift_rate = shift / 10_000.0
            shifted = DeterministicZeroCurve(
                tenors=np.array(self.base_curve.tenors, dtype=float),
                zero_rates=np.array(self.base_curve.zero_rates, dtype=float) + shift_rate,
            )
            scenarios.append(Scenario(name=f"parallel_shift_{shift:+.0f}bps", model=shifted))
        return scenarios


@dataclass(frozen=True)
class DeterministicStressScenarioGenerator(ScenarioGenerator):
    """Deterministic stress scenarios with parallel and twist shocks."""

    base_curve: DeterministicZeroCurve
    parallel_shifts_bps: list[float]
    twist_shifts_bps: list[float]
    twist_pivot_year: float = 5.0

    def generate(self) -> list[Scenario]:
        scenarios = DeterministicScenarioGenerator(
            base_curve=self.base_curve,
            shifts_bps=self.parallel_shifts_bps,
        ).generate()
        scenarios.extend(self._twist_scenarios())
        return scenarios

    def _twist_scenarios(self) -> list[Scenario]:
        tenors = np.array(self.base_curve.tenors, dtype=float)
        zero_rates = np.array(self.base_curve.zero_rates, dtype=float)
        max_span = max(np.max(np.abs(tenors - self.twist_pivot_year)), 1e-8)
        slope_profile = np.clip((tenors - self.twist_pivot_year) / max_span, -1.0, 1.0)

        scenarios: list[Scenario] = []
        for twist in self.twist_shifts_bps:
            twist_rate = twist / 10_000.0
            shifted = DeterministicZeroCurve(
                tenors=tenors,
                zero_rates=zero_rates + twist_rate * slope_profile,
            )
            scenarios.append(Scenario(name=f"twist_{twist:+.0f}bps_pivot_{self.twist_pivot_year:g}y", model=shifted))
        return scenarios


@dataclass(frozen=True)
class HullWhiteMonteCarloScenarioGenerator(ScenarioGenerator):
    """Maps Hull-White terminal short-rate shocks into parallel-curve scenarios."""

    base_curve: DeterministicZeroCurve
    model: HullWhiteModel
    horizon_years: float
    n_steps: int
    n_paths: int
    seed: int | None = None

    def generate(self) -> list[Scenario]:
        paths = self.model.simulate_short_rate_paths(
            horizon_years=self.horizon_years,
            n_steps=self.n_steps,
            n_paths=self.n_paths,
            seed=self.seed,
        )
        r0 = self.model.short_rate(0.0)
        terminal = paths[:, -1]

        scenarios: list[Scenario] = []
        for idx, terminal_rate in enumerate(terminal):
            shift = terminal_rate - r0
            shifted_curve = DeterministicZeroCurve(
                tenors=np.array(self.base_curve.tenors, dtype=float),
                zero_rates=np.array(self.base_curve.zero_rates, dtype=float) + shift,
            )
            scenarios.append(Scenario(name=f"hw_mc_path_{idx:04d}", model=shifted_curve))
        return scenarios
