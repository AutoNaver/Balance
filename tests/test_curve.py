import numpy as np
import pytest

from models.curve import DeterministicZeroCurve


def test_discount_factor_is_one_at_zero():
    curve = DeterministicZeroCurve(
        tenors=np.array([1.0, 5.0]),
        zero_rates=np.array([0.02, 0.03]),
    )
    assert curve.discount_factor(0.0) == pytest.approx(1.0)


def test_discount_factor_decreases_with_time_for_positive_rates():
    curve = DeterministicZeroCurve(
        tenors=np.array([1.0, 5.0]),
        zero_rates=np.array([0.02, 0.03]),
    )
    assert curve.discount_factor(5.0) < curve.discount_factor(1.0)
