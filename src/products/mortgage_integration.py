from __future__ import annotations

from dataclasses import dataclass
import math

from models.base import InterestRateModel
from products.base import Cashflow, Product


_FREQ_TO_MONTHS = {"monthly": 1, "quarterly": 3, "annual": 12}


@dataclass(frozen=True)
class MortgageConfig:
    notional: float
    fixed_rate: float
    maturity_years: float
    repayment_type: str = "annuity"
    payment_frequency: str = "monthly"
    interest_only_years: float = 0.0
    day_count: str = "30/360"
    start_month: int = 1

    def validate(self) -> None:
        if self.notional <= 0.0:
            raise ValueError("notional must be positive")
        if self.maturity_years <= 0.0:
            raise ValueError("maturity_years must be positive")
        if self.payment_frequency not in _FREQ_TO_MONTHS:
            raise ValueError("payment_frequency must be one of: monthly, quarterly, annual")
        if self.start_month < 1 or self.start_month > 12:
            raise ValueError("start_month must be in [1, 12]")
        if self.day_count.upper() not in {"30/360", "ACT/365"}:
            raise ValueError("day_count must be one of: 30/360, ACT/365")


class PrepaymentModel:
    def annual_cpr(
        self,
        *,
        fixed_rate: float,
        refinance_rate: float,
        age_years: float,
        maturity_years: float,
        month_index: int,
    ) -> float:
        raise NotImplementedError


@dataclass(frozen=True)
class ConstantCPRPrepayment(PrepaymentModel):
    cpr: float = 0.0

    def annual_cpr(
        self,
        *,
        fixed_rate: float,
        refinance_rate: float,
        age_years: float,
        maturity_years: float,
        month_index: int,
        ) -> float:
        return max(0.0, float(self.cpr))


