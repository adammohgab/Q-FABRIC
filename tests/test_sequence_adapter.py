import pytest

from qfabric.sequence_adapter import _load_sequence


def test_sequence_adapter_fails_clearly_when_dependency_missing(monkeypatch):
    import qfabric.sequence_adapter as adapter

    def missing(_name):
        raise ImportError("not installed")

    monkeypatch.setattr(adapter, "import_module", missing)
    with pytest.raises(RuntimeError, match="SeQUeNCe is not installed"):
        _load_sequence()


@pytest.mark.parametrize("seed", [True, 1.5, "7", None])
def test_sequence_adapter_rejects_invalid_seed(seed):
    from qfabric.sequence_adapter import run_elementary_link_smoke_test

    with pytest.raises(ValueError, match="seed"):
        run_elementary_link_smoke_test(seed=seed)


@pytest.mark.parametrize(
    "distance",
    [0, -1, float("nan"), float("inf"), -float("inf"), True, "1000"],
)
def test_sequence_adapter_rejects_invalid_distance(distance):
    from qfabric.sequence_adapter import run_elementary_link_smoke_test

    with pytest.raises(ValueError, match="distance_m"):
        run_elementary_link_smoke_test(distance_m=distance)


def test_sequence_result_converts_to_planner_network_state():
    from qfabric.sequence_adapter import (
        SequenceSwappingResult,
        network_state_from_sequence_result,
    )

    result = SequenceSwappingResult(
        sequence_version="1.3.1",
        simulated_time=2_822_600_010,
        left_link_generated=True,
        right_link_generated=True,
        swapping_succeeded=True,
        endpoint_a_fidelity=0.686375,
        endpoint_c_fidelity=0.686375,
        end_to_end_entangled=True,
        left_link_attempts=2,
        right_link_attempts=4,
        left_link_simulated_time=907_525_010,
        right_link_simulated_time=1_815_075_000,
        pre_swap_endpoint_a_fidelity=0.85,
        pre_swap_endpoint_c_fidelity=0.85,
    )

    state = network_state_from_sequence_result(
        result,
        pair_coherence_time_ps=1_000_000_000,
        memory_slots=2,
    )

    assert set(state.nodes) == {"A", "B", "C"}
    assert state.nodes["A"].memory_slots == 2
    assert state.nodes["B"].memory_slots == 4
    assert state.nodes["C"].memory_slots == 2
    assert len(state.links) == 2

    left, right = state.links
    assert (left.source, left.target) == ("A", "B")
    assert (right.source, right.target) == ("B", "C")
    assert left.fidelity == right.fidelity == 0.85
    assert left.generation_probability == 0.5
    assert right.generation_probability == 0.25
    assert left.expected_generation_time == 907_525_010
    assert right.expected_generation_time == 1_815_075_000


def test_sequence_result_conversion_rejects_failed_swapping():
    from dataclasses import replace
    from qfabric.sequence_adapter import (
        SequenceSwappingResult,
        network_state_from_sequence_result,
    )

    result = SequenceSwappingResult(
        "1.3.1", 100, True, True, False,
        0.5, 0.5, False, 1, 1, 50, 50, 0.85, 0.85,
    )

    with pytest.raises(ValueError, match="swapping"):
        network_state_from_sequence_result(result, 1_000_000)


@pytest.mark.parametrize("coherence", [0, -1, float("nan"), float("inf"), True])
def test_sequence_result_conversion_rejects_invalid_coherence(coherence):
    from qfabric.sequence_adapter import (
        SequenceSwappingResult,
        network_state_from_sequence_result,
    )

    result = SequenceSwappingResult(
        "1.3.1", 100, True, True, True,
        0.8, 0.8, True, 1, 1, 50, 50, 0.85, 0.85,
    )

    with pytest.raises(ValueError, match="pair_coherence_time_ps"):
        network_state_from_sequence_result(result, coherence)


def test_bbpssw_purification_smoke_succeeds():
    from qfabric.sequence_adapter import run_bbpssw_purification_smoke_test

    result = run_bbpssw_purification_smoke_test(seed=17)

    assert result.sequence_version == "1.3.1"
    assert result.purification_succeeded is True
    assert result.kept_pair_linked is True
    assert result.input_fidelity == pytest.approx(0.85)
    assert result.output_fidelity_a == pytest.approx(0.8841463414634146)
    assert result.output_fidelity_b == pytest.approx(0.8841463414634146)
    assert result.measurement_a == result.measurement_b
    assert result.left_link_attempts > 0
    assert result.right_link_attempts > 0
