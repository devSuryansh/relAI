import pytest

from relai.agents import FunctionAgent
from relai.env import TRIAL_KEY
from relai.harness import evaluate
from relai.stats import bootstrap_ci, compare, mcnemar_exact, success_ci, wilson_interval
from relai.types import Step, Task, Trajectory


def test_wilson_interval_matches_the_textbook_value() -> None:
    low, high = wilson_interval(8, 10)
    assert low == pytest.approx(0.4902, abs=1e-4)
    assert high == pytest.approx(0.9433, abs=1e-4)
    assert wilson_interval(0, 0) == (0.0, 1.0)
    assert wilson_interval(10, 10)[1] == 1.0


def test_bootstrap_is_seeded_and_brackets_the_mean() -> None:
    values = [0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 0.0]
    first = bootstrap_ci(values, seed=3)
    assert first == bootstrap_ci(values, seed=3)
    assert first[0] <= sum(values) / len(values) <= first[1]


def test_mcnemar_exact_p_values() -> None:
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(6, 0) == pytest.approx(2 / 64)
    assert mcnemar_exact(3, 3) == 1.0


def _agent(name: str, passes: set[str]) -> FunctionAgent:
    def run(task: Task) -> Trajectory:
        return Trajectory(steps=[Step.final("yes" if task.id in passes else "no")])

    return FunctionAgent(name, run)


def test_compare_pairs_runs_by_task_and_trial() -> None:
    tasks = [Task(id=f"t{i}", prompt="q", expected="yes") for i in range(8)]
    strong = evaluate(_agent("strong", {t.id for t in tasks}), tasks)
    weak = evaluate(_agent("weak", {"t0", "t1"}), tasks)
    result = compare(strong, weak)
    assert (result.pairs, result.both, result.a_only, result.b_only) == (8, 2, 6, 0)
    assert result.delta == pytest.approx(0.75)
    assert result.significant()


def test_success_ci_resamples_tasks_when_there_are_trials() -> None:
    def run(task: Task) -> Trajectory:
        ok = task.id == "a" or task.metadata[TRIAL_KEY] == 0
        return Trajectory(steps=[Step.final("yes" if ok else "no")])

    tasks = [Task(id=name, prompt="q", expected="yes") for name in ("a", "b", "c")]
    report = evaluate(FunctionAgent("mixed", run), tasks, trials=3)
    low, high = success_ci(report, seed=1)
    assert low <= report.success_rate <= high
    assert success_ci(report, seed=1) == (low, high)
