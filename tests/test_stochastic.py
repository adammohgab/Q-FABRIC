import pytest

from qfabric.models import QuantumLink
from qfabric.stochastic import estimate_parallel_link_generation


def link(source: str, probability: float, duration: float = 1.0) -> QuantumLink:
    return QuantumLink(
        source=source,
        target=f"{source}-b",
        fidelity=0.9,
        generation_probability=probability,
        attempt_duration=duration,
        pair_coherence_time=10.0,
        memory_slots=100,
    )


def test_probability_one_has_deterministic_completion_time():
    result = estimate_parallel_link_generation(
        [link("a", 1.0, 2.0), link("b", 1.0, 3.0)],
        requested_pairs=4,
        trials=100,
    )
    assert result.mean == 12.0
    assert result.p50 == result.p95 == result.p99 == 12.0


def test_single_link_mean_matches_geometric_expectation_within_mc_error():
    result = estimate_parallel_link_generation(
        [link("a", 0.5, 2.0)], trials=100_000, seed=42
    )
    assert result.mean == pytest.approx(4.0, abs=0.04)
    assert result.p50 in (2.0, 4.0)
    assert result.p95 >= result.p50
    assert result.p99 >= result.p95


def test_seed_reproduces_result_and_multiple_pairs_are_counted():
    links = [link("a", 0.7), link("b", 0.4, 0.5)]
    first = estimate_parallel_link_generation(links, 3, 500, 7)
    second = estimate_parallel_link_generation(links, 3, 500, 7)
    assert first == second
    assert first.requested_pairs == 3


def test_invalid_inputs_are_rejected():
    with pytest.raises(ValueError):
        estimate_parallel_link_generation([], trials=10)
    with pytest.raises(ValueError):
        estimate_parallel_link_generation([link("a", 0.5)], requested_pairs=0)
    with pytest.raises(ValueError):
        estimate_parallel_link_generation([link("a", 0.5)], trials=0)


@pytest.mark.parametrize("value", [1.5, True, 0, -1])
def test_invalid_requested_pairs_are_rejected(value):
    with pytest.raises(ValueError):
        estimate_parallel_link_generation(
            [link("a", 0.5)], requested_pairs=value
        )


@pytest.mark.parametrize("value", [1.5, True, 0, -1])
def test_invalid_trials_are_rejected(value):
    with pytest.raises(ValueError):
        estimate_parallel_link_generation(
            [link("a", 0.5)], trials=value
        )


@pytest.mark.parametrize("value", [1.5, True, "42", None])
def test_invalid_seed_is_rejected(value):
    with pytest.raises(ValueError):
        estimate_parallel_link_generation(
            [link("a", 0.5)], seed=value
        )


def test_invalid_link_items_are_rejected():
    with pytest.raises(ValueError):
        estimate_parallel_link_generation(["not-a-link"], trials=10)


def test_probability_one_supports_multiple_requested_pairs():
    result = estimate_parallel_link_generation(
        [link("a", 1.0, 2.5)],
        requested_pairs=3,
        trials=20,
    )
    assert result.mean == 7.5
    assert result.p50 == result.p95 == result.p99 == 7.5
