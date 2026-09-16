from relai.analysis import analyze
from relai.types import FailureMode, Score, Step, Task, Trajectory


def _failed() -> Score:
    return Score(success=False, correctness=0.0)


def _ok() -> Score:
    return Score(success=True, correctness=1.0)


def test_planning_failure_when_required_tools_are_skipped() -> None:
    task = Task(
        id="lookup",
        prompt="search",
        expected="Paris",
        allowed_tools=["search"],
        tags=["requires_tools"],
    )
    traj = Trajectory(steps=[Step.plan("guess"), Step.final("Lyon")])
    report = analyze(task, traj, _failed())
    assert FailureMode.PLANNING in report.modes
    assert report.root_cause == FailureMode.PLANNING


def test_tool_misuse_for_disallowed_tool() -> None:
    task = Task(id="t", prompt="p", expected="x", allowed_tools=["search"])
    traj = Trajectory(
        steps=[
            Step.tool_call("shell", {"cmd": "rm"}),
            Step.observation("no"),
            Step.final("x"),
        ]
    )
    report = analyze(task, traj, _ok())
    assert FailureMode.TOOL_MISUSE in report.modes


def test_timeout_is_not_tool_misuse() -> None:
    task = Task(id="t", prompt="p", expected="sunny", allowed_tools=["weather"])
    traj = Trajectory(
        steps=[
            Step.tool_call("weather", {"city": "X"}, ok=False),
            Step.error("timeout"),
            Step.final("unknown"),
        ]
    )
    report = analyze(task, traj, _failed())
    assert FailureMode.TOOL_MISUSE not in report.modes
    assert FailureMode.RECOVERY in report.modes
    assert report.recovery_effectiveness == 0.0


def test_context_failure_repeats_tool_after_observation() -> None:
    task = Task(id="t", prompt="p", expected="b")
    traj = Trajectory(
        steps=[
            Step.tool_call("search", {"q": "a"}),
            Step.observation("try b instead"),
            Step.tool_call("search", {"q": "a"}),
            Step.final("a"),
        ]
    )
    report = analyze(task, traj, _failed())
    assert FailureMode.CONTEXT in report.modes
    assert report.root_cause == FailureMode.CONTEXT


def test_successful_recovery_is_not_a_failure_mode() -> None:
    task = Task(id="t", prompt="p", expected="sunny", allowed_tools=["weather"])
    traj = Trajectory(
        steps=[
            Step.tool_call("weather", {"city": "X"}, ok=False),
            Step.error("timeout"),
            Step.recovery("retry"),
            Step.tool_call("weather", {"city": "X"}, ok=True),
            Step.observation("sunny"),
            Step.final("sunny"),
        ]
    )
    report = analyze(task, traj, _ok())
    assert report.modes == []
    assert report.recovery_effectiveness == 1.0
    assert not report.unclassified


def test_unclassified_failure() -> None:
    task = Task(id="t", prompt="p", expected="42", allowed_tools=["calc"])
    traj = Trajectory(
        steps=[
            Step.plan("use calc"),
            Step.tool_call("calc", {"expr": "6*7"}, ok=True),
            Step.observation("42"),
            Step.final("41"),
        ]
    )
    report = analyze(task, traj, _failed())
    assert report.unclassified
    assert report.modes == []
