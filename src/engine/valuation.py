from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from engine.scenario import Scenario
from products.base import Product


@dataclass
class ValuationResult:
    scenario_pv: dict[str, float]
    portfolio_pv_distribution: np.ndarray

    def pvat_risk(self, confidence: float = 0.99) -> float:
        if not (0.0 < confidence < 1.0):
            raise ValueError("confidence must be between 0 and 1")
        base_pv = self.scenario_pv.get("parallel_shift_+0bps")
        if base_pv is None:
            base_pv = float(np.max(self.portfolio_pv_distribution))
        q = np.quantile(self.portfolio_pv_distribution, 1.0 - confidence)
        return float(base_pv - q)

    def expected_shortfall(self, confidence: float = 0.99) -> float:
        if not (0.0 < confidence < 1.0):
            raise ValueError("confidence must be between 0 and 1")
        base_pv = self.scenario_pv.get("parallel_shift_+0bps")
        if base_pv is None:
            base_pv = float(np.max(self.portfolio_pv_distribution))
        losses = base_pv - self.portfolio_pv_distribution
        var = np.quantile(losses, confidence)
        tail = losses[losses >= var]
        if tail.size == 0:
            return 0.0
        return float(np.mean(tail))

    def summary(self, confidence: float = 0.99) -> dict[str, float]:
        return {
            "pvat_risk": self.pvat_risk(confidence),
            "expected_shortfall": self.expected_shortfall(confidence),
            "min_pv": float(np.min(self.portfolio_pv_distribution)),
            "max_pv": float(np.max(self.portfolio_pv_distribution)),
            "mean_pv": float(np.mean(self.portfolio_pv_distribution)),
        }

    def risk_profile(self, confidences: list[float]) -> dict[str, dict[str, float]]:
        profile: dict[str, dict[str, float]] = {}
        for c in confidences:
            key = f"{c:.4f}"
            profile[key] = {
                "pvat_risk": self.pvat_risk(c),
                "expected_shortfall": self.expected_shortfall(c),
            }
        return profile

    def to_json(self, path: str | Path, confidence: float = 0.99) -> None:
        output = {
            "scenario_pv": self.scenario_pv,
            "portfolio_pv_distribution": self.portfolio_pv_distribution.tolist(),
            "pvat_risk": self.pvat_risk(confidence),
            "confidence": confidence,
        }
        Path(path).write_text(json.dumps(output, indent=2), encoding="utf-8")

    def to_csv(self, path: str | Path) -> None:
        with Path(path).open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["scenario", "pv"])
            for scenario, pv in self.scenario_pv.items():
                writer.writerow([scenario, pv])


class ValuationEngine:
    """Values product collections under scenario sets."""

    def __init__(self, products: list[Product]):
        self.products = products

    def value(self, scenarios: list[Scenario], as_of_date: str | None = None) -> ValuationResult:
        scenario_pv: dict[str, float] = {}
        pv_values: list[float] = []

        for scenario in scenarios:
            data = {"model": scenario.model, "name": scenario.name}
            data.update(scenario.data)
            total = sum(product.present_value(data, as_of_date) for product in self.products)
            scenario_pv[scenario.name] = float(total)
            pv_values.append(float(total))

        return ValuationResult(
            scenario_pv=scenario_pv,
            portfolio_pv_distribution=np.array(pv_values, dtype=float),
        )

    def value_with_contributions(
        self, scenarios: list[Scenario], as_of_date: str | None = None
    ) -> tuple[ValuationResult, dict[str, dict[str, float]]]:
        scenario_pv: dict[str, float] = {}
        pv_values: list[float] = []
        contributions: dict[str, dict[str, float]] = {}

        for scenario in scenarios:
            data = {"model": scenario.model, "name": scenario.name}
            data.update(scenario.data)
            per_product: dict[str, float] = {}
            total = 0.0
            for idx, product in enumerate(self.products):
                label = f"{idx:03d}_{product.__class__.__name__}"
                pv = float(product.present_value(data, as_of_date))
                per_product[label] = pv
                total += pv
            scenario_pv[scenario.name] = total
            pv_values.append(total)
            contributions[scenario.name] = per_product

        result = ValuationResult(
            scenario_pv=scenario_pv,
            portfolio_pv_distribution=np.array(pv_values, dtype=float),
        )
        return result, contributions

    def value_with_grouped_contributions(
        self,
        scenarios: list[Scenario],
        as_of_date: str | None = None,
    ) -> tuple[ValuationResult, dict[str, dict[str, float]]]:
        result, contributions = self.value_with_contributions(scenarios, as_of_date)
        grouped: dict[str, dict[str, float]] = {}

        for scenario_name, per_product in contributions.items():
            groups: dict[str, float] = {}
            for label, pv in per_product.items():
                # label format: "idx_ClassName"
                group = label.split("_", 1)[1] if "_" in label else label
                groups[group] = groups.get(group, 0.0) + pv
            grouped[scenario_name] = groups

        return result, grouped
