from relai.agents import FunctionAgent
from relai.harness import evaluate
from relai.types import Step, Task, Trajectory


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
