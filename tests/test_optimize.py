import pytest

from relai.agents import FunctionAgent
from relai.baselines import RetryAgent
from relai.env import FaultPolicy
from relai.harness import evaluate
from relai.metrics import normalized_match
from relai.optimize import dominates, grid, pareto_front, parse_objective, recommend, sweep
from relai.suite import load_suite
from relai.types import Step, Task, Trajectory


def test_grid_is_the_ordered_cartesian_product() -> None:
    assert grid({"a": [1, 2], "b": ["x", "y"]}) == [
        {"a": 1, "b": "x"},
        {"a": 1, "b": "y"},
        {"a": 2, "b": "x"},
        {"a": 2, "b": "y"},
    ]
    assert grid({}) == [{}]


def _report(name: str, passes: int, cost: float):
    tasks = [Task(id=f"t{i}", prompt="q", expected="yes") for i in range(4)]

    def run(task: Task) -> Trajectory:
        ok = int(task.id[1:]) < passes
        return Trajectory(steps=[Step.final("yes" if ok else "no", cost_usd=cost)])

    return evaluate(FunctionAgent(name, run), tasks)


def test_pareto_front_drops_dominated_variants() -> None:
    cheap_weak = _report("cheap_weak", passes=2, cost=0.001)
    pricey_strong = _report("pricey_strong", passes=4, cost=0.004)
    pricey_weak = _report("pricey_weak", passes=2, cost=0.004)
    assert dominates(cheap_weak, pricey_weak)
    front = pareto_front([cheap_weak, pricey_strong, pricey_weak])
    assert [r.variant for r in front] == ["pricey_strong", "cheap_weak"]


def test_recommend_picks_the_cheapest_variant_that_meets_the_target() -> None:
    reports = [
        _report("a", passes=4, cost=0.004),
        _report("b", passes=4, cost=0.002),
        _report("c", passes=3, cost=0.001),
    ]
    assert recommend(reports, min_success=1.0).variant == "b"
    assert recommend(reports, min_success=0.75).variant == "c"
    assert recommend(reports, min_success=1.1) is None


def test_parse_objective() -> None:
    assert parse_objective("pass_hat_k_value:max") == ("pass_hat_k_value", True)
    with pytest.raises(ValueError):
        parse_objective("success_rate")


def test_retry_sweep_trades_cost_for_reliability_under_faults() -> None:
    suite = load_suite("reliability")
    env = suite.env(FaultPolicy(timeout_rate=0.3))
    experiment = sweep(
        suite.tasks,
        lambda max_retries: RetryAgent(env, max_retries=max_retries),
        {"max_retries": [0, 1, 3]},
        normalized_match,
        trials=3,
    )
    by_name = {r.variant: r for r in experiment.reports}
    none, one, three = (by_name[f"max_retries={n}"] for n in (0, 1, 3))
    assert none.success_rate < one.success_rate < three.success_rate
    assert none.mean_cost_usd < one.mean_cost_usd < three.mean_cost_usd
    assert experiment.ranking()[0].variant == "max_retries=3"
    assert {r.variant for r in pareto_front(experiment.reports)} == set(by_name)
