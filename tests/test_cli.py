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
    assert "evaluate" in capsys.readouterr().out.lower() or "relai" in capsys.readouterr().out
