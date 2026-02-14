import numpy as np

from engine.scenario import DeterministicStressScenarioGenerator
from models.curve import DeterministicZeroCurve


def test_stress_scenarios_include_parallel_and_twist():
    curve = DeterministicZeroCurve(
        tenors=np.array([1.0, 3.0, 5.0, 10.0]),
        zero_rates=np.array([0.02, 0.021, 0.022, 0.024]),
    )
    gen = DeterministicStressScenarioGenerator(
        base_curve=curve,
        parallel_shifts_bps=[-50, 0, 50],
        twist_shifts_bps=[-25, 25],
        twist_pivot_year=5.0,
    )
    scenarios = gen.generate()
    assert len(scenarios) == 5
    names = [s.name for s in scenarios]
    assert "parallel_shift_+0bps" in names
    assert any(name.startswith("twist_") for name in names)


def test_positive_twist_steepens_long_end_vs_short_end():
    curve = DeterministicZeroCurve(
        tenors=np.array([1.0, 3.0, 5.0, 10.0]),
        zero_rates=np.array([0.02, 0.021, 0.022, 0.024]),
    )
    gen = DeterministicStressScenarioGenerator(
        base_curve=curve,
        parallel_shifts_bps=[],
        twist_shifts_bps=[50],
        twist_pivot_year=5.0,
    )
    scenario = gen.generate()[0]
    long_rate = scenario.model.short_rate(10.0)
    short_rate = scenario.model.short_rate(1.0)
    assert long_rate - short_rate > (curve.short_rate(10.0) - curve.short_rate(1.0))
