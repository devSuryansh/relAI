"""Controlled comparison of agent variants across a shared task suite."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from relai.agents import Agent
from relai.harness import EvalReport, evaluate
from relai.metrics import Scorer, exact_match
from relai.types import Task


@dataclass
class Variant:
    name: str
    agent: Agent

    def __post_init__(self) -> None:
        if self.agent.name != self.name:
            self.agent = _RenamedAgent(self.name, self.agent)


class _RenamedAgent:
    def __init__(self, name: str, inner: Agent) -> None:
        self.name = name
        self._inner = inner

    def run(self, task: Task):
        return self._inner.run(task)


class ExperimentReport(BaseModel):
    reports: list[EvalReport] = Field(default_factory=list)

    def ranking(self) -> list[EvalReport]:
        """Rank by success, then lower cost, then lower latency."""
        return sorted(
            self.reports,
            key=lambda report: (
                -report.success_rate,
                report.mean_cost_usd,
                report.mean_latency_ms,
            ),
        )

    def summary(self) -> list[dict[str, Any]]:
        return [report.summary() for report in self.ranking()]


def run_experiment(
    tasks: Sequence[Task],
    variants: Sequence[Variant],
    scorer: Scorer = exact_match,
) -> ExperimentReport:
    """Evaluate every variant on the same tasks for a controlled comparison."""
    reports = [evaluate(variant.agent, tasks, scorer) for variant in variants]
    return ExperimentReport(reports=reports)
