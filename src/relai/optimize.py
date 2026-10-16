"""Configuration sweeps and Pareto selection: reliability against cost and latency."""

from __future__ import annotations

import itertools
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from relai.agents import Agent
from relai.experiment import ExperimentReport, Variant, run_experiment
from relai.harness import EvalReport
from relai.metrics import Scorer, exact_match
from relai.types import Task

Objective = tuple[str, bool]
"""An EvalReport attribute name and whether larger values are better."""

DEFAULT_OBJECTIVES: tuple[Objective, ...] = (
    ("success_rate", True),
    ("mean_cost_usd", False),
    ("mean_step_latency_ms", False),
)


def grid(space: Mapping[str, Sequence[Any]]) -> list[dict[str, Any]]:
    """Every combination of the listed parameter values, in a stable order."""
    keys = list(space)
    return [
        dict(zip(keys, values, strict=True))
        for values in itertools.product(*(space[key] for key in keys))
    ]


def config_name(config: Mapping[str, Any]) -> str:
    return ",".join(f"{key}={value}" for key, value in config.items()) or "default"


def sweep(
    tasks: Sequence[Task],
    factory: Callable[..., Agent],
    space: Mapping[str, Sequence[Any]],
    scorer: Scorer = exact_match,
    *,
    trials: int = 1,
    seed: int = 0,
    name: str = "sweep",
    suite: str = "",
) -> ExperimentReport:
    """Build one variant per configuration and evaluate them all under identical conditions."""
    variants = [
        Variant(config_name(config), factory(**config), config=config) for config in grid(space)
    ]
    return run_experiment(
        tasks, variants, scorer, trials=trials, seed=seed, name=name, suite=suite
    )


def parse_objective(text: str) -> Objective:
    """Parse 'attribute:max' or 'attribute:min'."""
    attr, _, direction = text.partition(":")
    if direction not in ("max", "min"):
        raise ValueError(f"objective {text!r} must end with ':max' or ':min'")
    return attr, direction == "max"


def objective_value(report: EvalReport, attr: str) -> float:
    value = getattr(report, attr)
    return float(value() if callable(value) else value)


def dominates(
    a: EvalReport,
    b: EvalReport,
    objectives: Sequence[Objective] = DEFAULT_OBJECTIVES,
) -> bool:
    """True when a is at least as good as b on every objective and better on one."""
    pairs = [(_oriented(a, objective), _oriented(b, objective)) for objective in objectives]
    return all(x >= y for x, y in pairs) and any(x > y for x, y in pairs)


def pareto_front(
    reports: Sequence[EvalReport],
    objectives: Sequence[Objective] = DEFAULT_OBJECTIVES,
) -> list[EvalReport]:
    """Variants that no other variant beats on every objective at once."""
    front = [
        report
        for report in reports
        if not any(dominates(other, report, objectives) for other in reports if other is not report)
    ]
    return ExperimentReport(reports=front).ranking()


def recommend(
    reports: Sequence[EvalReport],
    *,
    min_success: float = 0.9,
    metric: str = "success_rate",
) -> EvalReport | None:
    """The cheapest, then fastest, variant whose reliability metric meets the target."""
    eligible = [
        report for report in reports if objective_value(report, metric) >= min_success - 1e-12
    ]
    if not eligible:
        return None
    return min(
        eligible,
        key=lambda report: (
            round(report.mean_cost_usd, 12),
            round(report.mean_step_latency_ms, 9),
            report.mean_latency_ms,
            report.variant,
        ),
    )


def _oriented(report: EvalReport, objective: Objective) -> float:
    attr, maximize = objective
    value = round(objective_value(report, attr), 12)
    return value if maximize else -value
