"""Failure-mode classification over agent trajectories."""

from __future__ import annotations

from relai.types import (
    FailureMode,
    FailureReport,
    Score,
    StepKind,
    Task,
    Trajectory,
)


def analyze(task: Task, trajectory: Trajectory, score: Score) -> FailureReport:
    """Classify planning, tool, context, recovery, and horizon failures on one run."""
    evidence: list[str] = []
    modes: list[FailureMode] = []
    first_at: dict[FailureMode, int] = {}

    planning_idx = _planning_failure(task, trajectory, score, evidence)
    if planning_idx is not None:
        modes.append(FailureMode.PLANNING)
        first_at[FailureMode.PLANNING] = planning_idx

    tool_idx = _tool_misuse(task, trajectory, evidence)
    if tool_idx is not None:
        modes.append(FailureMode.TOOL_MISUSE)
        first_at[FailureMode.TOOL_MISUSE] = tool_idx

    context_idx = _context_failure(trajectory, evidence)
    if context_idx is not None:
        modes.append(FailureMode.CONTEXT)
        first_at[FailureMode.CONTEXT] = context_idx

    recovery_idx, effectiveness = _recovery_failure(trajectory, score, evidence)
    if recovery_idx is not None:
        modes.append(FailureMode.RECOVERY)
        first_at[FailureMode.RECOVERY] = recovery_idx

    horizon_idx = _horizon_failure(task, trajectory, evidence)
    if horizon_idx is not None:
        modes.append(FailureMode.HORIZON)
        first_at[FailureMode.HORIZON] = horizon_idx

    unclassified = not score.success and not modes
    if unclassified:
        evidence.append("failure did not match a known mode")

    root_cause = None
    if first_at:
        root_cause = min(first_at, key=first_at.get)

    return FailureReport(
        modes=modes,
        root_cause=root_cause,
        evidence=evidence,
        recovery_effectiveness=effectiveness,
        unclassified=unclassified,
    )


def _planning_failure(
    task: Task,
    trajectory: Trajectory,
    score: Score,
    evidence: list[str],
) -> int | None:
    if score.success or trajectory.final_output is None:
        return None
    tool_errors = [
        step
        for step in trajectory.of_kind(StepKind.TOOL_CALL)
        if step.tool_ok is False
    ]
    env_errors = trajectory.of_kind(StepKind.ERROR)
    if tool_errors or env_errors:
        return None
    plans = trajectory.of_kind(StepKind.PLAN)
    tools = trajectory.of_kind(StepKind.TOOL_CALL)
    requires_tools = "requires_tools" in task.tags or bool(task.allowed_tools)
    if requires_tools and not tools:
        evidence.append("required tools were never called")
        return _index_of(trajectory, StepKind.FINAL) or 0
    if "planning" in task.tags and not plans:
        evidence.append("planning-tagged task produced no plan")
        return _index_of(trajectory, StepKind.FINAL) or 0
    if not tools and not score.success:
        evidence.append("incorrect final answer with no tool use or errors")
        return _index_of(trajectory, StepKind.FINAL) or 0
    return None


def _tool_misuse(task: Task, trajectory: Trajectory, evidence: list[str]) -> int | None:
    first: int | None = None
    allowed = set(task.allowed_tools)
    for idx, step in enumerate(trajectory.steps):
        if step.kind != StepKind.TOOL_CALL:
            continue
        if allowed and step.tool_name not in allowed:
            evidence.append(f"called disallowed tool {step.tool_name!r}")
            first = idx if first is None else first
        if step.tool_ok is False and not _followed_by_error(trajectory, idx):
            evidence.append(f"tool {step.tool_name!r} failed without an environment error")
            first = idx if first is None else first
    return first


def _context_failure(trajectory: Trajectory, evidence: list[str]) -> int | None:
    last_sig: tuple[str | None, str] | None = None
    seen_observation = False
    for idx, step in enumerate(trajectory.steps):
        if step.kind == StepKind.OBSERVATION:
            seen_observation = True
            continue
        if step.kind != StepKind.TOOL_CALL:
            last_sig = None
            seen_observation = False
            continue
        sig = step.tool_signature()
        if last_sig == sig and seen_observation:
            evidence.append(
                f"repeated {step.tool_name!r} after an observation, ignoring new context"
            )
            return idx
        last_sig = sig
        seen_observation = False
    return None


def _followed_by_error(trajectory: Trajectory, idx: int) -> bool:
    rest = trajectory.steps[idx + 1 :]
    return bool(rest) and rest[0].kind == StepKind.ERROR


def _recovery_failure(
    trajectory: Trajectory,
    score: Score,
    evidence: list[str],
) -> tuple[int | None, float]:
    episodes = error_episodes(trajectory, score)
    if not episodes:
        return None, 1.0

    effectiveness = sum(1 for _, recovered in episodes if recovered) / len(episodes)
    failed_idx = next((idx for idx, recovered in episodes if not recovered), None)
    if failed_idx is None:
        return None, effectiveness

    has_recovery_step = any(
        step.kind == StepKind.RECOVERY for step in trajectory.steps[failed_idx:]
    )
    if not has_recovery_step:
        evidence.append("error occurred with no recovery attempt")
    else:
        evidence.append("recovery attempt did not restore a successful path")
    return failed_idx, effectiveness


def error_episodes(trajectory: Trajectory, score: Score) -> list[tuple[int, bool]]:
    """Each error step's index and whether the run later restored a working path.

    A path is restored by a later successful call of the tool that failed, or of
    any tool when the error follows no tool call, or by a correct final answer.
    Failed retries in between do not break the episode, so a chain of retries
    that ends in success counts every one of its errors as recovered.
    """
    steps = trajectory.steps
    episodes: list[tuple[int, bool]] = []
    for idx, step in enumerate(steps):
        if step.kind != StepKind.ERROR:
            continue
        previous = steps[idx - 1] if idx else None
        failed_tool = (
            previous.tool_name
            if previous is not None and previous.kind == StepKind.TOOL_CALL
            else None
        )
        recovered = False
        for later in steps[idx + 1 :]:
            if (
                later.kind == StepKind.TOOL_CALL
                and later.tool_ok
                and (failed_tool is None or later.tool_name == failed_tool)
            ):
                recovered = True
                break
            if later.kind == StepKind.FINAL:
                recovered = score.success
                break
        episodes.append((idx, recovered))
    return episodes


def _horizon_failure(task: Task, trajectory: Trajectory, evidence: list[str]) -> int | None:
    steps = len(trajectory.steps)
    if task.max_steps is not None and steps > task.max_steps:
        evidence.append(f"took {steps} steps, over the budget of {task.max_steps}")
        return task.max_steps
    if trajectory.final_output is None:
        evidence.append("run ended without a final answer")
        return max(steps - 1, 0)
    return None


def _index_of(trajectory: Trajectory, kind: StepKind) -> int | None:
    for idx, step in enumerate(trajectory.steps):
        if step.kind == kind:
            return idx
    return None
