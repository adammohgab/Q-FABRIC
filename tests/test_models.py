import math
import pytest

from qfabric.models import (
    EntanglementRequest,
    NetworkState,
    QuantumLink,
    QuantumNode,
)


def make_link():
    return QuantumLink("A", "B", 0.9, 0.5, 1.0, 10.0, 5)


def make_state(**kwargs):
    return NetworkState(
        {"A": QuantumNode("A", 5), "B": QuantumNode("B", 5)},
        [make_link()],
        **kwargs,
    )


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_link_rejects_non_finite_values(value):
    with pytest.raises(ValueError):
        QuantumLink("A", "B", value, 0.5, 1.0, 10.0, 5)


def test_node_rejects_boolean_capacity():
    with pytest.raises(ValueError):
        QuantumNode("A", True)


def test_request_rejects_non_finite_deadline():
    with pytest.raises(ValueError):
        EntanglementRequest("r", "u", "A", "B", 0.8, math.inf)


def test_request_rejects_boolean_pair_count():
    with pytest.raises(ValueError):
        EntanglementRequest("r", "u", "A", "B", 0.8, 10, requested_pairs=True)


def test_network_rejects_mismatched_node_key():
    with pytest.raises(ValueError):
        NetworkState({"X": QuantumNode("A", 5)}, [])


def test_network_rejects_duplicate_undirected_links():
    with pytest.raises(ValueError, match="duplicate physical link"):
        NetworkState(
            {"A": QuantumNode("A", 5), "B": QuantumNode("B", 5)},
            [make_link(), QuantumLink("B", "A", 0.9, 0.5, 1.0, 10.0, 5)],
        )


def test_network_rejects_node_capacity_overbooking():
    with pytest.raises(ValueError, match="node memory capacity exceeded"):
        make_state(node_reserved={"A": 6})


def test_network_rejects_link_capacity_overbooking_across_directions():
    with pytest.raises(ValueError, match="link memory capacity exceeded"):
        make_state(link_reserved={("A", "B"): 3, ("B", "A"): 3})


def test_network_accepts_valid_directional_reservations():
    state = make_state(
        node_reserved={"A": 2},
        link_reserved={("A", "B"): 2, ("B", "A"): 3},
    )
    assert state.node_reserved["A"] == 2
