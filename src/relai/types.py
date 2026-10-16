"""Domain types for agent trajectories, tasks, scores, and reports."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class StepKind(StrEnum):
    PLAN = "plan"
    TOOL_CALL = "tool_call"
    OBSERVATION = "observation"
    ERROR = "error"
    RECOVERY = "recovery"
    FINAL = "final"


class FailureMode(StrEnum):
    PLANNING = "planning"
    TOOL_MISUSE = "tool_misuse"
    CONTEXT = "context"
    RECOVERY = "recovery"
    HORIZON = "horizon"


class TokenUsage(BaseModel):
    prompt: int = 0
    completion: int = 0

    @property
    def total(self) -> int:
        return self.prompt + self.completion

    def __add__(self, other: TokenUsage) -> TokenUsage:
        return TokenUsage(
            prompt=self.prompt + other.prompt,
            completion=self.completion + other.completion,
        )


class Step(BaseModel):
    """One recorded action, observation, or outcome in an agent trajectory."""

    kind: StepKind
    content: str = ""
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    tool_ok: bool | None = None
    latency_ms: float = 0.0
    tokens: TokenUsage = Field(default_factory=TokenUsage)
    cost_usd: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def plan(cls, content: str, **kwargs: Any) -> Step:
        return cls(kind=StepKind.PLAN, content=content, **kwargs)

    @classmethod
    def tool_call(
        cls,
        name: str,
        args: dict[str, Any] | None = None,
        *,
        ok: bool = True,
        content: str = "",
        **kwargs: Any,
    ) -> Step:
        return cls(
            kind=StepKind.TOOL_CALL,
            content=content,
            tool_name=name,
            tool_args=args or {},
            tool_ok=ok,
            **kwargs,
        )

    @classmethod
    def observation(cls, content: str, **kwargs: Any) -> Step:
        return cls(kind=StepKind.OBSERVATION, content=content, **kwargs)

    @classmethod
    def error(cls, content: str, **kwargs: Any) -> Step:
        return cls(kind=StepKind.ERROR, content=content, **kwargs)

    @classmethod
    def recovery(cls, content: str, **kwargs: Any) -> Step:
        return cls(kind=StepKind.RECOVERY, content=content, **kwargs)

    @classmethod
    def final(cls, content: str, **kwargs: Any) -> Step:
        return cls(kind=StepKind.FINAL, content=content, **kwargs)

    def tool_signature(self) -> tuple[str | None, str]:
        return self.tool_name, repr(self.tool_args)


class Trajectory(BaseModel):
    steps: list[Step] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add(self, step: Step) -> None:
        self.steps.append(step)

    @property
    def final_output(self) -> str | None:
        for step in reversed(self.steps):
            if step.kind == StepKind.FINAL:
                return step.content
        return None

    def of_kind(self, kind: StepKind) -> list[Step]:
        return [step for step in self.steps if step.kind == kind]


class Task(BaseModel):
    id: str
    prompt: str
    expected: str | None = None
    allowed_tools: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    max_steps: int | None = Field(default=None, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Score(BaseModel):
    success: bool
    correctness: float = Field(ge=0.0, le=1.0)
    rationale: str = ""


class RunMetrics(BaseModel):
    success: bool
    correctness: float
    cost_usd: float
    latency_ms: float
    step_latency_ms: float
    tokens: TokenUsage = Field(default_factory=TokenUsage)
    tool_calls: int = 0
    unnecessary_tool_calls: int = 0
    recovery_attempts: int = 0
    recovery_successes: int = 0
    horizon_steps: int = 0

    @property
    def recovery_rate(self) -> float:
        if self.recovery_attempts == 0:
            return 1.0
        return self.recovery_successes / self.recovery_attempts


class FailureReport(BaseModel):
    modes: list[FailureMode] = Field(default_factory=list)
    root_cause: FailureMode | None = None
    evidence: list[str] = Field(default_factory=list)
    recovery_effectiveness: float = 1.0
    unclassified: bool = False


class RunResult(BaseModel):
    task_id: str
    variant: str
    trial: int = 0
    trajectory: Trajectory
    score: Score
    metrics: RunMetrics
    failures: FailureReport
