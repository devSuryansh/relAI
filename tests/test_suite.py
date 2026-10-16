import pytest

from relai.suite import Suite, builtin_suites, load_suite, save_suite


def test_builtin_suites_load_and_keep_shortcuts_in_metadata() -> None:
    assert {"demo", "reliability"} <= set(builtin_suites())
    suite = load_suite("reliability")
    assert len(suite.tasks) == 12
    refund = next(task for task in suite.tasks if task.id == "refund_in_inr")
    assert len(refund.metadata["solution"]) == 5
    assert refund.metadata["guess"] == "3000"
    assert refund.max_steps == 16


def test_suite_env_builds_tools_and_uses_default_faults() -> None:
    suite = load_suite("demo")
    env = suite.env()
    assert set(env.tools) == {"search", "weather"}
    assert env.faults.fail_first_n == 1
    assert env.faults.tools == ["weather"]


def test_save_and_reload_round_trip(tmp_path) -> None:
    suite = load_suite("reliability")
    for name in ("copy.yaml", "copy.json"):
        path = tmp_path / name
        save_suite(suite, path)
        again = load_suite(path)
        assert again.model_dump() == suite.model_dump()


def test_suite_rejects_undefined_tools_and_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="undefined tools"):
        Suite.model_validate(
            {"name": "x", "tasks": [{"id": "a", "prompt": "p", "allowed_tools": ["nope"]}]}
        )
    with pytest.raises(ValueError, match="duplicate"):
        Suite.model_validate(
            {"name": "x", "tasks": [{"id": "a", "prompt": "p"}, {"id": "a", "prompt": "q"}]}
        )


def test_unknown_suite_name_is_a_clear_error() -> None:
    with pytest.raises(FileNotFoundError, match="no suite"):
        load_suite("does-not-exist")
