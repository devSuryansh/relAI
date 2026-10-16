"""Reference agents with known behaviour, for offline experiments and classifier checks.

Each agent follows the reference tool plan in task.metadata["solution"] but
handles trouble in its own way, so the failure mode it should trigger is known
in advance. That makes them stand-ins for real agents when no model API is
available, and planted-defect fixtures for checking the failure classifier.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, ClassVar

from relai.env import Recorder, ToolEnv, ToolResult
from relai.types import FailureMode, Task, Trajectory

SOLUTION_KEY = "solution"
ANSWER_KEY = "answer"
GUESS_KEY = "guess"


@dataclass(frozen=True)
class PlannedCall:
    tool: str
    args: dict[str, Any]


def solution_of(task: Task) -> list[PlannedCall]:
    return [
        PlannedCall(tool=step["tool"], args=dict(step.get("args") or {}))
        for step in task.metadata.get(SOLUTION_KEY) or []
    ]


class PolicyAgent:
    """Runs the reference plan once and gives up on the first failed call."""

    default_name: ClassVar[str] = "naive"
    planted: ClassVar[FailureMode | None] = FailureMode.RECOVERY
    positional: ClassVar[str | None] = None

    def __init__(self, env: ToolEnv, *, name: str | None = None) -> None:
        self.env = env
        self.name = name or self.default_name

    def run(self, task: Task) -> Trajectory:
        rec = self.env.recorder(task)
        plan = solution_of(task)
        self.begin(rec, task, plan)
        outputs: list[str] = []
        for call in plan:
            result = self.attempt(rec, call.tool, _fill(call.args, outputs))
            if not result.ok:
                return rec.final("unknown")
            outputs.append(result.output)
        return rec.final(_answer(task, outputs))

    def begin(self, rec: Recorder, task: Task, plan: Sequence[PlannedCall]) -> None:
        rec.plan(_describe(plan))

    def attempt(self, rec: Recorder, tool: str, args: dict[str, Any]) -> ToolResult:
        return rec.call(tool, args)


class NaiveToolAgent(PolicyAgent):
    pass


class RetryAgent(PolicyAgent):
    """Retries environment faults with optional exponential backoff."""

    default_name = "retry"
    planted = None
    positional = "max_retries"

    def __init__(
        self,
        env: ToolEnv,
        *,
        max_retries: int = 2,
        backoff_ms: float = 0.0,
        name: str | None = None,
    ) -> None:
        super().__init__(env, name=name)
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        self.max_retries = max_retries
        self.backoff_ms = backoff_ms

    def attempt(self, rec: Recorder, tool: str, args: dict[str, Any]) -> ToolResult:
        result = rec.call(tool, args)
        retries = 0
        while not result.ok and result.fault is not None and retries < self.max_retries:
            retries += 1
            rec.recovery(
                f"retry {retries}/{self.max_retries} after {result.fault}",
                latency_ms=self.backoff_ms * 2 ** (retries - 1),
            )
            result = rec.call(tool, args)
        return result


class GuessingAgent(PolicyAgent):
    """Answers from memory and never calls a tool."""

    default_name = "guessing"
    planted = FailureMode.PLANNING

    def run(self, task: Task) -> Trajectory:
        rec = Recorder()
        rec.plan("answer from memory without tools")
        guess = task.metadata.get(GUESS_KEY, task.metadata.get(ANSWER_KEY, "unknown"))
        return rec.final(str(guess))


class LoopingAgent(RetryAgent):
    """Retries faults, but repeats each successful call and ignores what it returned."""

    default_name = "looping"
    planted = FailureMode.CONTEXT
    positional = "repeats"

    def __init__(
        self,
        env: ToolEnv,
        *,
        repeats: int = 2,
        max_retries: int = 2,
        name: str | None = None,
    ) -> None:
        super().__init__(env, max_retries=max_retries, name=name)
        self.repeats = repeats

    def attempt(self, rec: Recorder, tool: str, args: dict[str, Any]) -> ToolResult:
        result = super().attempt(rec, tool, args)
        if result.ok:
            for _ in range(self.repeats):
                rec.call(tool, args)
        return result


class CarelessAgent(RetryAgent):
    """Retries faults, but first reaches for a tool it was never given."""

    default_name = "careless"
    planted = FailureMode.TOOL_MISUSE
    positional = None

    def begin(self, rec: Recorder, task: Task, plan: Sequence[PlannedCall]) -> None:
        super().begin(rec, task, plan)
        rec.call("shell", {"cmd": f"grep -r '{task.id}' /data"})


BASELINES: dict[str, type[PolicyAgent]] = {
    "naive": NaiveToolAgent,
    "retry": RetryAgent,
    "guessing": GuessingAgent,
    "looping": LoopingAgent,
    "careless": CarelessAgent,
}


def make_baseline(spec: str, env: ToolEnv) -> PolicyAgent:
    """Build a baseline from 'name', 'name:value', or 'name:key=value,key=value'.

    The variant is named after the full spec, so 'retry:3' and 'retry:1' can be
    compared side by side.
    """
    kind, _, params = spec.partition(":")
    if kind not in BASELINES:
        known = ", ".join(BASELINES)
        raise ValueError(f"unknown baseline {kind!r}; choose one of {known}")
    cls = BASELINES[kind]
    kwargs: dict[str, Any] = {}
    for part in filter(None, params.split(",")):
        key, eq, value = part.partition("=")
        if not eq:
            if cls.positional is None:
                raise ValueError(f"baseline {kind!r} takes no positional parameter")
            key, value = cls.positional, part
        kwargs[key.strip()] = _parse_value(value.strip())
    return cls(env, name=spec if params else None, **kwargs)


def _describe(plan: Sequence[PlannedCall]) -> str:
    if not plan:
        return "answer directly"
    return "call " + ", then ".join(call.tool for call in plan)


def _fill(args: Mapping[str, Any], outputs: Sequence[str]) -> dict[str, Any]:
    filled: dict[str, Any] = {}
    for key, value in args.items():
        if isinstance(value, str):
            try:
                value = value.format(*outputs)
            except (IndexError, KeyError, ValueError):
                pass
        filled[key] = value
    return filled


def _answer(task: Task, outputs: Sequence[str]) -> str:
    template = task.metadata.get(ANSWER_KEY)
    if template is not None:
        try:
            return str(template).format(*outputs)
        except (IndexError, KeyError, ValueError):
            return str(template)
    return outputs[-1] if outputs else "unknown"


def _parse_value(text: str) -> Any:
    for cast in (int, float):
        try:
            return cast(text)
        except ValueError:
            continue
    if text.lower() in ("true", "false"):
        return text.lower() == "true"
    return text
