from __future__ import annotations

from dataclasses import dataclass
import math

from models.base import InterestRateModel
from models.market import DeterministicFXCurve, DeterministicHazardCurve
from products.base import Cashflow, Product


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


@dataclass(frozen=True)
class FXForward(Product):
    """Single-period FX forward valued in domestic currency."""

    notional_foreign: float
    strike: float  # domestic per unit foreign
    maturity_years: float
    pay_foreign_receive_domestic: bool = True

    def leg_cashflows(self, scenario: dict, as_of_date: str | None = None) -> dict[str, list[Cashflow]]:
        """Return exposure-ready cashflow decomposition."""
        return {"net_cashflows": self.get_cashflows(scenario, as_of_date)}

    def get_cashflows(self, scenario: dict, as_of_date: str | None = None) -> list[Cashflow]:
        model = scenario.get("model")
        fx_curve = scenario.get("fx_curve")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        if not isinstance(fx_curve, DeterministicFXCurve):
            raise TypeError("scenario['fx_curve'] must be DeterministicFXCurve")
        sign = 1.0 if self.pay_foreign_receive_domestic else -1.0
        payoff = sign * self.notional_foreign * (fx_curve.fx_forward(self.maturity_years) - self.strike)
        return [Cashflow(time=self.maturity_years, amount=payoff)]

    def present_value(self, scenario: dict, as_of_date: str | None = None) -> float:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        cfs = self.get_cashflows(scenario, as_of_date)
        return sum(cf.amount * model.discount_factor(cf.time) for cf in cfs)


