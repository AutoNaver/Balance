from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from engine.scenario import Scenario
from models.base import InterestRateModel
from products.base import Product


@dataclass(frozen=True)
class CSAConfig:
    netting_set_id: str
    discount_model: InterestRateModel
    collateral_rate: float = 0.0
    threshold: float = 0.0
    minimum_transfer_amount: float = 0.0


@dataclass
class CSAScenarioResult:
    unsecured_pv: float
    secured_pv: float
    netting_set_secured_pv: dict[str, float]


class CSADiscountingEngine:
    """Deterministic CSA-aware valuation on top of existing product pricers."""

    def __init__(self, products: list[Product]):
        self.products = products

    def value(
        self,
        scenarios: list[Scenario],
        product_to_netting_set: dict[int, str],
        csa_configs: dict[str, CSAConfig],
        as_of_date: str | None = None,
    ) -> dict[str, CSAScenarioResult]:
        results: dict[str, CSAScenarioResult] = {}

        for scenario in scenarios:
            base_data = {"model": scenario.model, "name": scenario.name}
            base_data.update(scenario.data)

            unsecured_total = 0.0
            secured_total = 0.0
            per_ns: dict[str, float] = {k: 0.0 for k in csa_configs}

            for idx, product in enumerate(self.products):
                unsecured_pv = float(product.present_value(base_data, as_of_date))
                unsecured_total += unsecured_pv

                ns_id = product_to_netting_set.get(idx)
                if ns_id is None or ns_id not in csa_configs:
                    secured_pv = unsecured_pv
                else:
                    cfg = csa_configs[ns_id]
                    secured_data = dict(base_data)
                    secured_data["model"] = cfg.discount_model
                    secured_pv = float(product.present_value(secured_data, as_of_date))
                    per_ns[ns_id] += secured_pv

                secured_total += secured_pv

            results[scenario.name] = CSAScenarioResult(
                unsecured_pv=float(unsecured_total),
                secured_pv=float(secured_total),
                netting_set_secured_pv=per_ns,
            )

        return results

    @staticmethod
    def summarize(results: dict[str, CSAScenarioResult]) -> dict[str, float]:
        if not results:
            return {"mean_unsecured_pv": 0.0, "mean_secured_pv": 0.0, "mean_collateral_impact": 0.0}
        unsecured = np.array([v.unsecured_pv for v in results.values()], dtype=float)
        secured = np.array([v.secured_pv for v in results.values()], dtype=float)
        impact = secured - unsecured
        return {
            "mean_unsecured_pv": float(np.mean(unsecured)),
            "mean_secured_pv": float(np.mean(secured)),
            "mean_collateral_impact": float(np.mean(impact)),
        }
