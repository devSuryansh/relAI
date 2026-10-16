import pytest

from relai.metrics import (
    compute_metrics,
    contains_match,
    exact_match,
    get_scorer,
    normalized_match,
    numeric_match,
    regex_match,
)
from relai.types import Score, Step, Task, TokenUsage, Trajectory


def test_exact_match_success() -> None:
    task = Task(id="t", prompt="q", expected="42")
    traj = Trajectory(steps=[Step.final("42")])
    score = exact_match(task, traj)
    assert score.success
    assert score.correctness == 1.0


def test_exact_match_failure_and_missing_expected() -> None:
    task = Task(id="t", prompt="q", expected="42")
    assert not exact_match(task, Trajectory(steps=[Step.final("41")])).success
    empty = Task(id="t", prompt="q")
    assert not exact_match(empty, Trajectory(steps=[Step.final("42")])).success


def test_contains_match() -> None:
    task = Task(id="t", prompt="q", expected="Paris")
    traj = Trajectory(steps=[Step.final("The capital is Paris.")])
    assert contains_match(task, traj).success


def test_normalized_match_ignores_case_punctuation_and_spacing() -> None:
    task = Task(id="t", prompt="q", expected="Gustave Eiffel")
    assert normalized_match(task, Trajectory(steps=[Step.final("  gustave   eiffel. ")])).success
    assert not normalized_match(task, Trajectory(steps=[Step.final("Eiffel")])).success


def test_numeric_match_gives_partial_credit_outside_tolerance() -> None:
    task = Task(id="t", prompt="q", expected="9984")
    scorer = numeric_match(tolerance=0.5)
    assert scorer(task, Trajectory(steps=[Step.final("It is 9,984.2 INR")])).success
    near = scorer(task, Trajectory(steps=[Step.final("9000")]))
    assert not near.success
    assert 0.9 < near.correctness < 0.91
    assert not scorer(task, Trajectory(steps=[Step.final("no idea")])).success


def test_regex_match_uses_task_expected_as_pattern() -> None:
    task = Task(id="t", prompt="q", expected=r"^O-\d{5}$")
    assert regex_match()(task, Trajectory(steps=[Step.final("O-88121")])).success
    assert not regex_match()(task, Trajectory(steps=[Step.final("order O-88121")])).success
    either = regex_match(r"shipped|delivered")
    assert either(task, Trajectory(steps=[Step.final("delivered")])).success


def test_get_scorer_rejects_unknown_names() -> None:
    assert get_scorer("exact") is exact_match
    with pytest.raises(ValueError, match="unknown scorer"):
        get_scorer("vibes")


def test_compute_metrics_aggregates_cost_tokens_tools_and_recovery() -> None:
    traj = Trajectory(
        steps=[
            Step.tool_call(
                "weather",
                {"city": "X"},
                ok=False,
                cost_usd=0.02,
                tokens=TokenUsage(prompt=10, completion=2),
                latency_ms=5,
            ),
            Step.error("timeout"),
            Step.recovery("retry"),
            Step.tool_call(
                "weather",
                {"city": "X"},
                ok=True,
                cost_usd=0.03,
                tokens=TokenUsage(prompt=8, completion=4),
                latency_ms=7,
            ),
            Step.observation("sunny"),
            Step.final("sunny", cost_usd=0.01, latency_ms=1),
        ]
    )
    score = Score(success=True, correctness=1.0)
    metrics = compute_metrics(traj, score, wall_ms=20.0)
    assert metrics.success
    assert metrics.cost_usd == 0.06
    assert metrics.latency_ms == 20.0
    assert metrics.step_latency_ms == 13.0
    assert metrics.tokens.total == 24
    assert metrics.tool_calls == 2
    assert metrics.recovery_attempts == 1
    assert metrics.recovery_successes == 1
    assert metrics.recovery_rate == 1.0
    assert metrics.horizon_steps == 6


def test_unnecessary_tool_calls_count_ignored_observations() -> None:
    traj = Trajectory(
        steps=[
            Step.tool_call("search", {"q": "a"}),
            Step.observation("result 1"),
            Step.tool_call("search", {"q": "a"}),
            Step.observation("result 1 again"),
            Step.final("a"),
        ]
    )
    metrics = compute_metrics(traj, Score(success=True, correctness=1.0), wall_ms=1.0)
    assert metrics.unnecessary_tool_calls == 1
