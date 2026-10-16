"""Tool environment with seeded fault injection for recovery experiments."""

from __future__ import annotations

import ast
import operator
import random
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, model_validator

from relai.types import Step, Task, Trajectory

TRIAL_KEY = "relai.trial"
SEED_KEY = "relai.seed"


class FaultPolicy(BaseModel):
    """Environment failures injected into tool calls.

    A fault depends only on (seed, task, trial, tool, call number), never on which
    agent is calling, so every variant faces the same failure schedule.
    """

    timeout_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    fail_first_n: int = Field(default=0, ge=0)
    timeout_ms: float = Field(default=1000.0, ge=0.0)
    tools: list[str] | None = None

    @model_validator(mode="after")
    def _rates_fit(self) -> FaultPolicy:
        if self.timeout_rate + self.error_rate > 1.0:
            raise ValueError("timeout_rate + error_rate must not exceed 1.0")
        return self

    @property
    def active(self) -> bool:
        return bool(self.timeout_rate or self.error_rate or self.fail_first_n)

    def applies_to(self, tool: str) -> bool:
        return self.tools is None or tool in self.tools

    def fault_for(self, *, seed: int, task_id: str, trial: int, tool: str, call: int) -> str | None:
        """Return the fault for the call-th call of a tool in one run, if any."""
        if not self.applies_to(tool):
            return None
        if call <= self.fail_first_n:
            return "timeout"
        draw = random.Random(f"{seed}:{task_id}:{trial}:{tool}:{call}").random()
        if draw < self.timeout_rate:
            return "timeout"
        if draw < self.timeout_rate + self.error_rate:
            return "unavailable"
        return None


@dataclass(frozen=True)
class Tool:
    name: str
    fn: Callable[..., Any]
    description: str = ""
    parameters: Mapping[str, Any] = field(default_factory=dict)
    cost_usd: float = 0.0
    latency_ms: float = 0.0

    def spec(self) -> dict[str, Any]:
        """OpenAI-style function schema for model adapters."""
        parameters = dict(self.parameters) or {"type": "object", "properties": {}}
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters,
            },
        }


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    output: str = ""
    fault: str | None = None
    cost_usd: float = 0.0
    latency_ms: float = 0.0


class ToolSession:
    """Tool access for one run of one task, with its own call counters."""

    def __init__(self, env: ToolEnv, task: Task) -> None:
        self.env = env
        self.task = task
        self.trial = int(task.metadata.get(TRIAL_KEY, 0))
        self.seed = int(task.metadata.get(SEED_KEY, env.seed))
        self._calls: dict[str, int] = {}

    def call(self, name: str, args: Mapping[str, Any] | None = None) -> ToolResult:
        tool = self.env.tools.get(name)
        if tool is None:
            return ToolResult(ok=False, output=f"unknown tool {name!r}")
        call = self._calls[name] = self._calls.get(name, 0) + 1
        fault = self.env.faults.fault_for(
            seed=self.seed,
            task_id=self.task.id,
            trial=self.trial,
            tool=name,
            call=call,
        )
        if fault == "timeout":
            return ToolResult(
                ok=False,
                output=f"{name} timed out",
                fault=fault,
                cost_usd=tool.cost_usd,
                latency_ms=self.env.faults.timeout_ms,
            )
        if fault is not None:
            return ToolResult(
                ok=False,
                output=f"{name} is unavailable",
                fault=fault,
                cost_usd=tool.cost_usd,
                latency_ms=tool.latency_ms,
            )
        try:
            output = tool.fn(**dict(args or {}))
        except Exception as exc:
            # Bad arguments are the agent's mistake, so this is not an environment fault.
            return ToolResult(
                ok=False,
                output=f"{type(exc).__name__}: {exc}",
                cost_usd=tool.cost_usd,
                latency_ms=tool.latency_ms,
            )
        return ToolResult(
            ok=True,
            output=str(output),
            cost_usd=tool.cost_usd,
            latency_ms=tool.latency_ms,
        )


