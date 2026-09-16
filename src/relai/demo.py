"""Built-in demo suite: two variants on short-horizon, tool, and recovery tasks."""

from __future__ import annotations

from relai.agents import ScriptedAgent
from relai.types import Step, Task, Trajectory

DEMO_TASKS: list[Task] = [
    Task(
        id="short_horizon_qa",
        prompt="What is 6 * 7?",
        expected="42",
        tags=["short-horizon"],
    ),
    Task(
        id="tool_lookup",
        prompt="Look up the capital of France.",
        expected="Paris",
        allowed_tools=["search"],
        tags=["requires_tools"],
    ),
    Task(
        id="recover_from_timeout",
        prompt="Fetch the weather, retrying if the tool fails.",
        expected="sunny",
        allowed_tools=["weather"],
        tags=["requires_tools", "recovery"],
    ),
]


def brittle_agent() -> ScriptedAgent:
    return ScriptedAgent(
        "brittle",
        {
            "short_horizon_qa": Trajectory(steps=[Step.final("42", cost_usd=0.001)]),
            "tool_lookup": Trajectory(
                steps=[
                    Step.plan("Guess without searching"),
                    Step.final("Lyon", cost_usd=0.002),
                ]
            ),
            "recover_from_timeout": Trajectory(
                steps=[
                    Step.tool_call("weather", {"city": "X"}, ok=False, cost_usd=0.002),
                    Step.error("timeout"),
                    Step.final("unknown", cost_usd=0.001),
                ]
            ),
        },
    )


def resilient_agent() -> ScriptedAgent:
    return ScriptedAgent(
        "resilient",
        {
            "short_horizon_qa": Trajectory(
                steps=[Step.plan("Compute directly"), Step.final("42", cost_usd=0.001)]
            ),
            "tool_lookup": Trajectory(
                steps=[
                    Step.plan("Use search"),
                    Step.tool_call("search", {"q": "capital of France"}, cost_usd=0.002),
                    Step.observation("Paris"),
                    Step.final("Paris", cost_usd=0.001),
                ]
            ),
            "recover_from_timeout": Trajectory(
                steps=[
                    Step.plan("Call weather, retry on failure"),
                    Step.tool_call("weather", {"city": "X"}, ok=False, cost_usd=0.002),
                    Step.error("timeout"),
                    Step.recovery("retry once"),
                    Step.tool_call("weather", {"city": "X"}, ok=True, cost_usd=0.002),
                    Step.observation("sunny"),
                    Step.final("sunny", cost_usd=0.001),
                ]
            ),
        },
    )
