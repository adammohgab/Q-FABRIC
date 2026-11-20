from qfabric.models import EntanglementRequest, NetworkState, QuantumLink, QuantumNode
from qfabric.planner import enumerate_paths, estimate_path, schedule_requests


def state():
    nodes = {name: QuantumNode(name, 10) for name in "ABCD"}
    links = [
        QuantumLink("A", "B", 0.98, 1.0, 1.0, 100.0, 10),
        QuantumLink("B", "D", 0.98, 1.0, 1.0, 100.0, 10),
        QuantumLink("A", "C", 0.95, 1.0, 1.0, 100.0, 10),
        QuantumLink("C", "D", 0.95, 1.0, 1.0, 100.0, 10),
    ]
    return NetworkState(nodes, links)


def test_path_enumeration_returns_two_routes():
    paths = enumerate_paths(state(), "A", "D")
    assert paths == [("A", "B", "D"), ("A", "C", "D")]


def test_estimator_detects_tight_deadline():
    req = EntanglementRequest("r", "u", "A", "D", 0.7, 0.99)
    estimate = estimate_path(req, ("A", "B", "D"), state())
    assert not estimate.feasible
    assert "deadline_infeasible" in estimate.rejection_reasons


def test_scheduler_accepts_feasible_request():
    req = EntanglementRequest("r", "u", "A", "D", 0.7, 5.0)
    result = schedule_requests([req], state())
    assert result[0].accepted
    assert result[0].path is not None


def test_scheduler_rejects_unreachable_request():
    req = EntanglementRequest("r", "u", "A", "D", 0.7, 5.0)
    s = state()
    s.links = [s.links[0]]
    result = schedule_requests([req], s)
    assert not result[0].accepted
    assert result[0].rejection_reasons == ("no_path",)


def test_scheduler_must_not_overbook_after_rounding():
    nodes = {"A": QuantumNode("A", 10), "B": QuantumNode("B", 10)}
    links = [QuantumLink("A", "B", 0.9, 1.0, 1.0, 100.0, 5)]
    network = NetworkState(nodes, links)
    request = EntanglementRequest("rounding", "u", "A", "B", 0.92, 10.0, 2)
    result = schedule_requests([request], network)
    assert not result[0].accepted
    assert network.link_reserved == {}


def test_purification_cost_is_included_in_completion_time():
    nodes = {"A": QuantumNode("A", 20), "B": QuantumNode("B", 20)}
    links = [QuantumLink("A", "B", 0.8, 1.0, 1.0, 1000.0, 20)]
    network = NetworkState(nodes, links)
    request = EntanglementRequest("purification-cost", "u", "A", "B", 0.85, 100.0)
    estimate = estimate_path(request, ("A", "B"), network, max_purification_rounds=2)

    assert estimate.feasible
    assert estimate.purification_rounds > 0
    assert estimate.expected_raw_pairs_per_delivered_pair > 1.0
    assert estimate.expected_completion_time > 1.0


def test_purification_cost_can_make_deadline_infeasible():
    nodes = {"A": QuantumNode("A", 20), "B": QuantumNode("B", 20)}
    links = [QuantumLink("A", "B", 0.8, 1.0, 1.0, 1000.0, 20)]
    network = NetworkState(nodes, links)
    request = EntanglementRequest("purification-deadline", "u", "A", "B", 0.85, 2.0)
    estimate = estimate_path(request, ("A", "B"), network, max_purification_rounds=2)

    assert not estimate.feasible
    assert "deadline_infeasible" in estimate.rejection_reasons
