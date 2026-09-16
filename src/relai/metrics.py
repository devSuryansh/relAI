"""Metric computation over scored trajectories."""

from __future__ import annotations

from collections.abc import Callable

from relai.types import (
    RunMetrics,
    Score,
    StepKind,
    Task,
    TokenUsage,
    Trajectory,
)

Scorer = Callable[[Task, Trajectory], Score]


def exact_match(task: Task, trajectory: Trajectory) -> Score:
    expected = (task.expected or "").strip()
    actual = (trajectory.final_output or "").strip()
    if not expected:
        return Score(
            success=False,
            correctness=0.0,
            rationale="task has no expected output",
        )
    if actual == expected:
        return Score(success=True, correctness=1.0, rationale="exact match")
    return Score(
        success=False,
        correctness=0.0,
        rationale=f"expected {expected!r}, got {actual!r}",
    )


def contains_match(task: Task, trajectory: Trajectory) -> Score:
    expected = (task.expected or "").strip()
    actual = (trajectory.final_output or "").strip()
    if not expected:
        return Score(
            success=False,
            correctness=0.0,
            rationale="task has no expected output",
        )
    if expected in actual:
        return Score(success=True, correctness=1.0, rationale="contains expected text")
    return Score(
        success=False,
        correctness=0.0,
        rationale=f"{expected!r} not found in {actual!r}",
    )


def compute_metrics(
    trajectory: Trajectory,
    score: Score,
    wall_ms: float,
) -> RunMetrics:
    """Derive reliability, cost, latency, tool, and recovery metrics from a run."""
    steps = trajectory.steps
    tokens = TokenUsage()
    for step in steps:
        tokens = tokens + step.tokens

    tool_calls = trajectory.of_kind(StepKind.TOOL_CALL)
    errors = trajectory.of_kind(StepKind.ERROR)

    return RunMetrics(
        success=score.success,
        correctness=score.correctness,
        cost_usd=sum(step.cost_usd for step in steps),
        latency_ms=wall_ms,
        step_latency_ms=sum(step.latency_ms for step in steps),
        tokens=tokens,
        tool_calls=len(tool_calls),
        unnecessary_tool_calls=_unnecessary_tool_calls(trajectory),
        recovery_attempts=max(len(errors), len(trajectory.of_kind(StepKind.RECOVERY))),
        recovery_successes=_recovery_outcomes(trajectory, score),
        horizon_steps=len(steps),
    )


def _unnecessary_tool_calls(trajectory: Trajectory) -> int:
    """Count duplicate tool calls that ignore an intervening observation."""
    count = 0
    last_sig: tuple[str | None, str] | None = None
    seen_observation = False
    for step in trajectory.steps:
        if step.kind == StepKind.OBSERVATION:
            seen_observation = True
            continue
        if step.kind != StepKind.TOOL_CALL:
            last_sig = None
            seen_observation = False
            continue
        sig = step.tool_signature()
        if last_sig == sig and seen_observation:
            count += 1
        last_sig = sig
        seen_observation = False
    return count


def _recovery_outcomes(trajectory: Trajectory, score: Score) -> int:
    """Count error episodes that later reach a successful tool call or successful final."""
    successes = 0
    pending_error = False
    for step in trajectory.steps:
        if step.kind == StepKind.ERROR:
            pending_error = True
            continue
        if not pending_error:
            continue
        if step.kind == StepKind.TOOL_CALL and step.tool_ok:
            successes += 1
            pending_error = False
        elif step.kind == StepKind.FINAL and score.success:
            successes += 1
            pending_error = False
    return successes
