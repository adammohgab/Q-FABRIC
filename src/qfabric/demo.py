from __future__ import annotations

import json
from dataclasses import asdict

from .certificate import issue_prediction_certificate
from .models import EntanglementRequest, NetworkState, QuantumLink, QuantumNode
from .planner import schedule_requests


def build_demo_state() -> NetworkState:
    nodes = {
        "A": QuantumNode("A", 8),
        "B": QuantumNode("B", 8),
        "C": QuantumNode("C", 8),
        "D": QuantumNode("D", 8),
    }
    links = [
        QuantumLink("A", "B", 0.94, 0.90, 1.0, 20.0, 8, 0.1),
        QuantumLink("B", "D", 0.94, 0.90, 1.0, 20.0, 8, 0.1),
        QuantumLink("A", "C", 0.97, 0.75, 1.2, 30.0, 8, 0.2),
        QuantumLink("C", "D", 0.97, 0.75, 1.2, 30.0, 8, 0.2),
        QuantumLink("B", "C", 0.96, 0.85, 1.0, 25.0, 4, 0.1),
    ]
    return NetworkState(nodes, links)


def main() -> None:
    state = build_demo_state()
    requests = [
        EntanglementRequest("R1", "user-1", "A", "D", 0.80, 5.0, 1, 2),
        EntanglementRequest("R2", "user-2", "A", "D", 0.82, 6.0, 1, 1),
        EntanglementRequest("R3", "user-1", "B", "C", 0.85, 3.0, 1, 0),
    ]
    allocations = schedule_requests(requests, state)
    by_id = {request.request_id: request for request in requests}
    output = []
    for allocation in allocations:
        cert = issue_prediction_certificate(by_id[allocation.request_id], allocation)
        output.append({"allocation": asdict(allocation), "certificate": asdict(cert)})
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
