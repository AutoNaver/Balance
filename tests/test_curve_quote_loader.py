from pathlib import Path

import pytest

from models.calibration import load_curve_quotes_csv, bootstrap_zero_curve


def test_load_curve_quotes_csv_and_bootstrap(tmp_path: Path):
    p = tmp_path / "quotes.csv"
    p.write_text(
        "instrument_type,tenor_years,rate,fixed_frequency\n"
        "deposit,1.0,0.02,\n"
        "swap,2.0,0.02,1\n"
        "swap,3.0,0.02,1\n",
        encoding="utf-8",
    )
    deposits, swaps = load_curve_quotes_csv(p)
    assert len(deposits) == 1
    assert len(swaps) == 2

    curve, diag = bootstrap_zero_curve(deposits, swaps)
    assert len(curve.tenors) == 3
    assert diag.max_abs_fit_error < 1e-3


def test_load_curve_quotes_csv_rejects_unknown_instrument(tmp_path: Path):
    p = tmp_path / "bad.csv"
    p.write_text(
        "instrument_type,tenor_years,rate,fixed_frequency\n"
        "futures,1.0,0.02,1\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unsupported instrument_type"):
        load_curve_quotes_csv(p)
