from pathlib import Path

import numpy as np

from engine.scenario import Scenario
from engine.valuation import ValuationEngine
from io_layer.loaders import load_mixed_portfolio_csv
from models.curve import DeterministicZeroCurve
from models.market import DeterministicFXCurve
from products.derivatives import FXForward


def test_loader_supports_corporate_bond(tmp_path: Path):
    csv_content = """product_type,id,notional,coupon_or_fixed_rate,maturity_years,coupon_type,payment_frequency,day_count,amortization_mode,annual_cpr\ncorporate_bond,CB1,100000,0.04,2,fixed,semi_annual,30/360,bullet,0.02\n"""
    path = tmp_path / "portfolio.csv"
    path.write_text(csv_content, encoding="utf-8")

    portfolio = load_mixed_portfolio_csv(path)
    assert len(portfolio) == 1
    assert portfolio[0].__class__.__name__ == "CorporateBond"


def test_loader_supports_integrated_german_mortgage(tmp_path: Path):
    csv_content = (
        "product_type,notional,coupon_or_fixed_rate,maturity_years,repayment_type,payment_frequency,day_count,start_month,use_behavioural_prepayment\n"
        "integrated_german_fixed_rate_mortgage,250000,0.035,10,annuity,monthly,30/360,1,true\n"
    )
    path = tmp_path / "portfolio.csv"
    path.write_text(csv_content, encoding="utf-8")

    portfolio = load_mixed_portfolio_csv(path)
    assert len(portfolio) == 1
    assert portfolio[0].__class__.__name__ == "IntegratedGermanFixedRateMortgageLoan"


def test_engine_supports_scenario_extra_data_for_fx_products():
    curve = DeterministicZeroCurve(
        tenors=np.array([0.5, 1.0, 2.0]),
        zero_rates=np.array([0.02, 0.02, 0.02]),
    )
    fx_curve = DeterministicFXCurve(
        tenors=np.array([0.5, 1.0, 2.0]),
        fx_forwards=np.array([1.10, 1.12, 1.14]),
    )
    product = FXForward(notional_foreign=1000000.0, strike=1.11, maturity_years=1.0)

    scenario = Scenario(name="base", model=curve, data={"fx_curve": fx_curve})
    result = ValuationEngine([product]).value([scenario])
    assert len(result.scenario_pv) == 1
