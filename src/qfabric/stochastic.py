"""Monte Carlo completion-time estimates for independent link generation.

This module models only elementary-link generation. It does not model memory
aging, swapping, purification, scheduling contention, or SeQUeNCe events.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import random
from statistics import fmean
from typing import Sequence

from .models import QuantumLink


@dataclass(frozen=True)
class GenerationTimeDistribution:
    trials: int
    requested_pairs: int
    mean: float
    p50: float
    p95: float
    p99: float
    seed: int
    method: str = "independent-geometric-monte-carlo"


def estimate_parallel_link_generation(
    links: Sequence[QuantumLink],
    requested_pairs: int = 1,
    trials: int = 100_000,
    seed: int = 0,
) -> GenerationTimeDistribution:
    """Estimate time until every link has generated ``requested_pairs`` pairs.

    Each link independently performs Bernoulli generation attempts with a
    constant success probability and fixed attempt duration. Attempts for a
    given link are sequential; different links operate in parallel. The result
    is the distribution of the maximum link completion time.

    Quantiles use the nearest-rank definition. A fixed seed makes runs
    reproducible. This is an analytical-model Monte Carlo utility, not a
    physical simulation or a replacement for SeQUeNCe.
    """
    try:
        links = tuple(links)
    except TypeError as exc:
        raise ValueError("links must be an iterable of QuantumLink objects") from exc

    if not links:
        raise ValueError("at least one link is required")
    if any(not isinstance(link, QuantumLink) for link in links):
        raise ValueError("every item in links must be a QuantumLink")

    if isinstance(requested_pairs, bool) or not isinstance(requested_pairs, int):
        raise ValueError("requested_pairs must be a positive integer")
    if requested_pairs < 1:
        raise ValueError("requested_pairs must be >= 1")

    if isinstance(trials, bool) or not isinstance(trials, int):
        raise ValueError("trials must be a positive integer")
    if trials < 1:
        raise ValueError("trials must be >= 1")

    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    completion_times: list[float] = []
    for _ in range(trials):
        slowest_link = 0.0
        for link in links:
            p = link.generation_probability
            log_failure = math.log1p(-p) if p < 1.0 else None
            elapsed = 0.0
            for _pair in range(requested_pairs):
                if p == 1.0:
                    attempts = 1
                else:
                    u = rng.random()
                    attempts = math.floor(math.log1p(-u) / log_failure) + 1
                elapsed += attempts * link.attempt_duration
            if elapsed > slowest_link:
                slowest_link = elapsed
        completion_times.append(slowest_link)

    ordered = sorted(completion_times)

    def nearest_rank(q: float) -> float:
        index = max(0, math.ceil(q * trials) - 1)
        return ordered[index]

    return GenerationTimeDistribution(
        trials=trials,
        requested_pairs=requested_pairs,
        mean=fmean(completion_times),
        p50=nearest_rank(0.50),
        p95=nearest_rank(0.95),
        p99=nearest_rank(0.99),
        seed=seed,
    )
