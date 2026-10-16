"""Metric computation over scored trajectories."""

from __future__ import annotations

import re
import string
from collections.abc import Callable

from relai.analysis import error_episodes
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


def normalized_match(task: Task, trajectory: Trajectory) -> Score:
    """Exact match after lowercasing, dropping punctuation, and collapsing spaces."""
    expected = _normalize(task.expected or "")
    actual = _normalize(trajectory.final_output or "")
    if not expected:
        return Score(success=False, correctness=0.0, rationale="task has no expected output")
    if actual == expected:
        return Score(success=True, correctness=1.0, rationale="normalized match")
    return Score(
        success=False,
        correctness=0.0,
        rationale=f"expected {expected!r}, got {actual!r} after normalization",
    )


def numeric_match(tolerance: float = 1e-6) -> Scorer:
    """Compare the first number in the answer with the expected number.

    Success needs the absolute error to be within tolerance. Correctness gives
    partial credit as one minus the relative error, floored at zero.
    """

    def score(task: Task, trajectory: Trajectory) -> Score:
        expected = _first_number(task.expected or "")
        if expected is None:
            return Score(success=False, correctness=0.0, rationale="expected output has no number")
        actual = _first_number(trajectory.final_output or "")
        if actual is None:
            return Score(success=False, correctness=0.0, rationale="answer has no number")
        error = abs(actual - expected)
        if error <= tolerance:
            return Score(success=True, correctness=1.0, rationale="within tolerance")
        relative = error / max(abs(expected), 1e-12)
        return Score(
            success=False,
            correctness=max(0.0, 1.0 - relative),
            rationale=f"expected {expected:g}, got {actual:g}",
        )

    return score


def regex_match(pattern: str | None = None) -> Scorer:
    """Succeed when the answer matches a pattern, or the task's expected text as a pattern."""

    def score(task: Task, trajectory: Trajectory) -> Score:
        regex = pattern if pattern is not None else task.expected
        if not regex:
            return Score(success=False, correctness=0.0, rationale="no pattern to match")
        actual = trajectory.final_output or ""
        if re.search(regex, actual):
            return Score(success=True, correctness=1.0, rationale=f"matched /{regex}/")
        return Score(
            success=False,
            correctness=0.0,
            rationale=f"{actual!r} does not match /{regex}/",
        )

    return score


SCORERS: dict[str, Scorer] = {
    "exact": exact_match,
    "contains": contains_match,
    "normalized": normalized_match,
    "numeric": numeric_match(),
    "regex": regex_match(),
}


def get_scorer(name: str) -> Scorer:
    try:
        return SCORERS[name]
    except KeyError:
        known = ", ".join(sorted(SCORERS))
        raise ValueError(f"unknown scorer {name!r}; choose one of {known}") from None


_PUNCT = str.maketrans("", "", string.punctuation)
_NUMBER = re.compile(r"[-+]?(?:\d+(?:,\d{3})*(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?")


def _normalize(text: str) -> str:
    return " ".join(text.lower().translate(_PUNCT).split())


def _first_number(text: str) -> float | None:
    match = _NUMBER.search(text)
    if match is None:
        return None
    return float(match.group().replace(",", ""))


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
    episodes = error_episodes(trajectory, score)

    return RunMetrics(
        success=score.success,
        correctness=score.correctness,
        cost_usd=sum(step.cost_usd for step in steps),
        latency_ms=wall_ms,
        step_latency_ms=sum(step.latency_ms for step in steps),
        tokens=tokens,
        tool_calls=len(tool_calls),
        unnecessary_tool_calls=_unnecessary_tool_calls(trajectory),
        recovery_attempts=len(episodes),
        recovery_successes=sum(1 for _, recovered in episodes if recovered),
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