@dataclass(frozen=True)
class FXSwap(Product):
    """Two-leg FX swap valued in domestic currency."""

    notional_foreign: float
    near_rate: float
    far_rate: float | None
    near_maturity_years: float
    far_maturity_years: float
    pay_foreign_receive_domestic: bool = True

    def leg_cashflows(self, scenario: dict, as_of_date: str | None = None) -> dict[str, list[Cashflow]]:
        """Return near/far leg decomposition for exposure analytics."""
        if self.far_maturity_years <= self.near_maturity_years:
            raise ValueError("far_maturity_years must be greater than near_maturity_years")
        sign = 1.0 if self.pay_foreign_receive_domestic else -1.0
        implied_far_rate = self.far_rate if self.far_rate is not None else self._implied_far_rate_from_curves(scenario)
        near_leg = [Cashflow(time=self.near_maturity_years, amount=sign * self.notional_foreign * self.near_rate)]
        far_leg = [Cashflow(time=self.far_maturity_years, amount=-sign * self.notional_foreign * implied_far_rate)]
        return {
            "near_leg_cashflows": near_leg,
            "far_leg_cashflows": far_leg,
            "net_cashflows": near_leg + far_leg,
        }

    def get_cashflows(self, scenario: dict, as_of_date: str | None = None) -> list[Cashflow]:
        return self.leg_cashflows(scenario, as_of_date)["net_cashflows"]

    def present_value(self, scenario: dict, as_of_date: str | None = None) -> float:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        return sum(cf.amount * model.discount_factor(cf.time) for cf in self.get_cashflows(scenario, as_of_date))

    def _implied_far_rate_from_curves(self, scenario: dict) -> float:
        domestic_model = scenario.get("model")
        foreign_model = scenario.get("foreign_model")
        if not isinstance(domestic_model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        if not isinstance(foreign_model, InterestRateModel):
            raise TypeError("scenario['foreign_model'] must implement InterestRateModel when far_rate is None")
        t_near = self.near_maturity_years
        t_far = self.far_maturity_years
        if t_far <= t_near:
            raise ValueError("far_maturity_years must be greater than near_maturity_years")
        if t_far <= 0.0:
            return self.near_rate
        # Broken-date covered interest parity from near date to far date.
        df_d_near = domestic_model.discount_factor(t_near)
        df_d_far = domestic_model.discount_factor(t_far)
        df_f_near = foreign_model.discount_factor(t_near)
        df_f_far = foreign_model.discount_factor(t_far)
        return self.near_rate * (df_f_far / max(df_f_near, 1e-12)) / max(df_d_far / max(df_d_near, 1e-12), 1e-12)


@dataclass(frozen=True)
class EuropeanSwaption(Product):
    """Black-76 European swaption on a fixed-float swap approximation."""

    notional: float
    strike: float
    option_maturity_years: float
    swap_tenor_years: float
    fixed_leg_frequency: int = 1
    volatility: float = 0.20
    is_payer: bool = True

    def get_cashflows(self, scenario: dict, as_of_date: str | None = None) -> list[Cashflow]:
        # Option payoff represented as a single expected discounted flow at expiry.
        return [Cashflow(time=self.option_maturity_years, amount=self.present_value(scenario, as_of_date))]

    def present_value(self, scenario: dict, as_of_date: str | None = None) -> float:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")

        expiry = self.option_maturity_years
        tenor = self.swap_tenor_years
        dt = 1.0 / self.fixed_leg_frequency
        n = int(round(tenor * self.fixed_leg_frequency))
        if n <= 0:
            raise ValueError("invalid swap tenor/frequency")
        payment_times = [expiry + (i + 1) * dt for i in range(n)]
        annuity = sum(dt * model.discount_factor(t) for t in payment_times)
        if annuity <= 0.0:
            raise ValueError("annuity must be positive")

        p_start = model.discount_factor(expiry)
        p_end = model.discount_factor(expiry + tenor)
        forward_swap_rate = (p_start - p_end) / annuity

        sigma_sqrt_t = self.volatility * math.sqrt(max(expiry, 1e-12))
        if sigma_sqrt_t <= 0.0:
            intrinsic = max(0.0, (forward_swap_rate - self.strike) if self.is_payer else (self.strike - forward_swap_rate))
            return self.notional * annuity * intrinsic

        d1 = (math.log(max(forward_swap_rate, 1e-12) / max(self.strike, 1e-12)) + 0.5 * sigma_sqrt_t**2) / sigma_sqrt_t
        d2 = d1 - sigma_sqrt_t
        if self.is_payer:
            price = forward_swap_rate * _norm_cdf(d1) - self.strike * _norm_cdf(d2)
        else:
            price = self.strike * _norm_cdf(-d2) - forward_swap_rate * _norm_cdf(-d1)
        return self.notional * annuity * price


@dataclass(frozen=True)
class CreditDefaultSwap(Product):
    """Running spread CDS with deterministic hazard and discount curves."""

    notional: float
    spread_bps: float
    maturity_years: float
    payment_frequency: int = 4
    recovery_rate: float = 0.40
    protection_buyer: bool = True

    def get_cashflows(self, scenario: dict, as_of_date: str | None = None) -> list[Cashflow]:
        # Represent each premium payment as deterministic expected net cashflow.
        model = scenario.get("model")
        hazard_curve = scenario.get("hazard_curve")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        if not isinstance(hazard_curve, DeterministicHazardCurve):
            raise TypeError("scenario['hazard_curve'] must be DeterministicHazardCurve")

        leg = self.leg_present_values(scenario, as_of_date, as_cashflows=True)
        return leg["net_cashflows"]

    def present_value(self, scenario: dict, as_of_date: str | None = None) -> float:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        legs = self.leg_present_values(scenario, as_of_date, as_cashflows=False)
        return float(legs["protection_leg_pv"] - legs["premium_leg_pv"])

    def leg_present_values(
        self,
        scenario: dict,
        as_of_date: str | None = None,
        as_cashflows: bool = False,
    ) -> dict[str, float] | dict[str, list[Cashflow]]:
        model = scenario.get("model")
        hazard_curve = scenario.get("hazard_curve")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        if not isinstance(hazard_curve, DeterministicHazardCurve):
            raise TypeError("scenario['hazard_curve'] must be DeterministicHazardCurve")

        dt = 1.0 / self.payment_frequency
        n = int(round(self.maturity_years * self.payment_frequency))
        sign = 1.0 if self.protection_buyer else -1.0
        spread = self.spread_bps / 10_000.0

        premium_cfs: list[Cashflow] = []
        protection_cfs: list[Cashflow] = []
        net_cfs: list[Cashflow] = []
        premium_pv = 0.0
        protection_pv = 0.0

        for i in range(1, n + 1):
            t = i * dt
            survival = hazard_curve.survival_probability(t)
            default_prob = max(0.0, hazard_curve.survival_probability(t - dt) - survival)
            premium_amount = sign * self.notional * spread * dt * survival
            protection_amount = sign * self.notional * (1.0 - self.recovery_rate) * default_prob
            df = model.discount_factor(t)
            premium_pv += premium_amount * df
            protection_pv += protection_amount * df

            premium_cfs.append(Cashflow(time=t, amount=premium_amount))
            protection_cfs.append(Cashflow(time=t, amount=protection_amount))
            net_cfs.append(Cashflow(time=t, amount=protection_amount - premium_amount))

        if as_cashflows:
            return {
                "premium_cashflows": premium_cfs,
                "protection_cashflows": protection_cfs,
                "net_cashflows": net_cfs,
            }
        return {
            "premium_leg_pv": premium_pv,
            "protection_leg_pv": protection_pv,
        }


@dataclass(frozen=True)
class CrossCurrencySwap(Product):
    """Deterministic CCS with start/end notional exchange and fixed/floating coupon choice."""

    domestic_notional: float
    foreign_notional: float
    maturity_years: float
    domestic_frequency: int = 2
    foreign_frequency: int = 2
    domestic_fixed_rate: float | None = None
    foreign_fixed_rate: float | None = None
    domestic_spread: float = 0.0
    foreign_spread: float = 0.0
    pay_domestic_receive_foreign: bool = True
    exchange_notionals: bool = True
    mark_to_market: bool = False

    def leg_cashflows(self, scenario: dict, as_of_date: str | None = None) -> dict[str, list[Cashflow]]:
        """Return decomposed leg/notional/reset cashflows for exposure reporting."""
        domestic_model = scenario.get("model")
        foreign_model = scenario.get("foreign_model")
        fx_curve = scenario.get("fx_curve")
        if not isinstance(domestic_model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        if not isinstance(foreign_model, InterestRateModel):
            raise TypeError("scenario['foreign_model'] must implement InterestRateModel")
        if not isinstance(fx_curve, DeterministicFXCurve):
            raise TypeError("scenario['fx_curve'] must be DeterministicFXCurve")

        notional_exchange_cashflows: list[Cashflow] = []
        reset_exchange_cashflows: list[Cashflow] = []
        sign = -1.0 if self.pay_domestic_receive_foreign else 1.0
        current_foreign_notional = self.foreign_notional
        if self.mark_to_market:
            current_foreign_notional = self.domestic_notional / max(fx_curve.fx_forward(0.0), 1e-12)

        if self.exchange_notionals:
            notional_exchange_cashflows.append(Cashflow(time=0.0, amount=sign * self.domestic_notional))
            notional_exchange_cashflows.append(
                Cashflow(time=0.0, amount=-sign * current_foreign_notional * fx_curve.fx_forward(0.0))
            )

        domestic_leg_cashflows = self._leg_cashflows(
            domestic_model,
            self.domestic_notional,
            self.domestic_frequency,
            self.domestic_fixed_rate,
            self.domestic_spread,
            sign,
        )
        foreign_leg_cashflows = self._leg_cashflows(
            foreign_model,
            current_foreign_notional,
            self.foreign_frequency,
            self.foreign_fixed_rate,
            self.foreign_spread,
            -sign,
            fx_curve,
            convert_foreign=True,
            mark_to_market=self.mark_to_market,
        )

        if self.mark_to_market and self.exchange_notionals:
            n_resets = int(round(self.maturity_years * self.foreign_frequency))
            dt = 1.0 / self.foreign_frequency
            for i in range(1, n_resets):
                t = i * dt
                new_foreign_notional = self.domestic_notional / max(fx_curve.fx_forward(t), 1e-12)
                delta_foreign = new_foreign_notional - current_foreign_notional
                adjustment_domestic = -sign * delta_foreign * fx_curve.fx_forward(t)
                reset_exchange_cashflows.append(Cashflow(time=t, amount=adjustment_domestic))
                current_foreign_notional = new_foreign_notional

        if self.exchange_notionals:
            t = self.maturity_years
            notional_exchange_cashflows.append(Cashflow(time=t, amount=-sign * self.domestic_notional))
            notional_exchange_cashflows.append(Cashflow(time=t, amount=sign * current_foreign_notional * fx_curve.fx_forward(t)))

        net_cashflows = (
            notional_exchange_cashflows
            + domestic_leg_cashflows
            + foreign_leg_cashflows
            + reset_exchange_cashflows
        )
        return {
            "notional_exchange_cashflows": notional_exchange_cashflows,
            "domestic_leg_cashflows": domestic_leg_cashflows,
            "foreign_leg_cashflows": foreign_leg_cashflows,
            "reset_exchange_cashflows": reset_exchange_cashflows,
            "net_cashflows": net_cashflows,
        }

    def get_cashflows(self, scenario: dict, as_of_date: str | None = None) -> list[Cashflow]:
        return self.leg_cashflows(scenario, as_of_date)["net_cashflows"]

    def present_value(self, scenario: dict, as_of_date: str | None = None) -> float:
        domestic_model = scenario.get("model")
        if not isinstance(domestic_model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        return sum(cf.amount * domestic_model.discount_factor(cf.time) for cf in self.get_cashflows(scenario, as_of_date))

    def _leg_cashflows(
        self,
        model: InterestRateModel,
        notional: float,
        frequency: int,
        fixed_rate: float | None,
        spread: float,
        sign: float,
        fx_curve: DeterministicFXCurve | None = None,
        convert_foreign: bool = False,
        mark_to_market: bool = False,
    ) -> list[Cashflow]:
        n = int(round(self.maturity_years * frequency))
        dt = 1.0 / frequency
        cfs: list[Cashflow] = []
        for i in range(1, n + 1):
            t0 = (i - 1) * dt
            t1 = i * dt
            effective_notional = notional
            if mark_to_market and convert_foreign:
                if fx_curve is None:
                    raise ValueError("fx_curve required for mark-to-market conversion")
                effective_notional = self.domestic_notional / max(fx_curve.fx_forward(t0), 1e-12)
            rate = fixed_rate if fixed_rate is not None else model.forward_rate(t0, t1)
            amount = sign * effective_notional * (rate + spread) * dt
            if convert_foreign:
                if fx_curve is None:
                    raise ValueError("fx_curve required for foreign leg conversion")
                amount *= fx_curve.fx_forward(t1)
            cfs.append(Cashflow(time=t1, amount=amount))
        return cfs


@dataclass(frozen=True)
class InterestRateCapFloor(Product):
    """Black-style cap/floor valuation on simple forward rates."""

    notional: float
    strike: float
    maturity_years: float
    payment_frequency: int = 4
    volatility: float = 0.20
    is_cap: bool = True

    def get_cashflows(self, scenario: dict, as_of_date: str | None = None) -> list[Cashflow]:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        dt = 1.0 / self.payment_frequency
        n = int(round(self.maturity_years * self.payment_frequency))
        cfs: list[Cashflow] = []
        for i in range(1, n + 1):
            t0 = (i - 1) * dt
            t1 = i * dt
            optionlet = self._optionlet_value(model, t0, t1)
            cfs.append(Cashflow(time=t1, amount=optionlet / max(model.discount_factor(t1), 1e-12)))
        return cfs

    def present_value(self, scenario: dict, as_of_date: str | None = None) -> float:
        model = scenario.get("model")
        if not isinstance(model, InterestRateModel):
            raise TypeError("scenario['model'] must implement InterestRateModel")
        dt = 1.0 / self.payment_frequency
        n = int(round(self.maturity_years * self.payment_frequency))
        return sum(self._optionlet_value(model, (i - 1) * dt, i * dt) for i in range(1, n + 1))

    def _optionlet_value(self, model: InterestRateModel, t0: float, t1: float) -> float:
        fwd = max(model.forward_rate(t0, t1), 1e-12)
        k = max(self.strike, 1e-12)
        tau = max(t1 - t0, 1e-12)
        expiry = max(t0, 1e-12)
        vol_term = self.volatility * math.sqrt(expiry)
        df = model.discount_factor(t1)

        if vol_term <= 0.0:
            intrinsic = max(0.0, (fwd - k) if self.is_cap else (k - fwd))
            return self.notional * tau * df * intrinsic

        d1 = (math.log(fwd / k) + 0.5 * vol_term**2) / vol_term
        d2 = d1 - vol_term
        if self.is_cap:
            payoff = fwd * _norm_cdf(d1) - k * _norm_cdf(d2)
        else:
            payoff = k * _norm_cdf(-d2) - fwd * _norm_cdf(-d1)
        return self.notional * tau * df * payoff
