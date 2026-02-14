from __future__ import annotations

from dataclasses import dataclass, field
import math

from models.base import InterestRateModel
from products.base import Cashflow, Product


_FREQ_TO_MONTHS = {"monthly": 1, "quarterly": 3, "annual": 12}


@dataclass(frozen=True)
class BehaviouralPrepaymentModel:
    """Deterministic prepayment model combining incentive, age, and seasonality."""

    base_cpr: float = 0.01
    incentive_weight: float = 0.6
    age_weight: float = 0.25
    seasonality_weight: float = 0.15
    incentive_slope: float = 12.0
    age_slope: float = 1.0
    seasonality_factors: tuple[float, ...] = (
        1.10,
        1.10,
        1.00,
        0.98,
        0.98,
        1.00,
        1.02,
        1.02,
        1.00,
        1.00,
        1.08,
        1.12,
    )
    min_cpr: float = 0.0
    max_cpr: float = 0.30

    def __post_init__(self) -> None:
        if len(self.seasonality_factors) != 12:
            raise ValueError("seasonality_factors must contain 12 monthly values")
        if self.min_cpr < 0.0 or self.max_cpr <= self.min_cpr:
            raise ValueError("invalid CPR bounds")

    def cpr(
        self,
        fixed_rate: float,
        refinance_rate: float,
        age_years: float,
        maturity_years: float,
        month_index: int,
    ) -> float:
        if maturity_years <= 0.0:
            raise ValueError("maturity_years must be positive")
        if not (1 <= month_index <= 12):
            raise ValueError("month_index must be in [1, 12]")

        incentive = max(0.0, fixed_rate - refinance_rate)
        incentive_component = 1.0 - math.exp(-self.incentive_slope * incentive)
        age_component = min(1.0, max(0.0, self.age_slope * age_years / maturity_years))
        seasonality_raw = self.seasonality_factors[month_index - 1]
        seasonality_component = max(0.0, seasonality_raw - 1.0)

        combined = (
            self.base_cpr
            + self.incentive_weight * incentive_component
            + self.age_weight * age_component
            + self.seasonality_weight * seasonality_component
        )
        return min(self.max_cpr, max(self.min_cpr, combined))


@dataclass(frozen=True)
class GermanFixedRateMortgageLoan(Product):
    """German-style fixed-rate mortgage with optional behavioural prepayments."""

    notional: float
    fixed_rate: float
    maturity_years: float
    repayment_type: str = "annuity"
    payment_frequency: str = "monthly"
    interest_only_years: float = 0.0
    day_count: str = "30/360"
    prepayment_model: BehaviouralPrepaymentModel | None = field(default=None)
    start_month: int = 1

    def get_cashflows(self, scenario: dict, as_of_date: str | None = None) -> list[Cashflow]:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        return self._expected_cashflows(model)

    def present_value(self, scenario: dict, as_of_date: str | None = None) -> float:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        return sum(cf.amount * model.discount_factor(cf.time) for cf in self._expected_cashflows(model))

    def _expected_cashflows(self, model: InterestRateModel) -> list[Cashflow]:
        months_per_period = _FREQ_TO_MONTHS.get(self.payment_frequency)
        if months_per_period is None:
            raise ValueError("payment_frequency must be one of: monthly, quarterly, annual")
        if self.maturity_years <= 0.0:
            raise ValueError("maturity_years must be positive")
        if self.notional <= 0.0:
            raise ValueError("notional must be positive")
        if self.start_month < 1 or self.start_month > 12:
            raise ValueError("start_month must be in [1, 12]")

        periods = int(round(self.maturity_years * 12 / months_per_period))
        dt = months_per_period / 12.0
        rate_per_period = self.fixed_rate * self._day_count_factor(dt)
        interest_only_periods = int(round(self.interest_only_years * 12 / months_per_period))

        balance = self.notional
        cashflows: list[Cashflow] = []
        annuity_payment = self._annuity_payment(rate_per_period, periods, interest_only_periods)
        const_principal = 0.0
        if self.repayment_type == "constant_repayment":
            amort_periods = max(1, periods - interest_only_periods)
            const_principal = self.notional / amort_periods

        for i in range(1, periods + 1):
            if balance <= 1e-8:
                break
            t0 = (i - 1) * dt
            t1 = i * dt
            interest_cf = balance * rate_per_period

            if i <= interest_only_periods:
                scheduled_principal = 0.0
            elif self.repayment_type == "annuity":
                scheduled_principal = max(0.0, annuity_payment - interest_cf)
            elif self.repayment_type == "constant_repayment":
                scheduled_principal = const_principal
            elif self.repayment_type == "interest_only_then_amortizing":
                remaining_periods = max(1, periods - i + 1)
                scheduled_principal = balance / remaining_periods
            else:
                raise ValueError(
                    "repayment_type must be one of: annuity, constant_repayment, interest_only_then_amortizing"
                )

            scheduled_principal = min(balance, scheduled_principal)
            post_sched_balance = balance - scheduled_principal
            prepay = self._prepayment_amount(model, t0, t1, i, post_sched_balance)
            prepay = min(post_sched_balance, prepay)

            total_cf = interest_cf + scheduled_principal + prepay
            cashflows.append(Cashflow(time=t1, amount=total_cf))
            balance = post_sched_balance - prepay

        if balance > 1e-8:
            cashflows.append(Cashflow(time=periods * dt, amount=balance))
        return cashflows

    def _annuity_payment(self, rate_per_period: float, periods: int, interest_only_periods: int) -> float:
        amort_periods = periods - interest_only_periods
        if amort_periods <= 0:
            return 0.0
        if rate_per_period == 0.0:
            return self.notional / amort_periods
        # Payment level applies from first amortizing period onward.
        return self.notional * rate_per_period / (1.0 - (1.0 + rate_per_period) ** (-amort_periods))

    def _prepayment_amount(
        self,
        model: InterestRateModel,
        t0: float,
        t1: float,
        period_idx: int,
        outstanding_after_sched: float,
    ) -> float:
        if self.prepayment_model is None or outstanding_after_sched <= 0.0:
            return 0.0

        remaining = max(1e-6, self.maturity_years - t0)
        refinance_rate = model.forward_rate(t0, min(self.maturity_years, t0 + remaining))
        age_years = t0
        month = ((self.start_month - 1) + period_idx - 1) % 12 + 1
        annual_cpr = self.prepayment_model.cpr(
            fixed_rate=self.fixed_rate,
            refinance_rate=refinance_rate,
            age_years=age_years,
            maturity_years=self.maturity_years,
            month_index=month,
        )
        dt = max(1e-8, t1 - t0)
        smm = 1.0 - (1.0 - annual_cpr) ** dt
        return outstanding_after_sched * smm

    def _day_count_factor(self, dt: float) -> float:
        if self.day_count.upper() == "30/360":
            return dt
        if self.day_count.upper() == "ACT/365":
            return dt
        raise ValueError("day_count must be one of: 30/360, ACT/365")
