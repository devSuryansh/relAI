"""Render experiments as Markdown or as a standalone HTML page."""

from __future__ import annotations

from html import escape
from typing import Any

from relai.experiment import ExperimentReport
from relai.harness import EvalReport
from relai.optimize import pareto_front
from relai.stats import compare, success_ci
from relai.types import FailureMode, RunResult

MODES = [mode.value for mode in FailureMode] + ["unclassified"]


def summary_rows(experiment: ExperimentReport) -> list[dict[str, Any]]:
    """One display row per variant in rank order, shared by every renderer."""
    front = {id(report) for report in pareto_front(experiment.reports)}
    rows = []
    for rank, report in enumerate(experiment.ranking(), start=1):
        low, high = success_ci(report)
        rows.append(
            {
                "rank": rank,
                "variant": report.variant,
                "pareto": id(report) in front,
                "success": report.success_rate,
                "ci": (low, high),
                "trials": report.trials,
                "pass_hat_k": report.pass_hat_k_value,
                "consistency": report.consistency,
                "cost": report.mean_cost_usd,
                "latency": report.mean_step_latency_ms,
                "wall": report.mean_latency_ms,
                "recovery": report.mean_recovery_rate,
                "horizon": report.mean_horizon_steps,
                "failures": report.failure_counts(),
                "root_causes": report.root_cause_counts(),
            }
        )
    return rows


def to_markdown(experiment: ExperimentReport, *, title: str | None = None) -> str:
    rows = summary_rows(experiment)
    lines = [f"# {title or _title(experiment)}", ""]
    lines.append(_context_line(experiment))
    lines += [
        "",
        "| rank | variant | success (95% CI) | pass^k | consistency | cost | latency "
        "| recovery | horizon |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        star = " *" if row["pareto"] else ""
        lines.append(
            f"| {row['rank']} | {row['variant']}{star} | {_ci_text(row)} "
            f"| {row['pass_hat_k']:.2f} | {row['consistency']:.2f} | ${row['cost']:.4f} "
            f"| {row['latency']:.0f} ms | {row['recovery']:.2f} | {row['horizon']:.1f} |"
        )
    lines += ["", "\\* on the Pareto front for success, cost, and latency.", ""]
    lines += ["## Failure modes", ""]
    lines.append("| variant | " + " | ".join(MODES) + " |")
    lines.append("| --- |" + " --- |" * len(MODES))
    for row in rows:
        counts = row["failures"]
        lines.append(f"| {row['variant']} | " + " | ".join(str(counts[m]) for m in MODES) + " |")
    paired = _paired_text(experiment)
    if paired:
        lines += ["", "## Paired comparison", "", paired]
    return "\n".join(lines) + "\n"


def to_html(experiment: ExperimentReport, *, title: str | None = None) -> str:
    rows = summary_rows(experiment)
    heading = escape(title or _title(experiment))
    parts = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        f"<title>{heading}</title>",
        f"<style>{_CSS}</style></head><body>",
        f"<h1>{heading}</h1>",
        f'<p class="muted">{escape(_context_line(experiment))}</p>',
        "<h2>Ranking</h2>",
        _summary_table(rows),
        '<p class="muted">&#9733; marks variants on the Pareto front: no other variant is at '
        "least as good on success, cost, and latency while better on one of them.</p>",
    ]
    paired = _paired_text(experiment)
    if paired:
        parts += ["<h2>Paired comparison</h2>", f"<p>{escape(paired)}</p>"]
    parts += ["<h2>Failure modes</h2>", _failure_bars(rows)]
    parts.append("<h2>Runs</h2>")
    for report in experiment.ranking():
        parts.append(_runs_section(report))
    parts.append("</body></html>")
    return "\n".join(parts) + "\n"


def _title(experiment: ExperimentReport) -> str:
    return f"Agent Reliability Lab: {experiment.name}"


def _context_line(experiment: ExperimentReport) -> str:
    reports = experiment.reports
    trials = max((report.trials for report in reports), default=1)
    tasks = len(reports[0].by_task()) if reports else 0
    seed = reports[0].seed if reports else 0
    suite = experiment.suite or "custom tasks"
    return (
        f"Suite: {suite}. Variants: {len(reports)}. Tasks: {tasks}. "
        f"Trials per task: {trials}. Seed: {seed}."
    )


def _ci_text(row: dict[str, Any]) -> str:
    low, high = row["ci"]
    return f"{row['success']:.2f} [{low:.2f}, {high:.2f}]"


def _paired_text(experiment: ExperimentReport) -> str:
    ranked = experiment.ranking()
    if len(ranked) < 2:
        return ""
    best, runner_up = ranked[0], ranked[1]
    try:
        result = compare(best, runner_up)
    except ValueError:
        return ""
    verdict = "a significant" if result.significant() else "no significant"
    return (
        f"{best.variant} vs {runner_up.variant} on {result.pairs} paired runs: "
        f"{result.a_only} won only by {best.variant}, {result.b_only} only by "
        f"{runner_up.variant}. Exact McNemar p = {result.p_value:.4f}, so {verdict} "
        "difference at the 0.05 level."
    )


