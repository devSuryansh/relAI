import pytest

from relai.demo import DEMO_TASKS, brittle_agent, resilient_agent
from relai.experiment import Variant, run_experiment
from relai.store import RunStore, experiment_from_results, read_jsonl, write_jsonl


@pytest.fixture
def experiment():
    return run_experiment(
        DEMO_TASKS,
        [
            Variant("brittle", brittle_agent(), config={"retries": 0}),
            Variant("resilient", resilient_agent(), config={"retries": 1}),
        ],
        trials=2,
        name="demo",
        suite="scripted",
    )


def test_store_round_trip_keeps_results_and_metadata(tmp_path, experiment) -> None:
    path = tmp_path / "runs.db"
    with RunStore(path) as store:
        first = store.save(experiment)
        second = store.save(experiment)
        assert second == first + 1
        listed = store.experiments()
        assert [item.runs for item in listed] == [12, 12]
    with RunStore(path) as store:
        loaded = store.load(first)
        latest = store.load()
    assert loaded.name == "demo" and loaded.suite == "scripted"
    assert loaded.summary() == experiment.summary()
    assert latest.summary() == experiment.summary()
    assert loaded.report_for("resilient").config == {"retries": 1}


def test_failure_counts_come_from_sql(tmp_path, experiment) -> None:
    with RunStore(tmp_path / "runs.db") as store:
        experiment_id = store.save(experiment)
        counts = store.failure_counts(experiment_id)
        steps = store.conn.execute("SELECT COUNT(*) FROM steps").fetchone()[0]
    assert counts == {"brittle": {"planning": 2, "recovery": 2}}
    expected_steps = sum(
        len(result.trajectory.steps) for report in experiment.reports for result in report.results
    )
    assert steps == expected_steps


def test_missing_experiment_is_a_lookup_error(tmp_path) -> None:
    with RunStore(tmp_path / "empty.db") as store, pytest.raises(LookupError):
        store.load()


def test_jsonl_round_trip(tmp_path, experiment) -> None:
    results = [result for report in experiment.reports for result in report.results]
    path = tmp_path / "runs.jsonl"
    assert write_jsonl(results, path) == len(results)
    again = experiment_from_results(read_jsonl(path))
    assert {r.variant for r in again.reports} == {"brittle", "resilient"}
    assert again.report_for("brittle").trials == 2
    assert again.report_for("brittle").success_rate == experiment.report_for(
        "brittle"
    ).success_rate
