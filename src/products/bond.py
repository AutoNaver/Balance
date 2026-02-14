from __future__ import annotations

from dataclasses import dataclass

from models.base import InterestRateModel
from products.base import Cashflow, Product


@dataclass(frozen=True)
class FixedRateBond(Product):
    notional: float
    coupon_rate: float
    maturity_years: float
    coupon_frequency: int = 1

    def get_cashflows(self, scenario: dict, as_of_date: str | None = None) -> list[Cashflow]:
        periods = int(round(self.maturity_years * self.coupon_frequency))
        if periods <= 0:
            raise ValueError("maturity_years and coupon_frequency imply zero periods")
        dt = 1.0 / self.coupon_frequency
        coupon = self.notional * self.coupon_rate * dt
        cashflows: list[Cashflow] = []
        for i in range(1, periods + 1):
            t = i * dt
            amount = coupon
            if i == periods:
                amount += self.notional
            cashflows.append(Cashflow(time=t, amount=amount))
        return cashflows

    def present_value(self, scenario: dict, as_of_date: str | None = None) -> float:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        return sum(cf.amount * model.discount_factor(cf.time) for cf in self.get_cashflows(scenario, as_of_date))
