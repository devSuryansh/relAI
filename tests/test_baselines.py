import pytest

from relai.baselines import BASELINES, RetryAgent, make_baseline
from relai.env import FaultPolicy
from relai.harness import evaluate
from relai.metrics import normalized_match
from relai.selfcheck import planted_defect_check
from relai.suite import load_suite
from relai.types import FailureMode


@pytest.fixture
def suite():
    return load_suite("reliability")


def test_naive_agent_solves_every_task_without_faults(suite) -> None:
    agent = make_baseline("naive", suite.env())
    report = evaluate(agent, suite.tasks, normalized_match)
    assert report.success_rate == 1.0
    assert report.failure_counts()["recovery"] == 0


@pytest.mark.parametrize(
    ("spec", "mode"),
    [
        ("naive", FailureMode.RECOVERY),
        ("guessing", FailureMode.PLANNING),
        ("looping", FailureMode.CONTEXT),
        ("careless", FailureMode.TOOL_MISUSE),
    ],
)
def test_each_planted_defect_is_diagnosed(suite, spec, mode) -> None:
    env = suite.env(FaultPolicy(fail_first_n=1))
    report = evaluate(make_baseline(spec, env), suite.tasks, normalized_match)
    causes = report.root_cause_counts()
    assert max(causes, key=causes.get) == mode.value


def test_retry_agent_recovers_where_naive_gives_up(suite) -> None:
    env = suite.env(FaultPolicy(fail_first_n=1))
    naive = evaluate(make_baseline("naive", env), suite.tasks, normalized_match)
    retry = evaluate(RetryAgent(env, max_retries=1), suite.tasks, normalized_match)
    assert naive.success_rate < 0.2
    assert retry.success_rate == 1.0
    assert retry.mean_recovery_rate == 1.0


def test_make_baseline_parses_positional_and_keyword_settings(suite) -> None:
    env = suite.env()
    retry = make_baseline("retry:3", env)
    assert isinstance(retry, RetryAgent) and retry.max_retries == 3
    assert retry.name == "retry:3"
    tuned = make_baseline("retry:max_retries=1,backoff_ms=250", env)
    assert (tuned.max_retries, tuned.backoff_ms) == (1, 250)
    assert make_baseline("looping:4", env).repeats == 4
    assert make_baseline("naive", env).name == "naive"
    with pytest.raises(ValueError, match="unknown baseline"):
        make_baseline("genius", env)
    with pytest.raises(ValueError, match="positional"):
        make_baseline("guessing:2", env)


def test_planted_defect_check_matches_every_planted_mode(suite) -> None:
    check = planted_defect_check(suite, faults=FaultPolicy(timeout_rate=0.3), trials=2)
    assert set(check.matrix) == set(BASELINES)
    for agent, planted in check.planted.items():
        if planted is not None:
            assert check.agreement(agent) >= 0.95
            assert check.precision(planted) >= 0.95
