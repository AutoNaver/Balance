from pathlib import Path

import numpy as np
import pytest

from io_layer.loaders import load_csa_configs_csv, load_product_netting_set_map_csv
from models.curve import DeterministicZeroCurve


def _curve(rate: float) -> DeterministicZeroCurve:
    return DeterministicZeroCurve(
        tenors=np.array([0.5, 1.0, 2.0, 5.0]),
        zero_rates=np.array([rate, rate, rate, rate]),
    )


def test_load_product_netting_set_map_csv(tmp_path: Path):
    csv_content = """product_index,netting_set_id\n0,ns_usd\n1,ns_eur\n"""
    path = tmp_path / "product_netting_map.csv"
    path.write_text(csv_content, encoding="utf-8")

    mapping = load_product_netting_set_map_csv(path)
    assert mapping == {0: "ns_usd", 1: "ns_eur"}


def test_load_csa_configs_csv_with_discount_model_lookup(tmp_path: Path):
    csv_content = (
        "netting_set_id,discount_model_key,collateral_rate,threshold,minimum_transfer_amount\n"
        "ns_usd,ois_usd,0.01,1000,100\n"
    )
    path = tmp_path / "csa_configs.csv"
    path.write_text(csv_content, encoding="utf-8")

    configs = load_csa_configs_csv(path, {"ois_usd": _curve(0.01)})

    assert "ns_usd" in configs
    cfg = configs["ns_usd"]
    assert cfg.collateral_rate == pytest.approx(0.01)
    assert cfg.threshold == pytest.approx(1000.0)
    assert cfg.minimum_transfer_amount == pytest.approx(100.0)


def test_load_csa_configs_csv_rejects_unknown_model_key(tmp_path: Path):
    csv_content = """netting_set_id,discount_model_key\nns1,missing_key\n"""
    path = tmp_path / "csa_configs.csv"
    path.write_text(csv_content, encoding="utf-8")

    with pytest.raises(ValueError, match="Unknown discount_model_key"):
        load_csa_configs_csv(path, {})
