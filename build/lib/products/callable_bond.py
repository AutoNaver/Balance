from __future__ import annotations

from dataclasses import dataclass
import math

from models.base import InterestRateModel
from products.base import Product


@dataclass(frozen=True)
class CallableFixedRateBond(Product):
    """Callable fixed-rate bond priced on a simple short-rate lattice."""

    notional: float
    coupon_rate: float
    maturity_years: float
    coupon_frequency: int = 1
    call_schedule: tuple[tuple[float, float], ...] = ()  # (call_time_years, call_price)
    short_rate_volatility: float = 0.01

    def present_value(self, scenario: dict, as_of_date: str | None = None) -> float:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        return self.price_with_oas(0.0, scenario, as_of_date)

    def get_cashflows(self, scenario: dict, as_of_date: str | None = None):
        # Callable valuation is path-dependent; deterministic contractual schedule only.
        dt = 1.0 / self.coupon_frequency
        n = int(round(self.maturity_years * self.coupon_frequency))
        if n <= 0:
            raise ValueError("invalid maturity/frequency")
        coupon = self.notional * self.coupon_rate * dt
        from products.base import Cashflow

        cfs = []
        for i in range(1, n + 1):
            t = i * dt
            amt = coupon + (self.notional if i == n else 0.0)
            cfs.append(Cashflow(time=t, amount=amt))
        return cfs

    def valuation_breakdown(
        self,
        scenario: dict,
        as_of_date: str | None = None,
        accrued_interest: float = 0.0,
    ) -> dict[str, float]:
        dirty = self.present_value(scenario, as_of_date)
        clean = dirty - accrued_interest
        return {
            "dirty_pv": dirty,
            "clean_pv": clean,
            "accrued_interest": accrued_interest,
            "dirty_price_pct": 100.0 * dirty / self.notional,
            "clean_price_pct": 100.0 * clean / self.notional,
        }

    def price_with_oas(self, oas: float, scenario: dict, as_of_date: str | None = None) -> float:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")

        dt = 1.0 / self.coupon_frequency
        n = int(round(self.maturity_years * self.coupon_frequency))
        if n <= 0:
            raise ValueError("invalid maturity/frequency")

        coupon = self.notional * self.coupon_rate * dt
        sigma = max(self.short_rate_volatility, 0.0)
        sqrt_dt = math.sqrt(dt)

        call_map = {float(t): float(price) for t, price in self.call_schedule}

        values = [self.notional for _ in range(n + 1)]
        for i in range(n - 1, -1, -1):
            t_i = i * dt
            t_pay = (i + 1) * dt
            next_vals: list[float] = []
            for j in range(i + 1):
                state = 2 * j - i
                local_r = model.short_rate(t_i) + state * sigma * sqrt_dt + oas
                disc = math.exp(-local_r * dt)
                cont = disc * (0.5 * values[j] + 0.5 * values[j + 1] + coupon)
                if t_pay in call_map:
                    call_val = disc * (call_map[t_pay] + coupon)
                    cont = min(cont, call_val)
                next_vals.append(cont)
            values = next_vals
        return float(values[0])

    def option_adjusted_spread(
        self,
        target_dirty_price: float,
        scenario: dict,
        as_of_date: str | None = None,
        lower: float = -0.10,
        upper: float = 0.50,
        tol: float = 1e-10,
        max_iter: int = 200,
    ) -> float:
        if target_dirty_price <= 0.0:
            raise ValueError("target_dirty_price must be positive")

        def f(x: float) -> float:
            return self.price_with_oas(x, scenario, as_of_date) - target_dirty_price

        lo, hi = lower, upper
        flo, fhi = f(lo), f(hi)
        while flo * fhi > 0.0 and hi < 5.0:
            hi *= 1.5
            fhi = f(hi)
        if flo * fhi > 0.0:
            raise ValueError("Unable to bracket OAS root")

        for _ in range(max_iter):
            mid = 0.5 * (lo + hi)
            fm = f(mid)
            if abs(fm) < tol:
                return mid
            if flo * fm <= 0:
                hi, fhi = mid, fm
            else:
                lo, flo = mid, fm
        return 0.5 * (lo + hi)
