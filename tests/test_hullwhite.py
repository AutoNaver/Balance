import numpy as np
import pytest

from models.curve import DeterministicZeroCurve
from models.hullwhite import HullWhiteModel


def test_hull_white_simulation_shape_and_seed_stability():
    curve = DeterministicZeroCurve(
        tenors=np.array([0.5, 1.0, 2.0, 5.0]),
        zero_rates=np.array([0.02, 0.021, 0.022, 0.024]),
    )
    model = HullWhiteModel(a=0.1, sigma=0.01, initial_curve=curve)

    paths1 = model.simulate_short_rate_paths(horizon_years=1.0, n_steps=12, n_paths=5, seed=123)
    paths2 = model.simulate_short_rate_paths(horizon_years=1.0, n_steps=12, n_paths=5, seed=123)

    assert paths1.shape == (5, 13)
    assert np.allclose(paths1, paths2)


def test_hull_white_zcb_price_at_maturity_is_one():
    curve = DeterministicZeroCurve(
        tenors=np.array([0.5, 1.0, 2.0, 5.0]),
        zero_rates=np.array([0.02, 0.021, 0.022, 0.024]),
    )
    model = HullWhiteModel(a=0.1, sigma=0.01, initial_curve=curve)
    assert model.zcb_price(2.0, 2.0) == pytest.approx(1.0)
