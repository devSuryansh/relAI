"""Evaluation harness: run an agent over tasks and collect scored reports."""

from __future__ import annotations

import time
from collections.abc import Sequence
from math import comb
from typing import Any

from pydantic import BaseModel, Field

from relai.agents import Agent
from relai.analysis import analyze
from relai.env import SEED_KEY, TRIAL_KEY
from relai.metrics import Scorer, compute_metrics, exact_match
from relai.types import FailureMode, RunResult, Step, Task, Trajectory


class EvalReport(BaseModel):
    variant: str
    trials: int = 1
    seed: int = 0
    config: dict[str, Any] = Field(default_factory=dict)
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
    def mean_step_latency_ms(self) -> float:
        return _mean(result.metrics.step_latency_ms for result in self.results)

    @property
    def mean_tokens(self) -> float:
        return _mean(result.metrics.tokens.total for result in self.results)

    @property
    def mean_tool_calls(self) -> float:
        return _mean(result.metrics.tool_calls for result in self.results)

    @property
    def mean_recovery_rate(self) -> float:
        return _mean(result.metrics.recovery_rate for result in self.results)

    @property
    def mean_horizon_steps(self) -> float:
        return _mean(result.metrics.horizon_steps for result in self.results)

    @property
    def pass_hat_k_value(self) -> float:
        """pass^k at k = trials: the chance that every one of k attempts succeeds."""
        return self.pass_hat_k(self.trials)

    def by_task(self) -> dict[str, list[RunResult]]:
        grouped: dict[str, list[RunResult]] = {}
        for result in self.results:
            grouped.setdefault(result.task_id, []).append(result)
        return grouped

    def pass_at_k(self, k: int) -> float:
        """Mean chance that at least one of k sampled trials succeeds."""
        return _mean(
            _pass_at_k(len(runs), _successes(runs), k) for runs in self.by_task().values()
        )

    def pass_hat_k(self, k: int) -> float:
        """Mean chance that all k sampled trials succeed (tau-bench pass^k)."""
        return _mean(
            _pass_hat_k(len(runs), _successes(runs), k) for runs in self.by_task().values()
        )

    @property
    def consistency(self) -> float:
        """Share of tasks whose trials all agree, either all passing or all failing."""
        groups = list(self.by_task().values())
        if not groups:
            return 0.0
        agree = sum(1 for runs in groups if _successes(runs) in (0, len(runs)))
        return agree / len(groups)

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

    def root_cause_counts(self) -> dict[str, int]:
        counts = {mode.value: 0 for mode in FailureMode}
        for result in self.results:
            if result.failures.root_cause is not None:
                counts[result.failures.root_cause.value] += 1
        return counts

    def summary(self) -> dict[str, Any]:
        return {
            "variant": self.variant,
            "config": dict(self.config),
            "n": self.n,
            "trials": self.trials,
            "success_rate": self.success_rate,
            "pass_at_k": self.pass_at_k(self.trials),
            "pass_hat_k": self.pass_hat_k_value,
            "consistency": self.consistency,
            "mean_correctness": self.mean_correctness,
            "mean_cost_usd": self.mean_cost_usd,
            "mean_latency_ms": self.mean_latency_ms,
            "mean_step_latency_ms": self.mean_step_latency_ms,
            "mean_tokens": self.mean_tokens,
            "mean_tool_calls": self.mean_tool_calls,
            "mean_recovery_rate": self.mean_recovery_rate,
            "mean_horizon_steps": self.mean_horizon_steps,
            "failure_counts": self.failure_counts(),
            "root_causes": self.root_cause_counts(),
        }


def evaluate(
    agent: Agent,
    tasks: Sequence[Task],
    scorer: Scorer = exact_match,
    *,
    trials: int = 1,
    seed: int = 0,
) -> EvalReport:
    """Run one agent on every task, trials times each, and return scored reports.

    The trial index and seed reach the agent through task.metadata, so tool
    environments can replay the same fault schedule for every variant.
    """
    if trials < 1:
        raise ValueError("trials must be at least 1")
    results: list[RunResult] = []
    for task in tasks:
        for trial in range(trials):
            run_task = task.model_copy(
                update={"metadata": {**task.metadata, TRIAL_KEY: trial, SEED_KEY: seed}},
                deep=True,
            )
            started = time.perf_counter()
            trajectory = _run_safely(agent, run_task)
            wall_ms = (time.perf_counter() - started) * 1000
            score = scorer(task, trajectory)
            metrics = compute_metrics(trajectory, score, wall_ms)
            failures = analyze(task, trajectory, score)
            results.append(
                RunResult(
                    task_id=task.id,
                    variant=agent.name,
                    trial=trial,
                    trajectory=trajectory,
                    score=score,
                    metrics=metrics,
                    failures=failures,
                )
            )
    return EvalReport(variant=agent.name, trials=trials, seed=seed, results=results)


def _run_safely(agent: Agent, task: Task) -> Trajectory:
    """A crashing agent is a failed run, not a crashed experiment."""
    try:
        return agent.run(task)
    except Exception as exc:
        return Trajectory(
            steps=[Step.error(f"agent raised {type(exc).__name__}: {exc}")],
            metadata={"crashed": True},
        )


def _successes(runs: list[RunResult]) -> int:
    return sum(1 for run in runs if run.metrics.success)


def _pass_at_k(n: int, c: int, k: int) -> float:
    _check_k(n, k)
    if n - c < k:
        return 1.0
    return 1.0 - comb(n - c, k) / comb(n, k)


def _pass_hat_k(n: int, c: int, k: int) -> float:
    _check_k(n, k)
    return comb(c, k) / comb(n, k)


def _check_k(n: int, k: int) -> None:
    if not 1 <= k <= n:
        raise ValueError(f"k must be between 1 and the number of trials ({n}), got {k}")


def _mean(values: Any) -> float:
    items = list(values)
    if not items:
        return 0.0
    return sum(items) / len(items)
