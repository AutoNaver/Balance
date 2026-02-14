from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from engine.collateral import CSAConfig
from models.base import InterestRateModel
from models.curve import DeterministicZeroCurve
from products.base import Product
from products.bond import FixedRateBond
from products.corporate_bond import CorporateBond
from products.derivatives import CreditDefaultSwap, CrossCurrencySwap, EuropeanSwaption, FXForward, FXSwap, InterestRateCapFloor
from products.mortgage_integration import (
    CleanRoomBehaviouralPrepayment,
    ConstantCPRPrepayment,
    IntegratedGermanFixedRateMortgageLoan,
    IntegratedMortgageLoan,
    MortgageCashflowGenerator,
    MortgageConfig,
)
from products.mortgage import BehaviouralPrepaymentModel, GermanFixedRateMortgageLoan
from products.swap import FixedFloatSwap, FloatFloatSwap


def load_zero_curve_csv(path: str | Path) -> DeterministicZeroCurve:
    data = np.genfromtxt(path, delimiter=",", names=True, dtype=float)
    return DeterministicZeroCurve(
        tenors=np.array(data["tenor_years"], dtype=float),
        zero_rates=np.array(data["zero_rate"], dtype=float),
    )


def load_fixed_bond_portfolio_csv(path: str | Path) -> list[FixedRateBond]:
    rows = np.genfromtxt(path, delimiter=",", names=True, dtype=None, encoding="utf-8")
    if rows.shape == ():
        rows = np.array([rows], dtype=rows.dtype)
    portfolio: list[FixedRateBond] = []
    for row in rows:
        portfolio.append(
            FixedRateBond(
                notional=float(row["notional"]),
                coupon_rate=float(row["coupon_rate"]),
                maturity_years=float(row["maturity_years"]),
                coupon_frequency=int(row["coupon_frequency"]),
            )
        )
    return portfolio


def load_mixed_portfolio_csv(path: str | Path) -> list[Product]:
    portfolio: list[Product] = []
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            product_type = str(row.get("product_type", "")).strip().lower()
            if not product_type:
                continue
            portfolio.append(_parse_product_row(row, product_type))
    return portfolio


def load_product_netting_set_map_csv(path: str | Path) -> dict[int, str]:
    mapping: dict[int, str] = {}
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            idx = _to_int(row, "product_index")
            netting_set_id = _to_str(row, "netting_set_id")
            if not netting_set_id:
                raise ValueError("netting_set_id must be non-empty")
            mapping[idx] = netting_set_id
    return mapping


def load_csa_configs_csv(path: str | Path, discount_models: dict[str, InterestRateModel]) -> dict[str, CSAConfig]:
    configs: dict[str, CSAConfig] = {}
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            netting_set_id = _to_str(row, "netting_set_id")
            model_key = _to_str(row, "discount_model_key")
            if model_key not in discount_models:
                raise ValueError(f"Unknown discount_model_key: {model_key}")
            configs[netting_set_id] = CSAConfig(
                netting_set_id=netting_set_id,
                discount_model=discount_models[model_key],
                collateral_rate=_to_float(row, "collateral_rate", 0.0),
                threshold=_to_float(row, "threshold", 0.0),
                minimum_transfer_amount=_to_float(row, "minimum_transfer_amount", 0.0),
            )
    return configs


