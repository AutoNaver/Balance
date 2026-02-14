from __future__ import annotations

from dataclasses import dataclass

from models.base import InterestRateModel
from products.base import Cashflow, Product


@dataclass(frozen=True)
class FixedFloatSwap(Product):
    """Vanilla fixed-float IRS without notional exchange."""

    notional: float
    fixed_rate: float
    maturity_years: float
    fixed_frequency: int = 1
    float_frequency: int = 4
    pay_fixed: bool = True

    def get_cashflows(self, scenario: dict, as_of_date: str | None = None) -> list[Cashflow]:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        return self.fixed_leg_cashflows() + self.float_leg_cashflows(model)

    def fixed_leg_cashflows(self) -> list[Cashflow]:
        n_fixed = int(round(self.maturity_years * self.fixed_frequency))
        if n_fixed <= 0:
            raise ValueError("maturity_years and fixed_frequency imply zero periods")
        dt = 1.0 / self.fixed_frequency
        coupon = self.notional * self.fixed_rate * dt
        return [Cashflow(time=i * dt, amount=coupon) for i in range(1, n_fixed + 1)]

    def float_leg_cashflows(self, model: InterestRateModel) -> list[Cashflow]:
        n_float = int(round(self.maturity_years * self.float_frequency))
        if n_float <= 0:
            raise ValueError("maturity_years and float_frequency imply zero periods")
        dt = 1.0 / self.float_frequency
        cashflows: list[Cashflow] = []
        for i in range(1, n_float + 1):
            t0 = (i - 1) * dt
            t1 = i * dt
            fwd = model.forward_rate(t0, t1)
            amount = self.notional * fwd * dt
            cashflows.append(Cashflow(time=t1, amount=amount))
        return cashflows

    def present_value(self, scenario: dict, as_of_date: str | None = None) -> float:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")

        pv_fixed = sum(cf.amount * model.discount_factor(cf.time) for cf in self.fixed_leg_cashflows())
        pv_float = sum(cf.amount * model.discount_factor(cf.time) for cf in self.float_leg_cashflows(model))
        return float(pv_float - pv_fixed if self.pay_fixed else pv_fixed - pv_float)


@dataclass(frozen=True)
class FloatFloatSwap(Product):
    """Vanilla float-float swap using one curve and leg spreads."""

    notional: float
    maturity_years: float
    pay_leg_frequency: int = 4
    receive_leg_frequency: int = 4
    pay_spread: float = 0.0
    receive_spread: float = 0.0
    pay_leg_sign: int = -1  # -1 pay, +1 receive

    def get_cashflows(self, scenario: dict, as_of_date: str | None = None) -> list[Cashflow]:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        return self._leg_cashflows(model, self.pay_leg_frequency, self.pay_spread, self.pay_leg_sign) + self._leg_cashflows(
            model, self.receive_leg_frequency, self.receive_spread, -self.pay_leg_sign
        )

    def present_value(self, scenario: dict, as_of_date: str | None = None) -> float:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        return sum(cf.amount * model.discount_factor(cf.time) for cf in self.get_cashflows(scenario, as_of_date))

    def _leg_cashflows(
        self,
        model: InterestRateModel,
        frequency: int,
        spread: float,
        sign: int,
    ) -> list[Cashflow]:
        n = int(round(self.maturity_years * frequency))
        if n <= 0:
            raise ValueError("maturity_years and frequency imply zero periods")
        dt = 1.0 / frequency
        cfs: list[Cashflow] = []
        for i in range(1, n + 1):
            t0 = (i - 1) * dt
            t1 = i * dt
            fwd = model.forward_rate(t0, t1) + spread
            cfs.append(Cashflow(time=t1, amount=sign * self.notional * fwd * dt))
        return cfs
