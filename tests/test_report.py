from relai.agents import ScriptedAgent
from relai.demo import DEMO_TASKS, brittle_agent, resilient_agent
from relai.experiment import Variant, run_experiment
from relai.report import summary_rows, to_html, to_markdown
from relai.types import Step, Trajectory


def _experiment():
    return run_experiment(
        DEMO_TASKS,
        [Variant("brittle", brittle_agent()), Variant("resilient", resilient_agent())],
        name="demo",
    )


def test_summary_rows_are_ranked_with_intervals() -> None:
    rows = summary_rows(_experiment())
    assert [row["variant"] for row in rows] == ["resilient", "brittle"]
    low, high = rows[0]["ci"]
    assert 0.0 <= low <= rows[0]["success"] <= high <= 1.0


def test_markdown_has_ranking_and_failure_tables() -> None:
    text = to_markdown(_experiment())
    assert text.startswith("# Agent Reliability Lab: demo")
    assert "| 1 | resilient" in text
    assert "## Failure modes" in text
    assert "McNemar" in text


def test_html_is_standalone_and_escapes_trajectory_text() -> None:
    sneaky = ScriptedAgent(
        "sneaky", {}, default=Trajectory(steps=[Step.final("<script>alert(1)</script>")])
    )
    experiment = run_experiment(DEMO_TASKS, [Variant("sneaky", sneaky)], name="xss")
    html = to_html(experiment)
    assert html.startswith("<!doctype html>")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "Failure modes" in html
