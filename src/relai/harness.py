"""Evaluation harness: run an agent over tasks and collect scored reports."""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, Field

from relai.agents import Agent
from relai.analysis import analyze
from relai.metrics import Scorer, compute_metrics, exact_match
from relai.types import FailureMode, RunResult, Task


class EvalReport(BaseModel):
    variant: str
    results: list[RunResult] = Field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.results)

    @property
    def success_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for result in self.results if result.metrics.success) / self.n

    @property
    def mean_correctness(self) -> float:
        return _mean(result.metrics.correctness for result in self.results)

    @property
    def mean_cost_usd(self) -> float:
        return _mean(result.metrics.cost_usd for result in self.results)

    @property
    def mean_latency_ms(self) -> float:
        return _mean(result.metrics.latency_ms for result in self.results)

    @property
    def mean_recovery_rate(self) -> float:
        return _mean(result.metrics.recovery_rate for result in self.results)

    @property
    def mean_horizon_steps(self) -> float:
        return _mean(result.metrics.horizon_steps for result in self.results)

    def failure_counts(self) -> dict[str, int]:
        counts = {mode.value: 0 for mode in FailureMode}
        unclassified = 0
        for result in self.results:
            for mode in result.failures.modes:
                counts[mode.value] += 1
            if result.failures.unclassified:
                unclassified += 1
        counts["unclassified"] = unclassified
        return counts

    def summary(self) -> dict[str, Any]:
        return {
            "variant": self.variant,
            "n": self.n,
            "success_rate": self.success_rate,
            "mean_correctness": self.mean_correctness,
            "mean_cost_usd": self.mean_cost_usd,
            "mean_latency_ms": self.mean_latency_ms,
            "mean_recovery_rate": self.mean_recovery_rate,
            "mean_horizon_steps": self.mean_horizon_steps,
            "failure_counts": self.failure_counts(),
        }


def evaluate(
    agent: Agent,
    tasks: Sequence[Task],
    scorer: Scorer = exact_match,
) -> EvalReport:
    """Run one agent on every task and return metrics plus failure reports."""
    results: list[RunResult] = []
    for task in tasks:
        started = time.perf_counter()
        trajectory = agent.run(task)
        wall_ms = (time.perf_counter() - started) * 1000
        score = scorer(task, trajectory)
        metrics = compute_metrics(trajectory, score, wall_ms)
        failures = analyze(task, trajectory, score)
        results.append(
            RunResult(
                task_id=task.id,
                variant=agent.name,
                trajectory=trajectory,
                score=score,
                metrics=metrics,
                failures=failures,
            )
        )
    return EvalReport(variant=agent.name, results=results)


def _mean(values: Any) -> float:
    items = list(values)
    if not items:
        return 0.0
    return sum(items) / len(items)
