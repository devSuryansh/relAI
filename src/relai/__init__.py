"""Agent Reliability Lab: evaluate, analyze, and compare AI agents."""

from relai.agents import Agent, FunctionAgent, ScriptedAgent
from relai.analysis import analyze
from relai.experiment import ExperimentReport, Variant, run_experiment
from relai.harness import EvalReport, evaluate
from relai.metrics import contains_match, exact_match
from relai.types import (
    FailureMode,
    FailureReport,
    RunMetrics,
    RunResult,
    Score,
    Step,
    StepKind,
    Task,
    Trajectory,
)

__version__ = "0.1.0"
__all__ = [
    "Agent",
    "EvalReport",
    "ExperimentReport",
    "FailureMode",
    "FailureReport",
    "FunctionAgent",
    "RunMetrics",
    "RunResult",
    "Score",
    "ScriptedAgent",
    "Step",
    "StepKind",
    "Task",
    "Trajectory",
    "Variant",
    "analyze",
    "contains_match",
    "evaluate",
    "exact_match",
    "run_experiment",
]
