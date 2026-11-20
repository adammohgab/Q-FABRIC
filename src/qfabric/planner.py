from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

from .models import EntanglementRequest, NetworkState, QuantumLink
from .physics import (
    bbpssw_rounds,
    entanglement_swapping_fidelity,
    werner_fidelity_after_wait,
)


@dataclass(frozen=True)
class PathEstimate:
    nodes: tuple[str, ...]
    expected_completion_time: float
    predicted_fidelity: float
    purification_rounds: int
    expected_raw_pairs_per_delivered_pair: float
    feasible: bool
    rejection_reasons: tuple[str, ...]


@dataclass(frozen=True)
class Allocation:
    request_id: str
    user_id: str
    accepted: bool
    path: tuple[str, ...] | None
    predicted_fidelity: float | None
    expected_completion_time: float | None
    purification_rounds: int | None
    rejection_reasons: tuple[str, ...]


def enumerate_paths(state: NetworkState, source: str, target: str, max_hops: int = 8) -> list[tuple[str, ...]]:
    if source not in state.nodes or target not in state.nodes:
        return []
    adjacency: dict[str, list[str]] = {node: [] for node in state.nodes}
    for link in state.links:
        adjacency[link.source].append(link.target)
        adjacency[link.target].append(link.source)
    paths: list[tuple[str, ...]] = []

    def walk(current: str, path: list[str]) -> None:
        if len(path) - 1 > max_hops:
            return
        if current == target:
            paths.append(tuple(path))
            return
        for neighbor in sorted(adjacency[current]):
            if neighbor not in path:
                walk(neighbor, path + [neighbor])

    walk(source, [source])
    return sorted(paths, key=lambda p: (len(p), p))


def estimate_path(
    request: EntanglementRequest,
    path: tuple[str, ...],
    state: NetworkState,
    max_purification_rounds: int = 2,
) -> PathEstimate:
    link_map = state.link_map()
    links: list[QuantumLink] = []
    for a, b in zip(path, path[1:]):
        link = link_map.get((a, b))
        if link is None:
            return _rejected(path, ("missing_link",))
        links.append(link)

    # First-order expected-time approximation: parallel link generation,
    # followed by classical swapping coordination at intermediate nodes.
    link_generation_times = [link.expected_generation_time for link in links]
    generation_finish = max(link_generation_times, default=0.0)
    swapping_latency = sum(link.classical_latency for link in links)
    reasons: list[str] = []

    # Links finishing earlier wait in memory until the slowest link is ready.
    aged_fidelities = [
        werner_fidelity_after_wait(
            link.fidelity,
            generation_finish - link_generation_times[i],
            link.pair_coherence_time,
        )
        for i, link in enumerate(links)
    ]

    best: tuple[float, int, float, float] | None = None
    for rounds in range(max_purification_rounds + 1):
        purified: list[float] = []
        raw_factor = 1.0
        purification_generation_time = 0.0

        for index, fidelity in enumerate(aged_fidelities):
            output_fidelity, _success, factor = bbpssw_rounds(fidelity, rounds)
            purified.append(output_fidelity)
            raw_factor = max(raw_factor, factor)
            purification_generation_time = max(
                purification_generation_time,
                link_generation_times[index] * factor,
            )

        end_to_end = entanglement_swapping_fidelity(purified)
        candidate = (
            end_to_end,
            rounds,
            raw_factor,
            purification_generation_time,
        )
        if best is None or candidate[0] > best[0]:
            best = candidate
        if end_to_end >= request.required_fidelity:
            best = candidate
            break

    assert best is not None
    predicted_fidelity, rounds, raw_factor, generation_time = best
    completion = request.arrival_time + generation_time + swapping_latency

    if completion > request.deadline:
        reasons.append("deadline_infeasible")
    if predicted_fidelity < request.required_fidelity:
        reasons.append("fidelity_infeasible")

    # Check per-link memory and intermediate-node memory for requested pairs.
    for link in links:
        reserved = state.link_reserved.get((link.source, link.target), 0)
        reserved += state.link_reserved.get((link.target, link.source), 0)
        needed = request.requested_pairs * math.ceil(raw_factor)
        if reserved + needed > link.memory_slots:
            reasons.append(f"link_memory_exhausted:{link.source}-{link.target}")
    for node_id in path:
        node = state.nodes[node_id]
        if state.node_reserved.get(node_id, 0) + request.requested_pairs > node.memory_slots:
            reasons.append(f"node_memory_exhausted:{node_id}")

    return PathEstimate(
        nodes=path,
        expected_completion_time=completion,
        predicted_fidelity=predicted_fidelity,
        purification_rounds=rounds,
        expected_raw_pairs_per_delivered_pair=raw_factor,
        feasible=not reasons,
        rejection_reasons=tuple(reasons),
    )


def schedule_requests(
    requests: Iterable[EntanglementRequest],
    state: NetworkState,
    max_hops: int = 8,
    max_purification_rounds: int = 2,
) -> list[Allocation]:
    """Feasibility-first EDF-style greedy baseline.

    This is not a fairness optimizer or a globally optimal scheduler. It sorts
    requests by slack, priority, arrival, and ID, then reserves resources greedily.
    Fairness is measured after execution and will be handled by a separate
    optimizer once the service-accounting definition is validated.
    """
    ordered = sorted(
        requests,
        key=lambda r: (r.deadline - r.arrival_time, -r.priority, r.arrival_time, r.request_id),
    )
    allocations: list[Allocation] = []
    for request in ordered:
        paths = enumerate_paths(state, request.source, request.target, max_hops)
        estimates = [
            estimate_path(request, path, state, max_purification_rounds)
            for path in paths
        ]
        feasible = [estimate for estimate in estimates if estimate.feasible]
        if not feasible:
            reasons = tuple(sorted({reason for e in estimates for reason in e.rejection_reasons}))
            if not paths:
                reasons = ("no_path",)
            allocations.append(Allocation(request.request_id, request.user_id, False, None, None, None, None, reasons))
            continue

        # Fairness is a tie-breaker only in this baseline. A later optimizer
        # must replace this heuristic and establish a formal objective.
        chosen = min(
            feasible,
            key=lambda e: (
                e.expected_raw_pairs_per_delivered_pair,
                e.expected_completion_time,
                len(e.nodes),
                e.nodes,
            ),
        )
        allocations.append(
            Allocation(
                request.request_id,
                request.user_id,
                True,
                chosen.nodes,
                chosen.predicted_fidelity,
                chosen.expected_completion_time,
                chosen.purification_rounds,
                (),
            )
        )
        _reserve(chosen, request, state)
    return allocations


def _reserve(estimate: PathEstimate, request: EntanglementRequest, state: NetworkState) -> None:
    # Conservative integer reservation: ceil expected raw-pair factor.
    slots = request.requested_pairs * math.ceil(estimate.expected_raw_pairs_per_delivered_pair)
    for a, b in zip(estimate.nodes, estimate.nodes[1:]):
        key = (a, b)
        state.link_reserved[key] = state.link_reserved.get(key, 0) + slots
    for node_id in estimate.nodes:
        state.node_reserved[node_id] = state.node_reserved.get(node_id, 0) + request.requested_pairs


def _rejected(path: tuple[str, ...], reasons: tuple[str, ...]) -> PathEstimate:
    return PathEstimate(path, float("inf"), 0.25, 0, 1.0, False, reasons)