def _summary_table(rows: list[dict[str, Any]]) -> str:
    head = (
        "<tr><th>#</th><th>variant</th><th>success [95% CI]</th><th>pass^k</th>"
        "<th>consistency</th><th>cost / run</th><th>latency</th><th>wall</th>"
        "<th>recovery</th><th>horizon</th><th>top root cause</th></tr>"
    )
    body = []
    for row in rows:
        star = " &#9733;" if row["pareto"] else ""
        causes = {k: v for k, v in row["root_causes"].items() if v}
        top = max(causes, key=causes.get) if causes else "none"
        body.append(
            f"<tr><td>{row['rank']}</td><td><b>{escape(row['variant'])}</b>{star}</td>"
            f"<td>{_ci_text(row)}</td><td>{row['pass_hat_k']:.2f}</td>"
            f"<td>{row['consistency']:.2f}</td><td>${row['cost']:.4f}</td>"
            f"<td>{row['latency']:.0f} ms</td><td>{row['wall']:.2f} ms</td>"
            f"<td>{row['recovery']:.2f}</td><td>{row['horizon']:.1f}</td>"
            f"<td>{escape(top)}</td></tr>"
        )
    return f"<table>{head}{''.join(body)}</table>"


def _failure_bars(rows: list[dict[str, Any]]) -> str:
    peak = max((count for row in rows for count in row["failures"].values()), default=0) or 1
    blocks = []
    for row in rows:
        bars = []
        for mode in MODES:
            count = row["failures"][mode]
            width = 100 * count / peak
            bars.append(
                f'<div class="bar"><span class="label">{mode}</span>'
                f'<span class="fill m-{mode}" style="width:{width:.1f}%"></span>'
                f'<span class="count">{count}</span></div>'
            )
        blocks.append(
            f'<div class="card"><h3>{escape(row["variant"])}</h3>{"".join(bars)}</div>'
        )
    return f'<div class="grid">{"".join(blocks)}</div>'


def _runs_section(report: EvalReport) -> str:
    items = [f"<h3>{escape(report.variant)}</h3>"]
    for result in report.results:
        items.append(_run_details(result))
    return "".join(items)


def _run_details(result: RunResult) -> str:
    ok = result.metrics.success
    status = '<span class="ok">pass</span>' if ok else '<span class="bad">fail</span>'
    failures = result.failures
    modes = ", ".join(mode.value for mode in failures.modes) or "none"
    if failures.unclassified:
        modes = "unclassified"
    summary = (
        f"{status} {escape(result.task_id)} (trial {result.trial}), "
        f"modes: {escape(modes)}, root cause: "
        f"{escape(failures.root_cause.value if failures.root_cause else 'none')}"
    )
    steps = "".join(
        f"<tr><td>{idx}</td><td>{escape(step.kind.value)}</td>"
        f"<td>{escape(step.tool_name or '')}</td>"
        f"<td>{escape(_ok_text(step.tool_ok))}</td>"
        f"<td>{escape(step.content)}</td><td>{step.latency_ms:.0f}</td>"
        f"<td>{step.cost_usd:.4f}</td></tr>"
        for idx, step in enumerate(result.trajectory.steps)
    )
    evidence = "".join(f"<li>{escape(item)}</li>" for item in failures.evidence)
    return (
        f"<details><summary>{summary}</summary>"
        f"<p class='muted'>{escape(result.score.rationale)}</p>"
        "<table><tr><th>#</th><th>kind</th><th>tool</th><th>ok</th><th>content</th>"
        f"<th>ms</th><th>$</th></tr>{steps}</table>"
        f"{f'<ul>{evidence}</ul>' if evidence else ''}</details>"
    )


def _ok_text(ok: bool | None) -> str:
    if ok is None:
        return ""
    return "yes" if ok else "no"


_CSS = """
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:2rem auto;
max-width:1100px;padding:0 1rem;color:#1f2933;line-height:1.45}
h1{margin-bottom:.2rem}h2{margin-top:2rem;border-bottom:1px solid #d9e2ec;padding-bottom:.3rem}
table{border-collapse:collapse;width:100%;font-size:.9rem;margin:.6rem 0}
th,td{border:1px solid #d9e2ec;padding:.35rem .5rem;text-align:left;vertical-align:top}
th{background:#f0f4f8}.muted{color:#627d98;font-size:.9rem}
.ok{color:#0b7a3e;font-weight:600}.bad{color:#b42318;font-weight:600}
details{border:1px solid #d9e2ec;border-radius:6px;padding:.4rem .7rem;margin:.35rem 0}
summary{cursor:pointer}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:1rem}
.card{border:1px solid #d9e2ec;border-radius:8px;padding:.6rem .9rem}
.card h3{margin:.2rem 0 .5rem}
.bar{display:grid;grid-template-columns:110px 1fr 32px;align-items:center;gap:.4rem;
font-size:.85rem;margin:.2rem 0}
.fill{display:block;height:.8rem;border-radius:3px;background:#9fb3c8;min-width:2px}
.m-planning{background:#f0b429}.m-tool_misuse{background:#e12d39}.m-context{background:#8719e0}
.m-recovery{background:#2186eb}.m-horizon{background:#0c6b58}.m-unclassified{background:#829ab1}
.count{text-align:right}
"""
