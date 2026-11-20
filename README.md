# Q-FABRIC research prototype v0.2.1

Q-FABRIC is a research prototype for deadline-, memory-, fidelity-, and fairness-aware quantum-network resource orchestration. This release adds an optional integration adapter for SeQUeNCe 1.3.1.

## Core prototype
- Werner-state memory-decoherence approximation.
- Ideal Werner-state entanglement swapping.
- Ideal BBPSSW purification calculations.
- Simple path enumeration and feasibility screening.
- Reproducible Monte Carlo estimator for the completion-time distribution of independent elementary-link generation.
- Greedy feasibility-first, earliest-slack scheduling baseline (not a fairness optimizer).
- Hash-addressed prediction certificate with explicit non-verification status.

## SeQUeNCe adapter
The adapter includes three successfully executed SeQUeNCe 1.3.1 integration smoke experiments: Barrett–Kok elementary-link generation, three-node A-B-C entanglement swapping, and BBPSSW purification. It uses idealized detector efficiency and zero channel attenuation to validate wiring, not hardware performance.

Install and run in Python 3.12+:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e '.[test,sequence]'
pytest -q
qfabric-demo
qfabric-sequence-smoke
```

## Important limitations
1. The memory model assumes exponential depolarizing decay toward fidelity 1/4.
2. The pair coherence time is supplied directly; for independent exponential memory decoherence, `1/T_pair = 1/T_A + 1/T_B`.
3. Swapping and BBPSSW are idealized and exclude gate, measurement, detector, and control errors.
4. The planner uses a first-order expected-time approximation and includes estimated raw-pair generation cost for purification. The separate `qfabric.stochastic` utility estimates the mean and p50/p95/p99 completion time for independent geometric elementary-link generation, including multiple requested pairs. It does not yet model memory aging, swapping, purification, contention, or correlated retries, and it is not a physical simulation.
5. Memory accounting does not yet model per-qubit temporal reservation calendars or detailed memory-bank constraints.
6. The scheduler is greedy and does not implement a formal Max-Min or Jain-fairness optimizer.
7. A certificate is a hash-addressed prediction record, not physical-state attestation or proof of SLA fulfillment.
8. The SeQUeNCe 1.3.1 adapter has been executed successfully for elementary-link generation, three-node swapping, and BBPSSW purification. These are simulator integration checks, not hardware validation.

See `STATUS.md` for the current validation gate.
