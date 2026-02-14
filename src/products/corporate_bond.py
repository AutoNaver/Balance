from __future__ import annotations

from dataclasses import dataclass
import math

from models.base import InterestRateModel
from products.base import Cashflow, Product


_FREQ_TO_YEARS = {
    "monthly": 1.0 / 12.0,
    "quarterly": 0.25,
    "semi_annual": 0.5,
    "annual": 1.0,
}


@dataclass(frozen=True)
class CorporateBond(Product):
    """Corporate bond with fixed/float coupons, amortization, and constant prepayment."""

    notional: float
    maturity_years: float
    coupon_type: str = "fixed"  # fixed | floating
    fixed_rate: float = 0.0
    spread: float = 0.0
    frequency: str = "semi_annual"
    day_count: str = "30/360"
    amortization_mode: str = "bullet"  # bullet | linear | custom
    custom_amortization: tuple[float, ...] = ()
    interest_only_periods: int = 0
    annual_cpr: float = 0.0
    periodic_prepayment_rate: float | None = None

    def get_cashflows(self, scenario: dict, as_of_date: str | None = None) -> list[Cashflow]:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        return self._cashflows(model)

    def present_value(self, scenario: dict, as_of_date: str | None = None) -> float:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        return sum(cf.amount * model.discount_factor(cf.time) for cf in self._cashflows(model))

    def valuation_breakdown(
        self,
        scenario: dict,
        as_of_date: str | None = None,
        accrued_interest: float = 0.0,
    ) -> dict[str, float]:
        """Return dirty/clean PV and price diagnostics."""
        dirty_pv = self.present_value(scenario, as_of_date)
        clean_pv = dirty_pv - accrued_interest
        return {
            "dirty_pv": dirty_pv,
            "clean_pv": clean_pv,
            "accrued_interest": accrued_interest,
            "dirty_price_pct": 100.0 * dirty_pv / self.notional,
            "clean_price_pct": 100.0 * clean_pv / self.notional,
        }

    def price_from_yield(
        self,
        annual_yield: float,
        scenario: dict,
        as_of_date: str | None = None,
        compounding: str = "continuous",
    ) -> float:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        cashflows = self._cashflows(model)
        if compounding == "continuous":
            return sum(cf.amount * math.exp(-annual_yield * cf.time) for cf in cashflows)
        if compounding == "annual":
            return sum(cf.amount / ((1.0 + annual_yield) ** cf.time) for cf in cashflows)
        raise ValueError("compounding must be one of: continuous, annual")

    def yield_to_maturity(
        self,
        target_dirty_pv: float,
        scenario: dict,
        as_of_date: str | None = None,
        compounding: str = "continuous",
        lower: float = -0.05,
        upper: float = 1.00,
        tol: float = 1e-10,
        max_iter: int = 200,
    ) -> float:
        if target_dirty_pv <= 0.0:
            raise ValueError("target_dirty_pv must be positive")
        lo = lower
        hi = upper
        f_lo = self.price_from_yield(lo, scenario, as_of_date, compounding) - target_dirty_pv
        f_hi = self.price_from_yield(hi, scenario, as_of_date, compounding) - target_dirty_pv
        while f_lo * f_hi > 0 and hi < 5.0:
            hi *= 1.5
            f_hi = self.price_from_yield(hi, scenario, as_of_date, compounding) - target_dirty_pv
        if f_lo * f_hi > 0:
            raise ValueError("Unable to bracket yield root for target_dirty_pv")
        for _ in range(max_iter):
            mid = 0.5 * (lo + hi)
            f_mid = self.price_from_yield(mid, scenario, as_of_date, compounding) - target_dirty_pv
            if abs(f_mid) < tol:
                return mid
            if f_lo * f_mid <= 0:
                hi = mid
                f_hi = f_mid
            else:
                lo = mid
                f_lo = f_mid
        return 0.5 * (lo + hi)

    def _cashflows(self, model: InterestRateModel) -> list[Cashflow]:
        if self.notional <= 0.0 or self.maturity_years <= 0.0:
            raise ValueError("notional and maturity_years must be positive")
        dt = _FREQ_TO_YEARS.get(self.frequency)
        if dt is None:
            raise ValueError("unsupported frequency")
        periods = int(round(self.maturity_years / dt))
        if periods <= 0:
            raise ValueError("invalid maturity/frequency combination")
        if self.interest_only_periods < 0 or self.interest_only_periods >= periods:
            raise ValueError("interest_only_periods must be in [0, periods)")

        schedule = self._scheduled_principal(periods)
        cashflows: list[Cashflow] = []
        outstanding = self.notional

        for i in range(1, periods + 1):
            t0 = (i - 1) * dt
            t1 = i * dt

            prepay = self._prepayment_amount(outstanding, dt)
            outstanding_after_prepay = max(0.0, outstanding - prepay)

            coupon_rate = self._coupon_rate(model, t0, t1)
            accrual = self._accrual_factor(dt)
            interest_cf = outstanding_after_prepay * coupon_rate * accrual

            scheduled = 0.0
            if i > self.interest_only_periods:
                scheduled = min(outstanding_after_prepay, schedule[i - 1])

            total = interest_cf + prepay + scheduled
            cashflows.append(Cashflow(time=t1, amount=total))
            outstanding = max(0.0, outstanding_after_prepay - scheduled)

        if outstanding > 1e-8:
            cashflows.append(Cashflow(time=periods * dt, amount=outstanding))
        return cashflows

    def _coupon_rate(self, model: InterestRateModel, t0: float, t1: float) -> float:
        if self.coupon_type == "fixed":
            return self.fixed_rate
        if self.coupon_type == "floating":
            return model.forward_rate(t0, t1) + self.spread
        raise ValueError("coupon_type must be fixed or floating")

    def _scheduled_principal(self, periods: int) -> list[float]:
        if self.amortization_mode == "bullet":
            principal = [0.0] * periods
            principal[-1] = self.notional
            return principal
        if self.amortization_mode == "linear":
            equal = self.notional / periods
            return [equal] * periods
        if self.amortization_mode == "custom":
            if len(self.custom_amortization) != periods:
                raise ValueError("custom_amortization length must equal number of periods")
            return [float(x) for x in self.custom_amortization]
        raise ValueError("amortization_mode must be bullet, linear, or custom")

    def _prepayment_amount(self, outstanding: float, dt: float) -> float:
        if self.periodic_prepayment_rate is not None:
            rate = max(0.0, self.periodic_prepayment_rate)
        else:
            annual = max(0.0, self.annual_cpr)
            rate = 1.0 - (1.0 - annual) ** dt
        return outstanding * rate

    def _accrual_factor(self, dt: float) -> float:
        dc = self.day_count.upper()
        if dc in {"30/360", "ACT/365", "ACT/360"}:
            return dt
        raise ValueError("unsupported day_count")