class Recorder:
    """Builds a trajectory while an agent works, routing tool calls through a session."""

    def __init__(self, session: ToolSession | None = None) -> None:
        self.trajectory = Trajectory()
        self._session = session

    @property
    def steps(self) -> int:
        return len(self.trajectory.steps)

    def plan(self, content: str, **kwargs: Any) -> None:
        self.trajectory.add(Step.plan(content, **kwargs))

    def observe(self, content: str, **kwargs: Any) -> None:
        self.trajectory.add(Step.observation(content, **kwargs))

    def error(self, content: str, **kwargs: Any) -> None:
        self.trajectory.add(Step.error(content, **kwargs))

    def recovery(self, content: str, **kwargs: Any) -> None:
        self.trajectory.add(Step.recovery(content, **kwargs))

    def call(self, name: str, args: Mapping[str, Any] | None = None) -> ToolResult:
        if self._session is None:
            raise RuntimeError("this recorder has no tool session")
        result = self._session.call(name, args)
        self.trajectory.add(
            Step.tool_call(
                name,
                dict(args or {}),
                ok=result.ok,
                cost_usd=result.cost_usd,
                latency_ms=result.latency_ms,
            )
        )
        if result.fault is not None:
            self.error(f"{result.fault}: {result.output}", metadata={"fault": result.fault})
        else:
            self.observe(result.output)
        return result

    def final(self, content: str, **kwargs: Any) -> Trajectory:
        self.trajectory.add(Step.final(content, **kwargs))
        return self.trajectory

    def stop(self) -> Trajectory:
        """End the run without a final answer."""
        return self.trajectory


class ToolEnv:
    """A set of tools plus the fault policy applied to every run that uses them."""

    def __init__(
        self,
        tools: Iterable[Tool],
        faults: FaultPolicy | None = None,
        *,
        seed: int = 0,
    ) -> None:
        self.tools = {tool.name: tool for tool in tools}
        self.faults = faults or FaultPolicy()
        self.seed = seed

    def session(self, task: Task) -> ToolSession:
        return ToolSession(self, task)

    def recorder(self, task: Task) -> Recorder:
        return Recorder(self.session(task))

    def with_faults(self, faults: FaultPolicy | None) -> ToolEnv:
        return ToolEnv(self.tools.values(), faults, seed=self.seed)

    def specs(self, names: Iterable[str] | None = None) -> list[dict[str, Any]]:
        wanted = set(names) if names else None
        return [
            tool.spec()
            for tool in self.tools.values()
            if wanted is None or tool.name in wanted
        ]


def lookup_tool(
    name: str,
    responses: Mapping[str, str],
    *,
    arg: str = "q",
    default: str = "no result",
    description: str = "",
    cost_usd: float = 0.0,
    latency_ms: float = 0.0,
) -> Tool:
    """A deterministic tool that answers from a table, ignoring case and spacing."""
    table = {_key(key): value for key, value in responses.items()}

    def fn(**kwargs: Any) -> str:
        if set(kwargs) != {arg}:
            raise TypeError(f"{name} takes exactly one argument named {arg!r}")
        return table.get(_key(str(kwargs[arg])), default)

    return Tool(
        name=name,
        fn=fn,
        description=description or f"Look up a value by {arg}.",
        parameters=_one_string_arg(arg),
        cost_usd=cost_usd,
        latency_ms=latency_ms,
    )


def calculator_tool(
    name: str = "calculator",
    *,
    arg: str = "expression",
    cost_usd: float = 0.0,
    latency_ms: float = 0.0,
) -> Tool:
    """Arithmetic over + - * / ** and parentheses, evaluated without eval()."""

    def fn(**kwargs: Any) -> str:
        if set(kwargs) != {arg}:
            raise TypeError(f"{name} takes exactly one argument named {arg!r}")
        value = _arith(ast.parse(str(kwargs[arg]), mode="eval").body)
        rounded = round(value, 6)
        return str(int(rounded)) if rounded == int(rounded) else str(rounded)

    return Tool(
        name=name,
        fn=fn,
        description="Evaluate an arithmetic expression.",
        parameters=_one_string_arg(arg),
        cost_usd=cost_usd,
        latency_ms=latency_ms,
    )


_OPS: dict[type, Callable[..., float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _arith(node: ast.expr) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _arith(node.left), _arith(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 64:
            raise ValueError("exponent too large")
        return _OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_arith(node.operand))
    raise ValueError("unsupported expression")


def _key(text: str) -> str:
    return " ".join(text.lower().split())


def _one_string_arg(arg: str) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {arg: {"type": "string"}},
        "required": [arg],
    }
