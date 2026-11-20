from __future__ import annotations

from collections import Counter
from typing import Iterable

from .models import EntanglementRequest, NetworkState
from .planner import (
    Allocation,
    enumerate_paths,
    estimate_path,
    schedule_requests,
    _reserve,
)


def _clone_state(state: NetworkState) -> NetworkState:
    from copy import deepcopy
    return deepcopy(state)


def _greedy_with_order(requests, state, ordering):
    ordered = sorted(requests, key=ordering)
    allocations = []

    for request in ordered:
        paths = enumerate_paths(
            state, request.source, request.target
        )
        estimates = [
            estimate_path(request, path, state)
            for path in paths
        ]
        feasible = [e for e in estimates if e.feasible]

        if not feasible:
            reasons = tuple(sorted({
                reason
                for estimate in estimates
                for reason in estimate.rejection_reasons
            }))
            if not paths:
                reasons = ("no_path",)

            allocations.append(
                Allocation(
                    request.request_id, request.user_id, False,
                    None, None, None, None, reasons
                )
            )
            continue

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


def _metrics(allocations: list[Allocation]) -> dict:
    total = len(allocations)
    accepted = [a for a in allocations if a.accepted]
    rejected = [a for a in allocations if not a.accepted]

    return {
        "total_requests": total,
        "accepted_requests": len(accepted),
        "rejected_requests": len(rejected),
        "acceptance_rate": len(accepted) / total if total else 0.0,
        "mean_predicted_fidelity": (
            sum(a.predicted_fidelity for a in accepted) / len(accepted)
            if accepted else 0.0
        ),
        "mean_completion_time": (
            sum(a.expected_completion_time for a in accepted) / len(accepted)
            if accepted else 0.0
        ),
        "rejection_reasons": dict(
            Counter(
                reason
                for allocation in rejected
                for reason in allocation.rejection_reasons
            )
        ),
    }


def run_benchmark(
    requests: Iterable[EntanglementRequest],
    state: NetworkState,
) -> dict:
    requests = list(requests)

    policies = {
        "qfabric": lambda rs, st: schedule_requests(rs, st),
        "edf": lambda rs, st: _greedy_with_order(
            rs, st,
            lambda r: (r.deadline, r.arrival_time, r.request_id),
        ),
        "priority_first": lambda rs, st: _greedy_with_order(
            rs, st,
            lambda r: (-r.priority, r.deadline, r.arrival_time, r.request_id),
        ),
        "shortest_slack": lambda rs, st: _greedy_with_order(
            rs, st,
            lambda r: (r.deadline - r.arrival_time, r.request_id),
        ),
    }

    results = {}
    for name, policy in policies.items():
        allocations = policy(requests, _clone_state(state))
        results[name] = _metrics(allocations)

    return {
        "benchmark_version": "0.1.0",
        "policies": results,
    }



def main() -> None:
    import json
    from .demo import build_demo_state
    from .models import EntanglementRequest

    state = build_demo_state()
    requests = [
        EntanglementRequest("R1", "user-1", "A", "D", 0.80, 5.0, 1, 2),
        EntanglementRequest("R2", "user-2", "A", "D", 0.82, 6.0, 1, 1),
        EntanglementRequest("R3", "user-1", "B", "C", 0.85, 3.0, 1, 0),
    ]

    print(json.dumps(run_benchmark(requests, state), indent=2))


if __name__ == "__main__":
    main()