@dataclass(frozen=True)
class CleanRoomBehaviouralPrepayment(PrepaymentModel):
    """Replicated behavioural CPR model for integrated mortgage products."""

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

    def annual_cpr(
        self,
        *,
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
        seasonality_component = max(0.0, self.seasonality_factors[month_index - 1] - 1.0)

        combined = (
            self.base_cpr
            + self.incentive_weight * incentive_component
            + self.age_weight * age_component
            + self.seasonality_weight * seasonality_component
        )
        return min(self.max_cpr, max(self.min_cpr, combined))


@dataclass(frozen=True)
class MortgagePeriodBreakdown:
    period_index: int
    t0: float
    t1: float
    begin_balance: float
    interest_cashflow: float
    scheduled_principal: float
    prepayment: float
    total_cashflow: float
    end_balance: float
    annual_cpr: float
    smm: float


@dataclass(frozen=True)
class MortgageCashflowGenerator:
    config: MortgageConfig
    prepayment_model: PrepaymentModel | None = None

    def generate(self, model: InterestRateModel) -> list[Cashflow]:
        return [
            Cashflow(time=row.t1, amount=row.total_cashflow)
            for row in self.generate_schedule(model)
        ]

    def generate_schedule(self, model: InterestRateModel) -> list[MortgagePeriodBreakdown]:
        cfg = self.config
        cfg.validate()
        months_per_period = _FREQ_TO_MONTHS[cfg.payment_frequency]

        periods = int(round(cfg.maturity_years * 12 / months_per_period))
        dt = months_per_period / 12.0
        interest_only_periods = int(round(cfg.interest_only_years * 12 / months_per_period))
        rate_per_period = cfg.fixed_rate * self._day_count_factor(cfg.day_count, dt)

        balance = cfg.notional
        annuity_payment = self._annuity_payment(rate_per_period, periods, interest_only_periods)
        const_principal = 0.0
        if cfg.repayment_type == "constant_repayment":
            const_principal = cfg.notional / max(1, periods - interest_only_periods)

        rows: list[MortgagePeriodBreakdown] = []
        for i in range(1, periods + 1):
            if balance <= 1e-8:
                break
            t0 = (i - 1) * dt
            t1 = i * dt
            begin_balance = balance
            interest_cf = balance * rate_per_period
            scheduled = self._scheduled_principal(
                repayment_type=cfg.repayment_type,
                i=i,
                periods=periods,
                interest_only_periods=interest_only_periods,
                annuity_payment=annuity_payment,
                interest_cf=interest_cf,
                const_principal=const_principal,
                balance=balance,
            )
            scheduled = min(balance, scheduled)
            post_sched = balance - scheduled

            prepay = 0.0
            cpr = 0.0
            smm = 0.0
            if self.prepayment_model is not None and post_sched > 0.0:
                remaining = max(1e-6, cfg.maturity_years - t0)
                refinance = model.forward_rate(t0, min(cfg.maturity_years, t0 + remaining))
                month = ((cfg.start_month - 1) + i - 1) % 12 + 1
                cpr = self.prepayment_model.annual_cpr(
                    fixed_rate=cfg.fixed_rate,
                    refinance_rate=refinance,
                    age_years=t0,
                    maturity_years=cfg.maturity_years,
                    month_index=month,
                )
                smm = 1.0 - (1.0 - max(0.0, cpr)) ** max(1e-8, dt)
                prepay = min(post_sched, post_sched * smm)
            end_balance = post_sched - prepay
            total_cf = interest_cf + scheduled + prepay

            rows.append(
                MortgagePeriodBreakdown(
                    period_index=i,
                    t0=t0,
                    t1=t1,
                    begin_balance=begin_balance,
                    interest_cashflow=interest_cf,
                    scheduled_principal=scheduled,
                    prepayment=prepay,
                    total_cashflow=total_cf,
                    end_balance=end_balance,
                    annual_cpr=cpr,
                    smm=smm,
                )
            )
            balance = end_balance

        if balance > 1e-8:
            rows.append(
                MortgagePeriodBreakdown(
                    period_index=periods + 1,
                    t0=periods * dt,
                    t1=periods * dt,
                    begin_balance=balance,
                    interest_cashflow=0.0,
                    scheduled_principal=0.0,
                    prepayment=0.0,
                    total_cashflow=balance,
                    end_balance=0.0,
                    annual_cpr=0.0,
                    smm=0.0,
                )
            )
        return rows

    def _annuity_payment(self, rate_per_period: float, periods: int, io_periods: int) -> float:
        n = periods - io_periods
        if n <= 0:
            return 0.0
        if rate_per_period == 0.0:
            return self.config.notional / n
        return self.config.notional * rate_per_period / (1.0 - (1.0 + rate_per_period) ** (-n))

    def _scheduled_principal(
        self,
        *,
        repayment_type: str,
        i: int,
        periods: int,
        interest_only_periods: int,
        annuity_payment: float,
        interest_cf: float,
        const_principal: float,
        balance: float,
    ) -> float:
        if i <= interest_only_periods:
            return 0.0
        if repayment_type == "annuity":
            return max(0.0, annuity_payment - interest_cf)
        if repayment_type == "constant_repayment":
            return const_principal
        if repayment_type == "interest_only_then_amortizing":
            return balance / max(1, periods - i + 1)
        raise ValueError("Unsupported repayment_type")

    def _day_count_factor(self, day_count: str, dt: float) -> float:
        dc = day_count.upper()
        if dc in {"30/360", "ACT/365"}:
            return dt
        raise ValueError("day_count must be one of: 30/360, ACT/365")


@dataclass(frozen=True)
class IntegratedMortgageLoan(Product):
    """Unified-engine mortgage product backed by reusable cashflow service."""

    cashflow_generator: MortgageCashflowGenerator

    def get_cashflows(self, scenario: dict, as_of_date: str | None = None) -> list[Cashflow]:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        return self.cashflow_generator.generate(model)

    def detailed_schedule(
        self,
        scenario: dict,
        as_of_date: str | None = None,
    ) -> list[MortgagePeriodBreakdown]:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        return self.cashflow_generator.generate_schedule(model)

    def present_value(self, scenario: dict, as_of_date: str | None = None) -> float:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        return sum(cf.amount * model.discount_factor(cf.time) for cf in self.cashflow_generator.generate(model))


@dataclass(frozen=True)
class IntegratedGermanFixedRateMortgageLoan(Product):
    """Replicated German fixed-rate mortgage feature set using clean-room components."""

    notional: float
    fixed_rate: float
    maturity_years: float
    repayment_type: str = "annuity"
    payment_frequency: str = "monthly"
    interest_only_years: float = 0.0
    day_count: str = "30/360"
    prepayment_model: PrepaymentModel | None = None
    start_month: int = 1

    def _generator(self) -> MortgageCashflowGenerator:
        return MortgageCashflowGenerator(
            config=MortgageConfig(
                notional=self.notional,
                fixed_rate=self.fixed_rate,
                maturity_years=self.maturity_years,
                repayment_type=self.repayment_type,
                payment_frequency=self.payment_frequency,
                interest_only_years=self.interest_only_years,
                day_count=self.day_count,
                start_month=self.start_month,
            ),
            prepayment_model=self.prepayment_model,
        )

    def get_cashflows(self, scenario: dict, as_of_date: str | None = None) -> list[Cashflow]:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        return self._generator().generate(model)

    def detailed_schedule(
        self,
        scenario: dict,
        as_of_date: str | None = None,
    ) -> list[MortgagePeriodBreakdown]:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        return self._generator().generate_schedule(model)

    def present_value(self, scenario: dict, as_of_date: str | None = None) -> float:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        return sum(cf.amount * model.discount_factor(cf.time) for cf in self._generator().generate(model))
