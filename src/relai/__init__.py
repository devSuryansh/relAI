"""Agent Reliability Lab: evaluate, analyze, and compare AI agents."""

from relai.agents import Agent, FunctionAgent, ScriptedAgent
from relai.analysis import analyze
from relai.baselines import (
    BASELINES,
    CarelessAgent,
    GuessingAgent,
    LoopingAgent,
    NaiveToolAgent,
    RetryAgent,
    make_baseline,
)
from relai.env import (
    FaultPolicy,
    Recorder,
    Tool,
    ToolEnv,
    ToolResult,
    calculator_tool,
    lookup_tool,
)
from relai.experiment import ExperimentReport, Variant, run_experiment, stress_test
from relai.harness import EvalReport, evaluate
from relai.metrics import (
    contains_match,
    exact_match,
    get_scorer,
    normalized_match,
    numeric_match,
    regex_match,
)
from relai.optimize import grid, pareto_front, recommend, sweep
from relai.report import to_html, to_markdown
from relai.selfcheck import planted_defect_check
from relai.stats import compare, mcnemar_exact, success_ci, wilson_interval
from relai.store import RunStore, read_jsonl, write_jsonl
from relai.suite import Suite, builtin_suites, load_suite
from relai.types import (
    FailureMode,
    FailureReport,
    RunMetrics,
    RunResult,
    Score,
    Step,
    StepKind,
    Task,
    TokenUsage,
    Trajectory,
)

__version__ = "0.1.0"
__all__ = [
    "BASELINES",
    "Agent",
    "CarelessAgent",
    "EvalReport",
    "ExperimentReport",
    "FailureMode",
    "FailureReport",
    "FaultPolicy",
    "FunctionAgent",
    "GuessingAgent",
    "LoopingAgent",
    "NaiveToolAgent",
    "Recorder",
    "RetryAgent",
    "RunMetrics",
    "RunResult",
    "RunStore",
    "Score",
    "ScriptedAgent",
    "Step",
    "StepKind",
    "Suite",
    "Task",
    "TokenUsage",
    "Tool",
    "ToolEnv",
    "ToolResult",
    "Trajectory",
    "Variant",
    "analyze",
    "builtin_suites",
    "calculator_tool",
    "compare",
    "contains_match",
    "evaluate",
    "exact_match",
    "get_scorer",
    "grid",
    "load_suite",
    "lookup_tool",
    "make_baseline",
    "mcnemar_exact",
    "normalized_match",
    "numeric_match",
    "pareto_front",
    "planted_defect_check",
    "read_jsonl",
    "recommend",
    "regex_match",
    "run_experiment",
    "stress_test",
    "success_ci",
    "sweep",
    "to_html",
    "to_markdown",
    "wilson_interval",
    "write_jsonl",
]
