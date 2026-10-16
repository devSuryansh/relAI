"""Statistics for reliability claims: confidence intervals and paired variant tests."""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from math import comb, sqrt
from statistics import NormalDist, fmean

from pydantic import BaseModel

from relai.harness import EvalReport


def wilson_interval(successes: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion; stays sensible at 0/n and n/n."""
    if n == 0:
        return (0.0, 1.0)
    if not 0 <= successes <= n:
        raise ValueError("successes must be between 0 and n")
    z = NormalDist().inv_cdf(0.5 + confidence / 2)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def bootstrap_ci(
    values: Sequence[float],
    *,
    statistic: Callable[[Sequence[float]], float] = fmean,
    confidence: float = 0.95,
    resamples: int = 2000,
    seed: int = 0,
) -> tuple[float, float]:
    """Seeded percentile bootstrap interval for a statistic of independent values."""
    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(values)
    draws = sorted(
        statistic([values[rng.randrange(n)] for _ in range(n)]) for _ in range(resamples)
    )
    alpha = (1 - confidence) / 2
    return (_quantile(draws, alpha), _quantile(draws, 1 - alpha))


def success_ci(
    report: EvalReport,
    *,
    confidence: float = 0.95,
    resamples: int = 2000,
    seed: int = 0,
) -> tuple[float, float]:
    """Interval for a report's success rate.

    Single-trial runs are independent, so this is a Wilson interval. With repeated
    trials the runs of one task are correlated, so tasks are resampled as whole
    clusters instead of resampling individual runs.
    """
    groups = [
        [1.0 if run.metrics.success else 0.0 for run in runs]
        for runs in report.by_task().values()
    ]
    if not groups:
        return (0.0, 0.0)
    if all(len(group) == 1 for group in groups):
        return wilson_interval(int(sum(g[0] for g in groups)), len(groups), confidence)
    rng = random.Random(seed)
    draws = []
    for _ in range(resamples):
        picked = [groups[rng.randrange(len(groups))] for _ in groups]
        draws.append(sum(sum(g) for g in picked) / sum(len(g) for g in picked))
    draws.sort()
    alpha = (1 - confidence) / 2
    return (_quantile(draws, alpha), _quantile(draws, 1 - alpha))


def mcnemar_exact(a_only: int, b_only: int) -> float:
    """Two-sided exact McNemar p-value from the two kinds of discordant pairs."""
    n = a_only + b_only
    if n == 0:
        return 1.0
    tail = sum(comb(n, i) for i in range(min(a_only, b_only) + 1)) / 2**n
    return min(1.0, 2 * tail)


class PairedComparison(BaseModel):
    a: str
    b: str
    pairs: int
    both: int
    a_only: int
    b_only: int
    neither: int
    p_value: float

    @property
    def delta(self) -> float:
        """Success-rate difference, a minus b, over the paired runs."""
        return (self.a_only - self.b_only) / self.pairs if self.pairs else 0.0

    def significant(self, alpha: float = 0.05) -> bool:
        return self.p_value < alpha


def compare(a: EvalReport, b: EvalReport) -> PairedComparison:
    """Pair two variants' runs by (task, trial) and test whether their success differs.

    Pairing is valid because both variants saw the same tasks and, through the
    shared seed, the same injected faults.
    """
    a_runs = {(run.task_id, run.trial): run.metrics.success for run in a.results}
    b_runs = {(run.task_id, run.trial): run.metrics.success for run in b.results}
    keys = a_runs.keys() & b_runs.keys()
    if not keys:
        raise ValueError("the reports share no (task, trial) pairs")
    both = sum(1 for key in keys if a_runs[key] and b_runs[key])
    a_only = sum(1 for key in keys if a_runs[key] and not b_runs[key])
    b_only = sum(1 for key in keys if b_runs[key] and not a_runs[key])
    return PairedComparison(
        a=a.variant,
        b=b.variant,
        pairs=len(keys),
        both=both,
        a_only=a_only,
        b_only=b_only,
        neither=len(keys) - both - a_only - b_only,
        p_value=mcnemar_exact(a_only, b_only),
    )


def _quantile(sorted_values: Sequence[float], q: float) -> float:
    position = q * (len(sorted_values) - 1)
    low = int(position)
    high = min(low + 1, len(sorted_values) - 1)
    weight = position - low
    return sorted_values[low] * (1 - weight) + sorted_values[high] * weight
