"""Declarative task suites: tasks, mock tools, and default faults in one YAML file."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from relai.env import FaultPolicy, Tool, ToolEnv, calculator_tool, lookup_tool
from relai.types import Task

TASK_SHORTCUTS = ("solution", "answer", "guess")
"""Task keys that YAML authors may write at top level; they live in Task.metadata."""


class ToolSpec(BaseModel):
    kind: Literal["lookup", "calculator"] = "lookup"
    description: str = ""
    arg: str | None = None
    responses: dict[str, str] = Field(default_factory=dict)
    default: str = "no result"
    cost_usd: float = Field(default=0.0, ge=0.0)
    latency_ms: float = Field(default=0.0, ge=0.0)

    def build(self, name: str) -> Tool:
        if self.kind == "calculator":
            return calculator_tool(
                name,
                arg=self.arg or "expression",
                cost_usd=self.cost_usd,
                latency_ms=self.latency_ms,
            )
        return lookup_tool(
            name,
            self.responses,
            arg=self.arg or "q",
            default=self.default,
            description=self.description,
            cost_usd=self.cost_usd,
            latency_ms=self.latency_ms,
        )


class Suite(BaseModel):
    name: str
    description: str = ""
    scorer: str = "normalized"
    tools: dict[str, ToolSpec] = Field(default_factory=dict)
    faults: FaultPolicy = Field(default_factory=FaultPolicy)
    tasks: list[Task] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _lift_task_shortcuts(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        tasks = []
        for raw in data.get("tasks") or []:
            if isinstance(raw, dict):
                raw = dict(raw)
                metadata = dict(raw.get("metadata") or {})
                for key in TASK_SHORTCUTS:
                    if key in raw:
                        metadata[key] = raw.pop(key)
                raw["metadata"] = metadata
            tasks.append(raw)
        return {**data, "tasks": tasks}

    @model_validator(mode="after")
    def _check_references(self) -> Suite:
        ids = [task.id for task in self.tasks]
        if len(set(ids)) != len(ids):
            raise ValueError(f"suite {self.name!r} has duplicate task ids")
        for task in self.tasks:
            used = set(task.allowed_tools)
            used.update(step["tool"] for step in task.metadata.get("solution") or [])
            missing = used - set(self.tools)
            if missing:
                raise ValueError(f"task {task.id!r} uses undefined tools: {sorted(missing)}")
        return self

    def env(self, faults: FaultPolicy | None = None, *, seed: int = 0) -> ToolEnv:
        """Build the suite's tools, with its default faults unless others are given."""
        tools = [spec.build(name) for name, spec in self.tools.items()]
        return ToolEnv(tools, faults if faults is not None else self.faults, seed=seed)


def builtin_suites() -> list[str]:
    folder = resources.files("relai") / "suites"
    return sorted(
        entry.name.removesuffix(".yaml")
        for entry in folder.iterdir()
        if entry.name.endswith(".yaml")
    )


def load_suite(source: str | Path) -> Suite:
    """Load a suite from a .yaml, .yml, or .json path, or by built-in name."""
    path = Path(source)
    if path.is_file():
        text = path.read_text(encoding="utf-8")
        data = json.loads(text) if path.suffix == ".json" else yaml.safe_load(text)
    elif str(source) in builtin_suites():
        resource = resources.files("relai") / "suites" / f"{source}.yaml"
        data = yaml.safe_load(resource.read_text(encoding="utf-8"))
    else:
        known = ", ".join(builtin_suites())
        raise FileNotFoundError(f"no suite file or built-in suite named {str(source)!r} ({known})")
    return Suite.model_validate(data)


def save_suite(suite: Suite, path: str | Path) -> None:
    data = suite.model_dump(mode="json", exclude_defaults=True)
    target = Path(path)
    if target.suffix == ".json":
        target.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    else:
        target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
