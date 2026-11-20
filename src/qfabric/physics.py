"""Explicitly scoped Werner-state calculations used by the planning prototype."""
from __future__ import annotations

import math


def werner_fidelity_after_wait(fidelity: float, wait_time: float, pair_coherence_time: float) -> float:
    """Depolarizing-memory approximation for a Werner pair.

    F(t)=1/4+(F0-1/4) exp(-t/T_pair). This is not a universal memory model.
    """
    _validate_fidelity(fidelity)
    wait_time = _finite(wait_time, "wait_time")
    pair_coherence_time = _finite(pair_coherence_time, "pair_coherence_time")
    if wait_time < 0 or pair_coherence_time <= 0:
        raise ValueError("wait_time must be >= 0 and coherence time > 0")
    return 0.25 + (fidelity - 0.25) * math.exp(-wait_time / pair_coherence_time)


def pair_coherence_time(t_a: float, t_b: float) -> float:
    """Effective pair time for independent exponential decoherence channels."""
    t_a = _finite(t_a, "t_a")
    t_b = _finite(t_b, "t_b")
    if t_a <= 0 or t_b <= 0:
        raise ValueError("single-memory coherence times must be positive")
    return 1.0 / (1.0 / t_a + 1.0 / t_b)


def werner_visibility(fidelity: float) -> float:
    _validate_fidelity(fidelity)
    return (4.0 * fidelity - 1.0) / 3.0


def fidelity_from_visibility(visibility: float) -> float:
    visibility = _finite(visibility, "visibility")
    if not 0.0 <= visibility <= 1.0:
        raise ValueError("visibility must be in [0, 1]")
    return (1.0 + 3.0 * visibility) / 4.0


def entanglement_swapping_fidelity(link_fidelities: list[float]) -> float:
    """Ideal swapping of independent Werner states, excluding gate/measurement errors."""
    if not link_fidelities:
        raise ValueError("at least one link fidelity is required")
    visibility = 1.0
    for fidelity in link_fidelities:
        visibility *= werner_visibility(fidelity)
    return fidelity_from_visibility(visibility)


def bbpssw_step(fidelity: float) -> tuple[float, float]:
    """Return (success_probability, output_fidelity) for ideal BBPSSW on Werner pairs."""
    _validate_fidelity(fidelity)
    p_success = (
        fidelity**2
        + 2.0 * fidelity * (1.0 - fidelity) / 3.0
        + 5.0 * (1.0 - fidelity) ** 2 / 9.0
    )
    numerator = fidelity**2 + (1.0 - fidelity) ** 2 / 9.0
    if p_success <= 0:
        raise ArithmeticError("non-positive purification success probability")
    return p_success, numerator / p_success


def bbpssw_rounds(fidelity: float, rounds: int) -> tuple[float, float, float]:
    """Return (final fidelity, cumulative success probability, raw-pair factor).

    For each ideal round, two equal-quality input pairs are consumed to produce
    one output pair with probability p. Expected raw-pair factor is multiplied
    by 2/p. Hardware errors and waiting-time correlations are not included.
    """
    if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds < 0:
        raise ValueError("rounds must be a non-negative integer")
    current = fidelity
    cumulative_success = 1.0
    raw_pair_factor = 1.0
    for _ in range(rounds):
        p, current = bbpssw_step(current)
        cumulative_success *= p
        raw_pair_factor *= 2.0 / p
    return current, cumulative_success, raw_pair_factor


def _finite(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _validate_fidelity(fidelity: float) -> None:
    fidelity = _finite(fidelity, "fidelity")
    if not 0.25 <= fidelity <= 1.0:
        raise ValueError("Werner-state fidelity must be in [0.25, 1]")
