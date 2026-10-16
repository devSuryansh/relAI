"""Controlled comparison of agent variants across a shared task suite."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from relai.agents import Agent
from relai.harness import EvalReport, evaluate
from relai.metrics import Scorer, exact_match
from relai.types import Task, Trajectory


@dataclass
class Variant:
    name: str
    agent: Agent
    config: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.agent.name != self.name:
            self.agent = _RenamedAgent(self.name, self.agent)


class _RenamedAgent:
    def __init__(self, name: str, inner: Agent) -> None:
        self.name = name
        self._inner = inner

    def run(self, task: Task) -> Trajectory:
        return self._inner.run(task)


class ExperimentReport(BaseModel):
    name: str = "experiment"
    suite: str = ""
    reports: list[EvalReport] = Field(default_factory=list)

    def ranking(self) -> list[EvalReport]:
        """Rank by success, then lower cost, then lower latency, then name.

        Latency compares recorded step latency first and whole milliseconds of
        wall-clock time second, so timer noise never reorders simulated runs.
        """
        return sorted(
            self.reports,
            key=lambda report: (
                -report.success_rate,
                round(report.mean_cost_usd, 12),
                round(report.mean_step_latency_ms, 3),
                round(report.mean_latency_ms),
                report.variant,
            ),
        )

    def report_for(self, variant: str) -> EvalReport:
        for report in self.reports:
            if report.variant == variant:
                return report
        raise KeyError(variant)

    def summary(self) -> list[dict[str, Any]]:
        return [report.summary() for report in self.ranking()]


def run_experiment(
    tasks: Sequence[Task],
    variants: Sequence[Variant],
    scorer: Scorer = exact_match,
    *,
    trials: int = 1,
    seed: int = 0,
    name: str = "experiment",
    suite: str = "",
) -> ExperimentReport:
    """Evaluate every variant on the same tasks, trials, and seed for a fair comparison."""
    names = [variant.name for variant in variants]
    if len(set(names)) != len(names):
        raise ValueError("variant names must be unique")
    reports = []
    for variant in variants:
        report = evaluate(variant.agent, tasks, scorer, trials=trials, seed=seed)
        report.config = dict(variant.config)
        reports.append(report)
    return ExperimentReport(name=name, suite=suite, reports=reports)


def stress_test(
    tasks: Sequence[Task],
    variants_at: Callable[[float], Sequence[Variant]],
    levels: Sequence[float],
    scorer: Scorer = exact_match,
    *,
    trials: int = 1,
    seed: int = 0,
) -> list[tuple[float, ExperimentReport]]:
    """Re-run the same variants at each stress level, such as a fault rate."""
    return [
        (
            level,
            run_experiment(
                tasks,
                variants_at(level),
                scorer,
                trials=trials,
                seed=seed,
                name=f"stress@{level:g}",
            ),
        )
        for level in levels
    ]
