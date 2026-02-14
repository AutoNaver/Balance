from __future__ import annotations

from dataclasses import dataclass

from models.curve import DeterministicZeroCurve
from models.market import DeterministicFXCurve, DeterministicForwardCurve, DeterministicHazardCurve
from products.base import Product


@dataclass
class SensitivityResult:
    product_sensitivities: dict[str, dict[str, float]]
    portfolio_sensitivities: dict[str, float]


class DeterministicSensitivityEngine:
    """Bump-and-revalue first-order sensitivities for deterministic scenarios."""

    def __init__(self, products: list[Product]):
        self.products = products

    def compute(
        self,
        base_scenario: dict,
        as_of_date: str | None = None,
        rate_bump_bps: float = 1.0,
        hazard_bump_bps: float = 1.0,
        fx_bump_pct: float = 0.01,
    ) -> SensitivityResult:
        base_pvs = self._product_pvs(base_scenario, as_of_date)

        metrics: list[tuple[str, str, float, dict]] = []
        if isinstance(base_scenario.get("model"), DeterministicZeroCurve):
            metrics.append(("DV01", "model", rate_bump_bps, self._bump_rate_curve(base_scenario, "model", rate_bump_bps)))
        if isinstance(base_scenario.get("foreign_model"), DeterministicZeroCurve):
            metrics.append(
                (
                    "DV01_foreign",
                    "foreign_model",
                    rate_bump_bps,
                    self._bump_rate_curve(base_scenario, "foreign_model", rate_bump_bps),
                )
            )
        if isinstance(base_scenario.get("forward_model"), (DeterministicZeroCurve, DeterministicForwardCurve)):
            metrics.append(
                (
                    "DV01_forward",
                    "forward_model",
                    rate_bump_bps,
                    self._bump_forward_source(base_scenario, rate_bump_bps),
                )
            )
        if isinstance(base_scenario.get("hazard_curve"), DeterministicHazardCurve):
            metrics.append(("CS01", "hazard_curve", hazard_bump_bps, self._bump_hazard_curve(base_scenario, hazard_bump_bps)))
        if isinstance(base_scenario.get("fx_curve"), DeterministicFXCurve):
            metrics.append(("FX_DELTA_1PCT", "fx_curve", fx_bump_pct, self._bump_fx_curve(base_scenario, fx_bump_pct)))

        by_product: dict[str, dict[str, float]] = {
            label: {} for label in base_pvs
        }
        portfolio: dict[str, float] = {}

        for metric_name, _source, bump_size, shocked_scenario in metrics:
            shocked_pvs = self._product_pvs(shocked_scenario, as_of_date)
            total = 0.0
            for label, base_pv in base_pvs.items():
                raw = shocked_pvs[label] - base_pv
                normalized = raw / bump_size if bump_size != 0.0 else 0.0
                by_product[label][metric_name] = float(normalized)
                total += normalized
            portfolio[metric_name] = float(total)

        return SensitivityResult(product_sensitivities=by_product, portfolio_sensitivities=portfolio)

    def _product_pvs(self, scenario: dict, as_of_date: str | None) -> dict[str, float]:
        out: dict[str, float] = {}
        for idx, product in enumerate(self.products):
            label = f"{idx:03d}_{product.__class__.__name__}"
            out[label] = float(product.present_value(scenario, as_of_date))
        return out

    @staticmethod
    def _bump_rate_curve(scenario: dict, key: str, bump_bps: float) -> dict:
        bumped = dict(scenario)
        curve = bumped[key]
        assert isinstance(curve, DeterministicZeroCurve)
        bumped[key] = DeterministicZeroCurve(
            tenors=curve.tenors,
            zero_rates=curve.zero_rates + (bump_bps / 10_000.0),
        )
        return bumped

    @staticmethod
    def _bump_forward_source(scenario: dict, bump_bps: float) -> dict:
        bumped = dict(scenario)
        fwd = bumped["forward_model"]
        if isinstance(fwd, DeterministicZeroCurve):
            bumped["forward_model"] = DeterministicZeroCurve(
                tenors=fwd.tenors,
                zero_rates=fwd.zero_rates + (bump_bps / 10_000.0),
            )
            return bumped
        assert isinstance(fwd, DeterministicForwardCurve)
        bumped["forward_model"] = DeterministicForwardCurve(
            tenors=fwd.tenors,
            forward_rates=fwd.forward_rates + (bump_bps / 10_000.0),
        )
        return bumped

    @staticmethod
    def _bump_hazard_curve(scenario: dict, bump_bps: float) -> dict:
        bumped = dict(scenario)
        hazard = bumped["hazard_curve"]
        assert isinstance(hazard, DeterministicHazardCurve)
        bumped["hazard_curve"] = DeterministicHazardCurve(
            tenors=hazard.tenors,
            hazard_rates=hazard.hazard_rates + (bump_bps / 10_000.0),
        )
        return bumped

    @staticmethod
    def _bump_fx_curve(scenario: dict, bump_pct: float) -> dict:
        bumped = dict(scenario)
        fx = bumped["fx_curve"]
        assert isinstance(fx, DeterministicFXCurve)
        bumped["fx_curve"] = DeterministicFXCurve(
            tenors=fx.tenors,
            fx_forwards=fx.fx_forwards * (1.0 + bump_pct),
        )
        return bumped
