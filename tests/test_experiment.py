from relai.demo import DEMO_TASKS, brittle_agent, resilient_agent
from relai.experiment import Variant, run_experiment


def test_experiment_ranks_resilient_above_brittle() -> None:
    report = run_experiment(
        DEMO_TASKS,
        [
            Variant("brittle", brittle_agent()),
            Variant("resilient", resilient_agent()),
        ],
    )
    ranking = report.ranking()
    assert ranking[0].variant == "resilient"
    assert ranking[0].success_rate == 1.0
    assert ranking[1].variant == "brittle"
    assert ranking[1].success_rate < 1.0
    summaries = report.summary()
    assert summaries[0]["variant"] == "resilient"
