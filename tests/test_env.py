import pytest

from relai.analysis import analyze
from relai.env import (
    SEED_KEY,
    TRIAL_KEY,
    FaultPolicy,
    Recorder,
    ToolEnv,
    calculator_tool,
    lookup_tool,
)
from relai.types import FailureMode, Score, StepKind, Task


def _task(trial: int = 0, seed: int = 0) -> Task:
    return Task(
        id="t",
        prompt="p",
        expected="sunny",
        allowed_tools=["weather"],
        metadata={TRIAL_KEY: trial, SEED_KEY: seed},
    )


def _weather_env(faults: FaultPolicy | None = None) -> ToolEnv:
    return ToolEnv([lookup_tool("weather", {"X": "sunny"}, arg="city", latency_ms=50)], faults)


def _schedule(env: ToolEnv, task: Task, calls: int = 20) -> list[str | None]:
    session = env.session(task)
    return [session.call("weather", {"city": "X"}).fault for _ in range(calls)]


def test_fault_schedule_is_reproducible_and_agent_independent() -> None:
    env = _weather_env(FaultPolicy(timeout_rate=0.4))
    first = _schedule(env, _task())
    assert first == _schedule(env, _task())
    assert "timeout" in first
    assert None in first


def test_fault_schedule_changes_with_trial_and_seed() -> None:
    env = _weather_env(FaultPolicy(timeout_rate=0.4))
    base = _schedule(env, _task())
    assert base != _schedule(env, _task(trial=1))
    assert base != _schedule(env, _task(seed=7))


def test_fail_first_n_and_tool_scoping() -> None:
    env = ToolEnv(
        [
            lookup_tool("weather", {"X": "sunny"}, arg="city"),
            lookup_tool("search", {"a": "b"}),
        ],
        FaultPolicy(fail_first_n=2, tools=["weather"]),
    )
    session = env.session(_task())
    faults = [session.call("weather", {"city": "X"}).fault for _ in range(3)]
    assert faults == ["timeout", "timeout", None]
    assert session.call("search", {"q": "a"}).ok


def test_rates_must_fit_in_one() -> None:
    with pytest.raises(ValueError):
        FaultPolicy(timeout_rate=0.7, error_rate=0.5)


def test_recorder_writes_error_steps_for_faults_and_observations_otherwise() -> None:
    env = _weather_env(FaultPolicy(fail_first_n=1, timeout_ms=900))
    rec = env.recorder(_task())
    first = rec.call("weather", {"city": "X"})
    rec.recovery("retry")
    second = rec.call("weather", {"city": "X"})
    traj = rec.final(second.output)
    assert not first.ok and first.fault == "timeout"
    assert second.ok and second.output == "sunny"
    kinds = [step.kind for step in traj.steps]
    assert kinds == [
        StepKind.TOOL_CALL,
        StepKind.ERROR,
        StepKind.RECOVERY,
        StepKind.TOOL_CALL,
        StepKind.OBSERVATION,
        StepKind.FINAL,
    ]
    assert traj.steps[0].latency_ms == 900
    assert traj.steps[3].latency_ms == 50
    report = analyze(_task(), traj, Score(success=True, correctness=1.0))
    assert report.modes == []


def test_unknown_tool_and_bad_arguments_are_misuse_not_environment_errors() -> None:
    env = _weather_env()
    rec = env.recorder(_task())
    unknown = rec.call("shell", {"cmd": "ls"})
    bad = rec.call("weather", {"town": "X"})
    traj = rec.final("sunny")
    assert not unknown.ok and unknown.fault is None
    assert not bad.ok and bad.fault is None and "TypeError" in bad.output
    assert not traj.of_kind(StepKind.ERROR)
    report = analyze(_task(), traj, Score(success=True, correctness=1.0))
    assert report.modes == [FailureMode.TOOL_MISUSE]


def test_recorder_without_session_refuses_tool_calls() -> None:
    with pytest.raises(RuntimeError):
        Recorder().call("weather")


def test_lookup_normalizes_keys_and_has_a_default() -> None:
    tool = lookup_tool("search", {"Capital of  France": "Paris"})
    assert tool.fn(q="capital of france") == "Paris"
    assert tool.fn(q="capital of spain") == "no result"


def test_calculator_is_safe_and_formats_whole_numbers() -> None:
    calc = calculator_tool()
    assert calc.fn(expression="120 * 83.2") == "9984"
    assert calc.fn(expression="(2 + 3) / 4") == "1.25"
    with pytest.raises(ValueError):
        calc.fn(expression="__import__('os').system('ls')")
    with pytest.raises(ValueError):
        calc.fn(expression="9 ** 9999")


def test_specs_follow_the_openai_function_shape() -> None:
    env = _weather_env()
    (spec,) = env.specs(["weather"])
    assert spec["type"] == "function"
    assert spec["function"]["name"] == "weather"
    assert spec["function"]["parameters"]["required"] == ["city"]
