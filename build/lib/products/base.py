from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Cashflow:
    time: float
    amount: float


class Product(ABC):
    """Common interface for all balance-sheet products."""

    @abstractmethod
    def get_cashflows(self, scenario: dict, as_of_date: str | None = None) -> list[Cashflow]:
        """Return future cashflows under a scenario."""

    @abstractmethod
    def present_value(self, scenario: dict, as_of_date: str | None = None) -> float:
        """Return product PV under a scenario."""

    def valuation_breakdown(
        self,
        scenario: dict,
        as_of_date: str | None = None,
        accrued_interest: float = 0.0,
    ) -> dict[str, float]:
        """Default clean/dirty PV breakdown for products."""
        dirty_pv = float(self.present_value(scenario, as_of_date))
        clean_pv = dirty_pv - accrued_interest
        return {
            "dirty_pv": dirty_pv,
            "clean_pv": clean_pv,
            "accrued_interest": float(accrued_interest),
        }
