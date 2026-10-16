import pytest

from relai.agents import FunctionAgent
from relai.env import SEED_KEY, TRIAL_KEY
from relai.harness import evaluate
from relai.types import FailureMode, Step, Task, Trajectory


def test_evaluate_scores_each_task_and_aggregates() -> None:
    tasks = [
        Task(id="ok", prompt="q", expected="yes"),
        Task(id="bad", prompt="q", expected="yes"),
    ]

    def run(task: Task) -> Trajectory:
        answer = "yes" if task.id == "ok" else "no"
        return Trajectory(steps=[Step.final(answer, cost_usd=0.01)])

    report = evaluate(FunctionAgent("stub", run), tasks)
    assert report.n == 2
    assert report.success_rate == 0.5
    assert report.mean_cost_usd == 0.01
    assert report.results[0].metrics.success
    assert not report.results[1].metrics.success
    assert report.results[1].failures.root_cause is not None


def _flaky(task: Task) -> Trajectory:
    """Passes 'always' on every trial, 'never' on none, 'half' on even trials."""
    trial = task.metadata[TRIAL_KEY]
    passed = task.id == "always" or (task.id == "half" and trial % 2 == 0)
    return Trajectory(steps=[Step.final("yes" if passed else "no")])


def test_trials_feed_pass_at_k_pass_hat_k_and_consistency() -> None:
    tasks = [Task(id=name, prompt="q", expected="yes") for name in ("always", "never", "half")]
    report = evaluate(FunctionAgent("flaky", _flaky), tasks, trials=4)
    assert report.n == 12
    assert report.trials == 4
    assert [r.trial for r in report.by_task()["half"]] == [0, 1, 2, 3]
    assert report.success_rate == pytest.approx(6 / 12)
    # half passes 2 of 4: pass@2 = 1 - C(2,2)/C(4,2) = 5/6, pass^2 = C(2,2)/C(4,2) = 1/6
    assert report.pass_at_k(2) == pytest.approx((1 + 0 + 5 / 6) / 3)
    assert report.pass_hat_k(2) == pytest.approx((1 + 0 + 1 / 6) / 3)
    assert report.pass_hat_k(4) == pytest.approx(1 / 3)
    assert report.consistency == pytest.approx(2 / 3)
    with pytest.raises(ValueError):
        report.pass_hat_k(5)


def test_trial_and_seed_reach_the_agent_without_changing_the_task() -> None:
    seen: list[tuple[int, int]] = []

    def run(task: Task) -> Trajectory:
        seen.append((task.metadata[TRIAL_KEY], task.metadata[SEED_KEY]))
        return Trajectory(steps=[Step.final("x")])

    task = Task(id="t", prompt="q", expected="x")
    evaluate(FunctionAgent("probe", run), [task], trials=2, seed=9)
    assert seen == [(0, 9), (1, 9)]
    assert task.metadata == {}


def test_a_crashing_agent_becomes_a_failed_run() -> None:
    def run(task: Task) -> Trajectory:
        raise RuntimeError("model endpoint unreachable")

    report = evaluate(FunctionAgent("crashy", run), [Task(id="t", prompt="q", expected="x")])
    (result,) = report.results
    assert not result.metrics.success
    assert result.trajectory.metadata["crashed"]
    assert "model endpoint unreachable" in result.trajectory.steps[0].content
    assert FailureMode.HORIZON in result.failures.modes


def test_trials_must_be_positive() -> None:
    with pytest.raises(ValueError):
        evaluate(FunctionAgent("x", _flaky), [], trials=0)
