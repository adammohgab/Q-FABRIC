from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _integer(value: object, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _identifier(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


@dataclass(frozen=True)
class QuantumNode:
    node_id: str
    memory_slots: int

    def __post_init__(self) -> None:
        _identifier(self.node_id, "node_id")
        _integer(self.memory_slots, "memory_slots")


@dataclass(frozen=True)
class QuantumLink:
    source: str
    target: str
    fidelity: float
    generation_probability: float
    attempt_duration: float
    pair_coherence_time: float
    memory_slots: int
    classical_latency: float = 0.0

    def __post_init__(self) -> None:
        _identifier(self.source, "source")
        _identifier(self.target, "target")
        if self.source == self.target:
            raise ValueError("self-links are not supported")

        fidelity = _finite_number(self.fidelity, "fidelity")
        probability = _finite_number(self.generation_probability, "generation_probability")
        attempt = _finite_number(self.attempt_duration, "attempt_duration")
        coherence = _finite_number(self.pair_coherence_time, "pair_coherence_time")
        latency = _finite_number(self.classical_latency, "classical_latency")

        if not 0.25 <= fidelity <= 1.0:
            raise ValueError("Werner-state fidelity must be in [0.25, 1]")
        if not 0.0 < probability <= 1.0:
            raise ValueError("generation_probability must be in (0, 1]")
        if attempt <= 0 or coherence <= 0:
            raise ValueError("durations must be positive")
        if latency < 0:
            raise ValueError("classical_latency must be non-negative")
        _integer(self.memory_slots, "memory_slots")

    @property
    def expected_generation_time(self) -> float:
        """Expected attempts-to-success time for a geometric trial model."""
        return self.attempt_duration / self.generation_probability


@dataclass(frozen=True)
class EntanglementRequest:
    request_id: str
    user_id: str
    source: str
    target: str
    required_fidelity: float
    deadline: float
    requested_pairs: int = 1
    priority: int = 0
    arrival_time: float = 0.0

    def __post_init__(self) -> None:
        for name in ("request_id", "user_id", "source", "target"):
            _identifier(getattr(self, name), name)
        if self.source == self.target:
            raise ValueError("source and target must differ")

        fidelity = _finite_number(self.required_fidelity, "required_fidelity")
        deadline = _finite_number(self.deadline, "deadline")
        arrival = _finite_number(self.arrival_time, "arrival_time")

        if not 0.25 <= fidelity <= 1.0:
            raise ValueError("required_fidelity must be in [0.25, 1]")
        if deadline < arrival:
            raise ValueError("deadline cannot precede arrival_time")
        if not isinstance(self.priority, int) or isinstance(self.priority, bool):
            raise ValueError("priority must be an integer")
        _integer(self.requested_pairs, "requested_pairs", minimum=1)


@dataclass
class NetworkState:
    nodes: dict[str, QuantumNode]
    links: list[QuantumLink]
    node_reserved: dict[str, int] = field(default_factory=dict)
    link_reserved: dict[tuple[str, str], int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.nodes, dict) or not isinstance(self.links, list):
            raise ValueError("nodes must be a dict and links must be a list")

        for key, node in self.nodes.items():
            if not isinstance(node, QuantumNode) or key != node.node_id:
                raise ValueError("node dictionary keys must match QuantumNode.node_id")

        physical_links: set[frozenset[str]] = set()
        for link in self.links:
            if not isinstance(link, QuantumLink):
                raise ValueError("links must contain QuantumLink instances")
            if link.source not in self.nodes or link.target not in self.nodes:
                raise ValueError(f"link endpoint missing: {link.source}-{link.target}")
            physical_key = frozenset((link.source, link.target))
            if physical_key in physical_links:
                raise ValueError(f"duplicate physical link: {link.source}-{link.target}")
            physical_links.add(physical_key)

        if not isinstance(self.node_reserved, dict):
            raise ValueError("node_reserved must be a dict")
        for node_id, amount in self.node_reserved.items():
            if node_id not in self.nodes:
                raise ValueError(f"reservation references unknown node: {node_id}")
            _integer(amount, "node reservation")
            if amount > self.nodes[node_id].memory_slots:
                raise ValueError(f"node memory capacity exceeded: {node_id}")

        if not isinstance(self.link_reserved, dict):
            raise ValueError("link_reserved must be a dict")
        link_map = self.link_map()
        totals: dict[frozenset[str], int] = {}
        capacities = {
            frozenset((link.source, link.target)): link.memory_slots
            for link in self.links
        }

        for key, amount in self.link_reserved.items():
            if not isinstance(key, tuple) or len(key) != 2:
                raise ValueError("link reservation keys must be (source, target) tuples")
            source, target = key
            if (source, target) not in link_map:
                raise ValueError(f"reservation references unknown link: {key}")
            _integer(amount, "link reservation")
            physical_key = frozenset((source, target))
            totals[physical_key] = totals.get(physical_key, 0) + amount
            if totals[physical_key] > capacities[physical_key]:
                raise ValueError(f"link memory capacity exceeded: {key}")

    def link_map(self) -> Mapping[tuple[str, str], QuantumLink]:
        result: dict[tuple[str, str], QuantumLink] = {}
        for link in self.links:
            result[(link.source, link.target)] = link
            result[(link.target, link.source)] = link
        return result
