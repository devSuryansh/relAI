import json

from relai.cli import main


def test_demo_prints_both_variants(capsys) -> None:
    assert main(["demo"]) == 0
    out = capsys.readouterr().out
    assert "brittle" in out
    assert "resilient" in out
    assert "success" in out


def test_demo_json_summaries(capsys) -> None:
    assert main(["demo", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    names = {row["variant"] for row in payload}
    assert names == {"brittle", "resilient"}


def test_help_without_command(capsys) -> None:
    assert main([]) == 0
    assert "evaluate" in capsys.readouterr().out.lower()


def test_suites_lists_builtins(capsys) -> None:
    assert main(["suites"]) == 0
    out = capsys.readouterr().out
    assert "demo" in out and "reliability" in out


def test_run_with_faults_trials_and_every_output(tmp_path, capsys) -> None:
    db, html, md = tmp_path / "runs.db", tmp_path / "r.html", tmp_path / "r.md"
    code = main(
        [
            "run",
            "reliability",
            "--agent",
            "naive",
            "--agent",
            "retry:2",
            "--trials",
            "2",
            "--timeout-rate",
            "0.3",
            "--store",
            str(db),
            "--html",
            str(html),
            "--markdown",
            str(md),
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "pass^k" in out and "McNemar" in out
    assert html.read_text().startswith("<!doctype html>")
    assert "retry:2" in md.read_text()

    assert main(["report", str(db), "--list"]) == 0
    assert "variants=2" in capsys.readouterr().out
    assert main(["report", str(db)]) == 0
    assert "retry:2" in capsys.readouterr().out


def test_run_json_is_ranked(capsys) -> None:
    assert main(["run", "demo", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [row["variant"] for row in payload] == ["retry", "naive"]
    assert payload[0]["success_rate"] == 1.0


def test_sweep_recommends_a_setting(capsys) -> None:
    code = main(
        [
            "sweep",
            "reliability",
            "--param",
            "max_retries=0,2",
            "--timeout-rate",
            "0.3",
            "--trials",
            "2",
            "--min-success",
            "0.9",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "Pareto front" in out
    assert "Recommended: max_retries=2" in out


def test_stress_json_curves_fall_as_faults_rise(capsys) -> None:
    code = main(["stress", "reliability", "--agent", "naive", "--rates", "0,0.5", "--json"])
    assert code == 0
    curves = json.loads(capsys.readouterr().out)["success_rate"]
    assert curves["naive"][0] == 1.0
    assert curves["naive"][1] < curves["naive"][0]


def test_selfcheck_table(capsys) -> None:
    assert main(["selfcheck", "--trials", "1"]) == 0
    out = capsys.readouterr().out
    assert "precision by mode" in out
    assert "(control)" in out


def test_bad_agent_spec_is_a_clean_error(capsys) -> None:
    assert main(["run", "demo", "--agent", "nonsense"]) == 2
    assert "neither a baseline" in capsys.readouterr().err
