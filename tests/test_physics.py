import math
import pytest

from qfabric.physics import (
    bbpssw_step,
    bbpssw_rounds,
    entanglement_swapping_fidelity,
    pair_coherence_time,
    werner_fidelity_after_wait,
)


def test_memory_decay_starts_at_initial_fidelity():
    assert werner_fidelity_after_wait(0.9, 0.0, 10.0) == pytest.approx(0.9)


def test_memory_decay_approaches_mixed_state_limit():
    assert werner_fidelity_after_wait(0.9, 1e6, 10.0) == pytest.approx(0.25)


def test_pair_coherence_for_equal_memories():
    assert pair_coherence_time(10.0, 10.0) == pytest.approx(5.0)


def test_swapping_two_identical_pairs_reduces_visibility():
    result = entanglement_swapping_fidelity([0.9, 0.9])
    assert 0.25 < result < 0.9


def test_bbpssw_improves_high_fidelity_werner_pair():
    p, output = bbpssw_step(0.9)
    assert 0 < p <= 1
    assert output > 0.9


def test_bbpssw_raw_pair_factor_grows():
    _, _, factor = bbpssw_rounds(0.9, 2)
    assert factor > 4


def test_invalid_wait_rejected():
    with pytest.raises(ValueError):
        werner_fidelity_after_wait(0.9, -1, 10)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_physics_rejects_non_finite_fidelity(value):
    with pytest.raises(ValueError):
        werner_fidelity_after_wait(value, 0.0, 10.0)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_physics_rejects_non_finite_wait(value):
    with pytest.raises(ValueError):
        werner_fidelity_after_wait(0.9, value, 10.0)


def test_visibility_rejects_out_of_range_values():
    from qfabric.physics import fidelity_from_visibility
    with pytest.raises(ValueError):
        fidelity_from_visibility(1.1)


def test_bbpssw_rounds_rejects_non_integer_rounds():
    with pytest.raises(ValueError):
        bbpssw_rounds(0.9, 1.5)
