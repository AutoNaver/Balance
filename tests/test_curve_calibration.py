import pytest

from models.calibration import DepositQuote, SwapQuote, bootstrap_zero_curve


def test_bootstrap_flat_curve_reprices_deposits_and_swaps():
    r = 0.02
    deposits = [DepositQuote(tenor_years=1.0, simple_rate=r)]
    swaps = [SwapQuote(maturity_years=2.0, par_rate=r), SwapQuote(maturity_years=3.0, par_rate=r)]

    curve, diag = bootstrap_zero_curve(deposits, swaps, interpolation="linear_zero")

    assert len(curve.tenors) == 3
    assert diag.monotonic_discount_factors
    assert diag.non_negative_forwards
    assert diag.max_abs_fit_error < 5e-4


def test_bootstrap_rejects_missing_grid_for_swap_bootstrap():
    deposits = [DepositQuote(tenor_years=0.5, simple_rate=0.02)]
    swaps = [SwapQuote(maturity_years=2.0, par_rate=0.02, fixed_frequency=2)]

    with pytest.raises(ValueError, match="missing earlier discount factor"):
        bootstrap_zero_curve(deposits, swaps)


def test_bootstrap_interpolation_policy_validation():
    deposits = [DepositQuote(tenor_years=1.0, simple_rate=0.02)]
    swaps = []
    with pytest.raises(ValueError, match="interpolation must be"):
        bootstrap_zero_curve(deposits, swaps, interpolation="cubic")
