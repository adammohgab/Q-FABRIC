"""Optional SeQUeNCe 1.3.1 adapter.

This module intentionally keeps SeQUeNCe imports lazy so the core planner and
unit tests remain usable without the optional simulator dependency.
The smoke test models one heralded Barrett-Kok elementary link. It is an
integration check, not yet a multi-hop Q-FABRIC experiment.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from importlib import import_module, metadata
from typing import Any

from qfabric.models import NetworkState, QuantumLink, QuantumNode


SUPPORTED_SEQUENCE_VERSION = "1.3.1"


@dataclass(frozen=True)
class SequenceSmokeResult:
    sequence_version: str
    simulated_time: int
    entangled_memory_updates: int
    raw_memory_updates: int
    endpoint_a_fidelity: float
    endpoint_b_fidelity: float
    entangled_memory_linked: bool


def _load_sequence() -> tuple[Any, str]:
    try:
        sq = import_module("sequence")
    except ImportError as exc:
        raise RuntimeError(
            "SeQUeNCe is not installed. Install the optional dependency with "
            "`pip install -e '.[sequence]'` in a Python 3.12+ environment."
        ) from exc

    try:
        version = metadata.version("sequence")
    except metadata.PackageNotFoundError:
        version = str(getattr(sq, "__version__", "unknown"))

    if version != SUPPORTED_SEQUENCE_VERSION:
        raise RuntimeError(
            f"Q-FABRIC adapter was reviewed for SeQUeNCe {SUPPORTED_SEQUENCE_VERSION}; "
            f"found {version!r}. Refusing an unvalidated API version."
        )
    return sq, version


def run_elementary_link_smoke_test(seed: int = 7, distance_m: float = 1_000.0) -> SequenceSmokeResult:
    """Run one SeQUeNCe Barrett-Kok elementary-link experiment.

    API construction follows the official SeQUeNCe 1.3.1 entanglement tutorial.
    The test uses idealized detector efficiency and zero channel attenuation so
    that it validates adapter wiring rather than a hardware performance claim.
    """
    if (
        isinstance(seed, bool)
        or not isinstance(seed, int)
    ):
        raise ValueError("seed must be an integer")

    if (
        isinstance(distance_m, bool)
        or not isinstance(distance_m, (int, float))
        or not math.isfinite(distance_m)
        or distance_m <= 0
    ):
        raise ValueError("distance_m must be a finite positive number")

    sq, version = _load_sequence()

    class _Manager:
        def __init__(self, owner: Any, memory_name: str):
            self.owner = owner
            self.memory_name = memory_name
            self.raw_counter = 0
            self.ent_counter = 0

        def update(self, protocol: Any, memory: Any, state: str) -> None:
            if state == "RAW":
                self.raw_counter += 1
                memory.reset()
            elif state == "ENTANGLED":
                self.ent_counter += 1

        def create_protocol(self, middle: str, other: str) -> None:
            memory = self.owner.components[self.memory_name]
            self.owner.protocols = [
                sq.EntanglementGenerationA.create(
                    self.owner, f"{self.owner.name}.eg", middle, other, memory
                )
            ]

    class _EntangleNode(sq.Node):
        def __init__(self, name: str, timeline: Any):
            super().__init__(name, timeline)
            memory_name = f"{name}.memo"
            memory = sq.Memory(memory_name, timeline, 0.9, 2_000, 1, -1, 500)
            memory.owner = self
            memory.add_receiver(self)
            self.add_component(memory)
            self.resource_manager = _Manager(self, memory_name)

        def init(self) -> None:
            self.get_components_by_type("Memory")[0].reset()

        def receive_message(self, src: str, msg: Any) -> None:
            self.protocols[0].received_message(src, msg)

        def get(self, photon: Any, **kwargs: Any) -> None:
            self.send_qubit(kwargs["dst"], photon)

    timeline = sq.Timeline()
    node_a = _EntangleNode("qf_node_a", timeline)
    node_b = _EntangleNode("qf_node_b", timeline)
    bsm = sq.BSMNode("qf_bsm", timeline, [node_a.name, node_b.name])
    node_a.set_seed(seed)
    node_b.set_seed(seed + 1)
    bsm.set_seed(seed + 2)

    bsm_device = bsm.get_components_by_type("SingleAtomBSM")[0]
    bsm_device.update_detectors_params("efficiency", 1)

    # The tutorial's elementary-link example uses two quantum channels to a BSM.
    qca = sq.QuantumChannel("qf_qc_a", timeline, attenuation=0, distance=distance_m)
    qcb = sq.QuantumChannel("qf_qc_b", timeline, attenuation=0, distance=distance_m)
    qca.set_ends(node_a, bsm.name)
    qcb.set_ends(node_b, bsm.name)

    nodes = [node_a, node_b, bsm]
    for source in nodes:
        for target in nodes:
            if source is not target:
                channel = sq.ClassicalChannel(
                    f"qf_cc_{source.name}_{target.name}", timeline, 1_000, 1e8
                )
                channel.set_ends(source, target.name)

    node_a.resource_manager.create_protocol(bsm.name, node_b.name)
    node_b.resource_manager.create_protocol(bsm.name, node_a.name)

    protocol_a = node_a.protocols[0]
    protocol_b = node_b.protocols[0]
    memory_a = node_a.get_components_by_type("Memory")[0]
    memory_b = node_b.get_components_by_type("Memory")[0]
    protocol_a.set_others(protocol_b.name, node_b.name, [memory_b.name])
    protocol_b.set_others(protocol_a.name, node_a.name, [memory_a.name])

    timeline.init()
    protocol_a.start()
    protocol_b.start()
    timeline.run()

    linked = (
        memory_a.entangled_memory.get("node_id") == node_b.name
        and memory_a.entangled_memory.get("memo_id") == memory_b.name
        and memory_b.entangled_memory.get("node_id") == node_a.name
        and memory_b.entangled_memory.get("memo_id") == memory_a.name
    )
    return SequenceSmokeResult(
        sequence_version=version,
        simulated_time=int(timeline.now()),
        entangled_memory_updates=node_a.resource_manager.ent_counter,
        raw_memory_updates=node_a.resource_manager.raw_counter,
        endpoint_a_fidelity=float(memory_a.fidelity),
        endpoint_b_fidelity=float(memory_b.fidelity),
        entangled_memory_linked=linked,
    )


@dataclass(frozen=True)
class SequenceSwappingResult:
    sequence_version: str
    simulated_time: int
    left_link_generated: bool
    right_link_generated: bool
    swapping_succeeded: bool
    endpoint_a_fidelity: float
    endpoint_c_fidelity: float
    end_to_end_entangled: bool
    left_link_attempts: int
    right_link_attempts: int
    left_link_simulated_time: int
    right_link_simulated_time: int
    pre_swap_endpoint_a_fidelity: float
    pre_swap_endpoint_c_fidelity: float


def run_three_node_swapping_smoke_test(
    seed: int = 17,
    distance_m: float = 500.0,
) -> SequenceSwappingResult:
    """Run Barrett-Kok generation on A-B and B-C, followed by swapping at B."""
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if (
        isinstance(distance_m, bool)
        or not isinstance(distance_m, (int, float))
        or not math.isfinite(distance_m)
        or distance_m <= 0
    ):
        raise ValueError("distance_m must be a finite positive number")

    sq, version = _load_sequence()
    from sequence.topology.node import QuantumRouter, BSMNode
    from sequence.entanglement_management.swapping.swapping_base import (
        EntanglementSwappingA,
        EntanglementSwappingB,
    )

    # Register the circuit-based swapping implementation.
    import_module("sequence.entanglement_management.swapping.swapping_circuit")

    EntanglementSwappingA.set_formalism("ket_vector")
    EntanglementSwappingB.set_formalism("ket_vector")

    timeline = sq.Timeline()

    node_a = QuantumRouter("qf3_a", timeline, memo_size=1, seed=seed)
    node_b = QuantumRouter("qf3_b", timeline, memo_size=2, seed=seed + 1)
    node_c = QuantumRouter("qf3_c", timeline, memo_size=1, seed=seed + 2)

    bsm_ab = BSMNode("qf3_bsm_ab", timeline, [node_a.name, node_b.name], seed=seed + 3)
    bsm_bc = BSMNode("qf3_bsm_bc", timeline, [node_b.name, node_c.name], seed=seed + 4)

    routers = [node_a, node_b, node_c]
    bsms = [bsm_ab, bsm_bc]
    nodes = routers + bsms

    # Use ideal detectors to test protocol integration, not hardware performance.
    for bsm in bsms:
        device = bsm.get_components_by_type("SingleAtomBSM")[0]
        device.update_detectors_params("efficiency", 1)

    # Two independent elementary quantum links.
    quantum_links = [
        (node_a, bsm_ab, "qf3_q_a_ab"),
        (node_b, bsm_ab, "qf3_q_b_ab"),
        (node_b, bsm_bc, "qf3_q_b_bc"),
        (node_c, bsm_bc, "qf3_q_c_bc"),
    ]

    for router, bsm, channel_name in quantum_links:
        channel = sq.QuantumChannel(
            channel_name,
            timeline,
            attenuation=0,
            distance=distance_m,
        )
        channel.set_ends(router, bsm.name)

    # Classical connectivity for generation and swapping messages.
    for source in nodes:
        for target in nodes:
            if source is target:
                continue
            channel = sq.ClassicalChannel(
                f"qf3_cc_{source.name}_{target.name}",
                timeline,
                1_000,
                1e8,
            )
            channel.set_ends(source, target.name)

    memory_a = node_a.components["qf3_a.MemoryArray"][0]
    memory_b_left = node_b.components["qf3_b.MemoryArray"][0]
    memory_b_right = node_b.components["qf3_b.MemoryArray"][1]
    memory_c = node_c.components["qf3_c.MemoryArray"][0]

    timeline.init()

    def generate_link(
        left_node,
        right_node,
        bsm,
        left_memory,
        right_memory,
        label,
        max_attempts=20,
    ):
        link_start_time = timeline.now()
        for attempt in range(1, max_attempts + 1):
            suffix = f"{label}_{attempt}"

            left_protocol = sq.EntanglementGenerationA.create(
                left_node,
                f"qf3_{suffix}_left",
                bsm.name,
                right_node.name,
                left_memory,
            )
            right_protocol = sq.EntanglementGenerationA.create(
                right_node,
                f"qf3_{suffix}_right",
                bsm.name,
                left_node.name,
                right_memory,
            )

            left_node.protocols.append(left_protocol)
            right_node.protocols.append(right_protocol)

            left_protocol.set_others(
                right_protocol.name,
                right_node.name,
                [right_memory.name],
            )
            right_protocol.set_others(
                left_protocol.name,
                left_node.name,
                [left_memory.name],
            )

            left_protocol.start()
            right_protocol.start()
            timeline.run()

            linked = (
                left_memory.entangled_memory.get("node_id") == right_node.name
                and right_memory.entangled_memory.get("node_id") == left_node.name
            )

            if linked:
                elapsed = int(timeline.now() - link_start_time)
                return left_protocol, right_protocol, attempt, elapsed

            remaining = (
                left_protocol in left_node.protocols
                or right_protocol in right_node.protocols
            )

            if remaining:
                raise RuntimeError(
                    f"{label} retry blocked: previous protocols remain registered; "
                    f"attempt={attempt}, "
                    f"results={left_protocol.bsm_res}/{right_protocol.bsm_res}"
                )

        raise RuntimeError(
            f"{label} generation exhausted {max_attempts} attempts; "
            f"time={timeline.now()}, "
            f"last_results={left_protocol.bsm_res}/{right_protocol.bsm_res}"
        )

    gen_a, gen_b_left, left_attempts, left_elapsed = generate_link(
        node_a, node_b, bsm_ab,
        memory_a, memory_b_left, "ab",
    )

    gen_b_right, gen_c, right_attempts, right_elapsed = generate_link(
        node_b, node_c, bsm_bc,
        memory_b_right, memory_c, "bc",
    )

    left_generated = True
    right_generated = True

    pre_swap_a_fidelity = float(memory_a.fidelity)
    pre_swap_c_fidelity = float(memory_c.fidelity)

    # Install the end-node swapping protocols.
    swap_a = EntanglementSwappingB.create(
        node_a, "qf3_swap_a", memory_a
    )
    swap_c = EntanglementSwappingB.create(
        node_c, "qf3_swap_c", memory_c
    )
    swap_b = EntanglementSwappingA.create(
        node_b,
        "qf3_swap_b",
        memory_b_left,
        memory_b_right,
        success_prob=1,
    )

    node_a.protocols.append(swap_a)
    node_b.protocols.append(swap_b)
    node_c.protocols.append(swap_c)

    swap_b.set_others(swap_a.name, node_a.name, [])
    swap_b.set_others(swap_c.name, node_c.name, [])
    swap_a.set_others(swap_b.name, node_b.name, [])
    swap_c.set_others(swap_b.name, node_b.name, [])

    swap_a.start()
    swap_c.start()
    swap_b.start()

    timeline.run()

    linked = (
        memory_a.entangled_memory.get("node_id") == node_c.name
        and memory_a.entangled_memory.get("memo_id") == memory_c.name
        and memory_c.entangled_memory.get("node_id") == node_a.name
        and memory_c.entangled_memory.get("memo_id") == memory_a.name
    )

    return SequenceSwappingResult(
        sequence_version=version,
        simulated_time=int(timeline.now()),
        left_link_generated=left_generated,
        right_link_generated=right_generated,
        swapping_succeeded=bool(swap_b.is_success),
        endpoint_a_fidelity=float(memory_a.fidelity),
        endpoint_c_fidelity=float(memory_c.fidelity),
        end_to_end_entangled=linked,
        left_link_attempts=left_attempts,
        right_link_attempts=right_attempts,
        left_link_simulated_time=left_elapsed,
        right_link_simulated_time=right_elapsed,
        pre_swap_endpoint_a_fidelity=pre_swap_a_fidelity,
        pre_swap_endpoint_c_fidelity=pre_swap_c_fidelity,
    )




@dataclass(frozen=True)
class SequencePurificationResult:
    sequence_version: str
    simulated_time: int
    left_link_attempts: int
    right_link_attempts: int
    input_fidelity: float
    output_fidelity_a: float
    output_fidelity_b: float
    measurement_a: int
    measurement_b: int
    purification_succeeded: bool
    kept_pair_linked: bool


def run_bbpssw_purification_smoke_test(
    seed: int = 17,
    distance_m: float = 500.0,
    max_attempts: int = 20,
) -> SequencePurificationResult:
    """Generate two elementary pairs and purify them using SeQUeNCe BBPSSW."""
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if (
        isinstance(distance_m, bool)
        or not isinstance(distance_m, (int, float))
        or not math.isfinite(distance_m)
        or distance_m <= 0
    ):
        raise ValueError("distance_m must be a finite positive number")
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 1:
        raise ValueError("max_attempts must be a positive integer")

    sq, version = _load_sequence()

    from sequence.topology.node import QuantumRouter, BSMNode
    from sequence.entanglement_management.purification.purification_protocol import (
        PurificationProtocol,
    )

    # Import registers the official circuit implementation.
    import_module("sequence.entanglement_management.purification.bbpssw_circuit")

    timeline = sq.Timeline()
    node_a = QuantumRouter("qfp_a", timeline, memo_size=2, seed=seed)
    node_b = QuantumRouter("qfp_b", timeline, memo_size=2, seed=seed + 1)

    bsm_left = BSMNode("qfp_bsm_left", timeline, [node_a.name, node_b.name], seed=seed + 2)
    bsm_right = BSMNode("qfp_bsm_right", timeline, [node_a.name, node_b.name], seed=seed + 3)

    nodes = [node_a, node_b, bsm_left, bsm_right]

    for bsm in (bsm_left, bsm_right):
        bsm.get_components_by_type("SingleAtomBSM")[0].update_detectors_params(
            "efficiency", 1
        )

    links = [
        (node_a, bsm_left, "qfp_q_a_left"),
        (node_b, bsm_left, "qfp_q_b_left"),
        (node_a, bsm_right, "qfp_q_a_right"),
        (node_b, bsm_right, "qfp_q_b_right"),
    ]

    for router, bsm, channel_name in links:
        channel = sq.QuantumChannel(
            channel_name, timeline, attenuation=0, distance=distance_m
        )
        channel.set_ends(router, bsm.name)

    for source in nodes:
        for target in nodes:
            if source is target:
                continue
            channel = sq.ClassicalChannel(
                f"qfp_cc_{source.name}_{target.name}", timeline, 1_000, 1e8
            )
            channel.set_ends(source, target.name)

    memories_a = [
        node_a.components["qfp_a.MemoryArray"][0],
        node_a.components["qfp_a.MemoryArray"][1],
    ]
    memories_b = [
        node_b.components["qfp_b.MemoryArray"][0],
        node_b.components["qfp_b.MemoryArray"][1],
    ]

    timeline.init()

    def generate_pair(index: int, bsm: Any) -> int:
        left_memory = memories_a[index]
        right_memory = memories_b[index]

        for attempt in range(1, max_attempts + 1):
            suffix = f"pair{index}_{attempt}"

            protocol_a = sq.EntanglementGenerationA.create(
                node_a, f"qfp_{suffix}_a", bsm.name, node_b.name, left_memory
            )
            protocol_b = sq.EntanglementGenerationA.create(
                node_b, f"qfp_{suffix}_b", bsm.name, node_a.name, right_memory
            )

            node_a.protocols.append(protocol_a)
            node_b.protocols.append(protocol_b)

            protocol_a.set_others(protocol_b.name, node_b.name, [right_memory.name])
            protocol_b.set_others(protocol_a.name, node_a.name, [left_memory.name])

            protocol_a.start()
            protocol_b.start()
            timeline.run()

            linked = (
                left_memory.entangled_memory.get("node_id") == node_b.name
                and left_memory.entangled_memory.get("memo_id") == right_memory.name
                and right_memory.entangled_memory.get("node_id") == node_a.name
                and right_memory.entangled_memory.get("memo_id") == left_memory.name
            )
            if linked:
                return attempt

            remaining = (
                protocol_a in node_a.protocols or protocol_b in node_b.protocols
            )
            if remaining:
                raise RuntimeError(
                    f"Generation retry blocked for pair {index}, attempt {attempt}"
                )

        raise RuntimeError(
            f"Could not generate pair {index} after {max_attempts} attempts"
        )

    left_attempts = generate_pair(0, bsm_left)
    right_attempts = generate_pair(1, bsm_right)

    input_fidelity = float(memories_a[0].fidelity)

    PurificationProtocol.set_formalism("ket_vector")

    purification_a = PurificationProtocol.create(
        node_a, "qfp_purification_a", memories_a[0], memories_a[1]
    )
    purification_b = PurificationProtocol.create(
        node_b, "qfp_purification_b", memories_b[0], memories_b[1]
    )

    node_a.protocols.append(purification_a)
    node_b.protocols.append(purification_b)

    purification_a.set_others(
        purification_b.name, node_b.name,
        [memories_b[0].name, memories_b[1].name],
    )
    purification_b.set_others(
        purification_a.name, node_a.name,
        [memories_a[0].name, memories_a[1].name],
    )

    purification_a.start()
    purification_b.start()
    timeline.run()

    succeeded = (
        purification_a.meas_res is not None
        and purification_b.meas_res is not None
        and purification_a.meas_res == purification_b.meas_res
    )

    kept_linked = (
        memories_a[0].entangled_memory.get("node_id") == node_b.name
        and memories_a[0].entangled_memory.get("memo_id") == memories_b[0].name
        and memories_b[0].entangled_memory.get("node_id") == node_a.name
        and memories_b[0].entangled_memory.get("memo_id") == memories_a[0].name
    )

    return SequencePurificationResult(
        sequence_version=version,
        simulated_time=int(timeline.now()),
        left_link_attempts=left_attempts,
        right_link_attempts=right_attempts,
        input_fidelity=input_fidelity,
        output_fidelity_a=float(memories_a[0].fidelity),
        output_fidelity_b=float(memories_b[0].fidelity),
        measurement_a=int(purification_a.meas_res),
        measurement_b=int(purification_b.meas_res),
        purification_succeeded=succeeded,
        kept_pair_linked=kept_linked,
    )


def network_state_from_sequence_result(
    result: SequenceSwappingResult,
    pair_coherence_time_ps: float,
    memory_slots: int = 1,
) -> NetworkState:
    """Convert one successful three-node SeQUeNCe run into a planner state.

    All time values use picoseconds. The per-run generation probability
    (1 / attempts) is a heuristic, not a statistically calibrated estimate.
    """
    if not isinstance(result, SequenceSwappingResult):
        raise ValueError("result must be a SequenceSwappingResult")

    if not result.left_link_generated or not result.right_link_generated:
        raise ValueError("both elementary links must be generated")

    if not result.swapping_succeeded or not result.end_to_end_entangled:
        raise ValueError("entanglement swapping must succeed")

    if (
        isinstance(pair_coherence_time_ps, bool)
        or not isinstance(pair_coherence_time_ps, (int, float))
        or not math.isfinite(pair_coherence_time_ps)
        or pair_coherence_time_ps <= 0
    ):
        raise ValueError("pair_coherence_time_ps must be finite and positive")

    if (
        isinstance(memory_slots, bool)
        or not isinstance(memory_slots, int)
        or memory_slots < 1
    ):
        raise ValueError("memory_slots must be an integer >= 1")

    def make_link(source: str, target: str, fidelity: float,
                  attempts: int, elapsed_ps: int) -> QuantumLink:
        if attempts < 1 or elapsed_ps < 1:
            raise ValueError("link attempts and elapsed time must be positive")
        attempt_duration = elapsed_ps / attempts
        return QuantumLink(
            source=source,
            target=target,
            fidelity=fidelity,
            generation_probability=1.0 / attempts,
            attempt_duration=attempt_duration,
            pair_coherence_time=float(pair_coherence_time_ps),
            memory_slots=memory_slots,
        )

    nodes = {
        "A": QuantumNode("A", memory_slots),
        "B": QuantumNode("B", memory_slots * 2),
        "C": QuantumNode("C", memory_slots),
    }
    links = [
        make_link(
            "A", "B", result.pre_swap_endpoint_a_fidelity,
            result.left_link_attempts, result.left_link_simulated_time,
        ),
        make_link(
            "B", "C", result.pre_swap_endpoint_c_fidelity,
            result.right_link_attempts, result.right_link_simulated_time,
        ),
    ]
    return NetworkState(nodes=nodes, links=links)