def _parse_product_row(row: dict[str, str], product_type: str) -> Product:
    if product_type == "fixed_bond":
        return FixedRateBond(
            notional=_to_float(row, "notional"),
            coupon_rate=_to_float(row, "coupon_or_fixed_rate"),
            maturity_years=_to_float(row, "maturity_years"),
            coupon_frequency=_to_int(row, "fixed_frequency", 1),
        )
    if product_type == "fixed_float_swap":
        return FixedFloatSwap(
            notional=_to_float(row, "notional"),
            fixed_rate=_to_float(row, "coupon_or_fixed_rate"),
            maturity_years=_to_float(row, "maturity_years"),
            fixed_frequency=_to_int(row, "fixed_frequency", 1),
            float_frequency=_to_int(row, "float_frequency", 4),
            pay_fixed=_to_bool(row, "pay_fixed", True),
        )
    if product_type == "float_float_swap":
        return FloatFloatSwap(
            notional=_to_float(row, "notional"),
            maturity_years=_to_float(row, "maturity_years"),
            pay_leg_frequency=_to_int(row, "fixed_frequency", 4),
            receive_leg_frequency=_to_int(row, "float_frequency", 4),
            pay_spread=_to_float(row, "pay_spread", 0.0),
            receive_spread=_to_float(row, "receive_spread", 0.0),
            pay_leg_sign=_to_int(row, "pay_leg_sign", -1),
        )
    if product_type == "german_fixed_rate_mortgage":
        seasonal = tuple(float(x) for x in _to_str(row, "seasonality_factors").split("|"))
        model = BehaviouralPrepaymentModel(
            base_cpr=_to_float(row, "base_cpr", 0.01),
            incentive_weight=_to_float(row, "incentive_weight", 0.6),
            age_weight=_to_float(row, "age_weight", 0.25),
            seasonality_weight=_to_float(row, "seasonality_weight", 0.15),
            incentive_slope=_to_float(row, "incentive_slope", 12.0),
            age_slope=_to_float(row, "age_slope", 1.0),
            seasonality_factors=seasonal,
            min_cpr=_to_float(row, "min_cpr", 0.0),
            max_cpr=_to_float(row, "max_cpr", 0.30),
        )
        return GermanFixedRateMortgageLoan(
            notional=_to_float(row, "notional"),
            fixed_rate=_to_float(row, "coupon_or_fixed_rate"),
            maturity_years=_to_float(row, "maturity_years"),
            repayment_type=_to_str(row, "repayment_type", "annuity"),
            payment_frequency=_to_str(row, "payment_frequency", "monthly"),
            interest_only_years=_to_float(row, "interest_only_years", 0.0),
            day_count=_to_str(row, "day_count", "30/360"),
            prepayment_model=model,
            start_month=_to_int(row, "start_month", 1),
        )
    if product_type == "integrated_mortgage":
        cfg = MortgageConfig(
            notional=_to_float(row, "notional"),
            fixed_rate=_to_float(row, "coupon_or_fixed_rate"),
            maturity_years=_to_float(row, "maturity_years"),
            repayment_type=_to_str(row, "repayment_type", "annuity"),
            payment_frequency=_to_str(row, "payment_frequency", "monthly"),
            interest_only_years=_to_float(row, "interest_only_years", 0.0),
            day_count=_to_str(row, "day_count", "30/360"),
            start_month=_to_int(row, "start_month", 1),
        )
        if _to_bool(row, "use_behavioural_prepayment", False):
            seasonal_raw = _to_str(row, "seasonality_factors")
            seasonal = tuple(float(x) for x in seasonal_raw.split("|")) if seasonal_raw else CleanRoomBehaviouralPrepayment().seasonality_factors
            prepay = CleanRoomBehaviouralPrepayment(
                base_cpr=_to_float(row, "base_cpr", 0.01),
                incentive_weight=_to_float(row, "incentive_weight", 0.6),
                age_weight=_to_float(row, "age_weight", 0.25),
                seasonality_weight=_to_float(row, "seasonality_weight", 0.15),
                incentive_slope=_to_float(row, "incentive_slope", 12.0),
                age_slope=_to_float(row, "age_slope", 1.0),
                seasonality_factors=seasonal,
                min_cpr=_to_float(row, "min_cpr", 0.0),
                max_cpr=_to_float(row, "max_cpr", 0.30),
            )
        else:
            prepay = ConstantCPRPrepayment(cpr=_to_float(row, "annual_cpr", 0.0))
        return IntegratedMortgageLoan(cashflow_generator=MortgageCashflowGenerator(cfg, prepayment_model=prepay))
    if product_type == "integrated_german_fixed_rate_mortgage":
        prepay_model = None
        if _to_bool(row, "use_behavioural_prepayment", False):
            seasonal_raw = _to_str(row, "seasonality_factors")
            seasonal = tuple(float(x) for x in seasonal_raw.split("|")) if seasonal_raw else CleanRoomBehaviouralPrepayment().seasonality_factors
            prepay_model = CleanRoomBehaviouralPrepayment(
                base_cpr=_to_float(row, "base_cpr", 0.01),
                incentive_weight=_to_float(row, "incentive_weight", 0.6),
                age_weight=_to_float(row, "age_weight", 0.25),
                seasonality_weight=_to_float(row, "seasonality_weight", 0.15),
                incentive_slope=_to_float(row, "incentive_slope", 12.0),
                age_slope=_to_float(row, "age_slope", 1.0),
                seasonality_factors=seasonal,
                min_cpr=_to_float(row, "min_cpr", 0.0),
                max_cpr=_to_float(row, "max_cpr", 0.30),
            )
        elif _to_float(row, "annual_cpr", 0.0) > 0.0:
            prepay_model = ConstantCPRPrepayment(cpr=_to_float(row, "annual_cpr", 0.0))
        return IntegratedGermanFixedRateMortgageLoan(
            notional=_to_float(row, "notional"),
            fixed_rate=_to_float(row, "coupon_or_fixed_rate"),
            maturity_years=_to_float(row, "maturity_years"),
            repayment_type=_to_str(row, "repayment_type", "annuity"),
            payment_frequency=_to_str(row, "payment_frequency", "monthly"),
            interest_only_years=_to_float(row, "interest_only_years", 0.0),
            day_count=_to_str(row, "day_count", "30/360"),
            prepayment_model=prepay_model,
            start_month=_to_int(row, "start_month", 1),
        )
    if product_type == "corporate_bond":
        custom_raw = _to_str(row, "custom_amortization")
        custom = tuple(float(x) for x in custom_raw.split("|")) if custom_raw else ()
        return CorporateBond(
            notional=_to_float(row, "notional"),
            maturity_years=_to_float(row, "maturity_years"),
            coupon_type=_to_str(row, "coupon_type", "fixed"),
            fixed_rate=_to_float(row, "coupon_or_fixed_rate", 0.0),
            spread=_to_float(row, "spread", 0.0),
            frequency=_to_str(row, "payment_frequency", "semi_annual"),
            day_count=_to_str(row, "day_count", "30/360"),
            amortization_mode=_to_str(row, "amortization_mode", "bullet"),
            custom_amortization=custom,
            interest_only_periods=_to_int(row, "interest_only_periods", 0),
            annual_cpr=_to_float(row, "annual_cpr", 0.0),
            periodic_prepayment_rate=_to_opt_float(row, "periodic_prepayment_rate"),
        )
    if product_type == "fx_forward":
        return FXForward(
            notional_foreign=_to_float(row, "notional_foreign"),
            strike=_to_float(row, "strike"),
            maturity_years=_to_float(row, "maturity_years"),
            pay_foreign_receive_domestic=_to_bool(row, "pay_foreign_receive_domestic", True),
        )
    if product_type == "fx_swap":
        return FXSwap(
            notional_foreign=_to_float(row, "notional_foreign"),
            near_rate=_to_float(row, "near_rate"),
            far_rate=_to_opt_float(row, "far_rate"),
            near_maturity_years=_to_float(row, "near_maturity_years"),
            far_maturity_years=_to_float(row, "far_maturity_years"),
            pay_foreign_receive_domestic=_to_bool(row, "pay_foreign_receive_domestic", True),
        )
    if product_type == "swaption":
        return EuropeanSwaption(
            notional=_to_float(row, "notional"),
            strike=_to_float(row, "strike"),
            option_maturity_years=_to_float(row, "option_maturity_years"),
            swap_tenor_years=_to_float(row, "swap_tenor_years"),
            fixed_leg_frequency=_to_int(row, "fixed_frequency", 1),
            volatility=_to_float(row, "volatility", 0.20),
            is_payer=_to_bool(row, "is_payer", True),
        )
    if product_type == "cds":
        return CreditDefaultSwap(
            notional=_to_float(row, "notional"),
            spread_bps=_to_float(row, "spread_bps"),
            maturity_years=_to_float(row, "maturity_years"),
            payment_frequency=_to_int(row, "float_frequency", 4),
            recovery_rate=_to_float(row, "recovery_rate", 0.40),
            protection_buyer=_to_bool(row, "protection_buyer", True),
        )
    if product_type == "cap_floor":
        return InterestRateCapFloor(
            notional=_to_float(row, "notional"),
            strike=_to_float(row, "strike"),
            maturity_years=_to_float(row, "maturity_years"),
            payment_frequency=_to_int(row, "float_frequency", 4),
            volatility=_to_float(row, "volatility", 0.20),
            is_cap=_to_bool(row, "is_cap", True),
        )
    if product_type == "ccs":
        return CrossCurrencySwap(
            domestic_notional=_to_float(row, "notional"),
            foreign_notional=_to_float(row, "notional_foreign"),
            maturity_years=_to_float(row, "maturity_years"),
            domestic_frequency=_to_int(row, "fixed_frequency", 2),
            foreign_frequency=_to_int(row, "float_frequency", 2),
            domestic_fixed_rate=_to_opt_float(row, "coupon_or_fixed_rate"),
            foreign_fixed_rate=_to_opt_float(row, "foreign_fixed_rate"),
            domestic_spread=_to_float(row, "spread", 0.0),
            foreign_spread=_to_float(row, "foreign_spread", 0.0),
            pay_domestic_receive_foreign=_to_bool(row, "pay_domestic_receive_foreign", True),
            exchange_notionals=_to_bool(row, "exchange_notionals", True),
            mark_to_market=_to_bool(row, "mark_to_market", False),
        )
    raise ValueError(f"Unsupported product_type: {product_type}")


def _to_str(row: dict[str, str], key: str, default: str = "") -> str:
    value = row.get(key, "")
    return default if value is None or str(value).strip() == "" else str(value).strip()


def _to_float(row: dict[str, str], key: str, default: float | None = None) -> float:
    value = row.get(key, "")
    if value is None or str(value).strip() == "":
        if default is None:
            raise ValueError(f"Missing required float field: {key}")
        return default
    return float(value)


def _to_opt_float(row: dict[str, str], key: str) -> float | None:
    value = row.get(key, "")
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def _to_int(row: dict[str, str], key: str, default: int | None = None) -> int:
    value = row.get(key, "")
    if value is None or str(value).strip() == "":
        if default is None:
            raise ValueError(f"Missing required int field: {key}")
        return default
    return int(float(value))


def _to_bool(row: dict[str, str], key: str, default: bool = False) -> bool:
    value = row.get(key, "")
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y"}
