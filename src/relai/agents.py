"""Agent seam: any object with a name and run(task) -> Trajectory."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Protocol, runtime_checkable

from relai.types import Task, Trajectory


@runtime_checkable
class Agent(Protocol):
    """Anything that can produce a trajectory for a task."""

    name: str

    def run(self, task: Task) -> Trajectory: ...


class FunctionAgent:
    """Adapter that wraps a callable into the Agent interface."""

    def __init__(self, name: str, fn: Callable[[Task], Trajectory]) -> None:
        self.name = name
        self._fn = fn

    def run(self, task: Task) -> Trajectory:
        return self._fn(task)


class ScriptedAgent:
    """Deterministic agent that returns a canned trajectory per task id."""

    def __init__(
        self,
        name: str,
        scripts: Mapping[str, Trajectory],
        default: Trajectory | None = None,
    ) -> None:
        self.name = name
        self._scripts = dict(scripts)
        self._default = default or Trajectory()

    def run(self, task: Task) -> Trajectory:
        return self._scripts.get(task.id, self._default).model_copy(deep=True)
