"""Regenerate every number, table, and sample report used in the academic documents.

    python academic/results/make_results.py

All runs use the offline baseline agents on the built-in reliability suite, so
the output is deterministic for a given seed and needs no model API.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

from relai import (
    FaultPolicy,
    RetryAgent,
    Variant,
    compare,
    load_suite,
    make_baseline,
    pareto_front,
    recommend,
    run_experiment,
    stress_test,
    success_ci,
    sweep,
    to_html,
)
from relai.baselines import solution_of
from relai.metrics import get_scorer
from relai.selfcheck import COLUMNS, planted_defect_check

OUT = Path(__file__).resolve().parent
SEED = 0
TRIALS = 5
RATE = 0.3
STRESS_RATES = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
STRESS_AGENTS = ["naive", "retry:1", "retry:3"]
LENGTH_TRIALS = 200


def main() -> None:
    suite = load_suite("reliability")
    scorer = get_scorer(suite.scorer)
    summary: dict[str, object] = {"seed": SEED, "trials": TRIALS, "timeout_rate": RATE}

    env = suite.env(FaultPolicy(timeout_rate=RATE), seed=SEED)
    comparison = run_experiment(
        suite.tasks,
        [Variant(spec, make_baseline(spec, env)) for spec in STRESS_AGENTS],
        scorer,
        trials=TRIALS,
        seed=SEED,
        name="naive vs retry",
        suite=suite.name,
    )
    rows = []
    for report in comparison.ranking():
        low, high = success_ci(report)
        counts = report.failure_counts()
        rows.append(
            {
                "variant": report.variant,
                "success": round(report.success_rate, 4),
                "ci_low": round(low, 4),
                "ci_high": round(high, 4),
                "pass_hat_k": round(report.pass_hat_k_value, 4),
                "consistency": round(report.consistency, 4),
                "cost_usd": round(report.mean_cost_usd, 6),
                "latency_ms": round(report.mean_step_latency_ms, 1),
                "recovery": round(report.mean_recovery_rate, 4),
                "steps": round(report.mean_horizon_steps, 2),
                **{f"n_{mode}": count for mode, count in counts.items()},
            }
        )
    _write_csv("comparison.csv", rows)
    paired = [compare(comparison.report_for("retry:3"), comparison.report_for(other))
              for other in ("retry:1", "naive")]
    summary["paired"] = [item.model_dump() | {"delta": item.delta} for item in paired]
    (OUT / "sample_report.html").write_text(to_html(comparison), encoding="utf-8")

    levels = stress_test(
        suite.tasks,
        lambda rate: [
            Variant(spec, make_baseline(spec, suite.env(FaultPolicy(timeout_rate=rate))))
            for spec in STRESS_AGENTS
        ],
        STRESS_RATES,
        scorer,
        trials=TRIALS,
        seed=SEED,
    )
    stress_rows = []
    for rate, experiment in levels:
        row: dict[str, object] = {"rate": rate}
        for spec in STRESS_AGENTS:
            report = experiment.report_for(spec)
            key = spec.replace(":", "")
            row[f"{key}_success"] = round(report.success_rate, 4)
            row[f"{key}_passk"] = round(report.pass_hat_k_value, 4)
        stress_rows.append(row)
    _write_csv("stress.csv", stress_rows)

    tuned = sweep(
        suite.tasks,
        lambda max_retries: RetryAgent(env, max_retries=max_retries),
        {"max_retries": [0, 1, 2, 3, 4]},
        scorer,
        trials=TRIALS,
        seed=SEED,
        suite=suite.name,
    )
    front = {report.variant for report in pareto_front(tuned.reports)}
    sweep_rows = [
        {
            "max_retries": report.config["max_retries"],
            "success": round(report.success_rate, 4),
            "pass_hat_k": round(report.pass_hat_k_value, 4),
            "cost_usd": round(report.mean_cost_usd, 6),
            "latency_ms": round(report.mean_step_latency_ms, 1),
            "horizon_flags": report.failure_counts()["horizon"],
            "recovery_flags": report.failure_counts()["recovery"],
            "pareto": int(report.variant in front),
        }
        for report in sorted(tuned.reports, key=lambda r: r.config["max_retries"])
    ]
    _write_csv("sweep.csv", sweep_rows)
    best = recommend(tuned.reports, min_success=0.95)
    summary["recommended_at_0.95"] = best.variant if best else None

    check = planted_defect_check(
        suite, faults=FaultPolicy(timeout_rate=RATE), trials=TRIALS, seed=SEED
    )
    _write_csv(
        "selfcheck.csv",
        [
            {
                "agent": agent,
                "planted": check.planted[agent] or "control",
                **row,
                "agreement": round(check.agreement(agent), 4),
            }
            for agent, row in check.matrix.items()
        ],
    )
    planted_modes = sorted({mode for mode in check.planted.values() if mode})
    summary["precision"] = {mode: check.precision(mode) for mode in planted_modes}
    summary["selfcheck_columns"] = COLUMNS

    summary["length_check"] = _length_check(suite, scorer)
    _write_csv("length_check.csv", summary["length_check"])

    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    _capture_cli()
    print(f"wrote results to {OUT}")


def _length_check(suite, scorer) -> list[dict[str, object]]:
    """Measured success by chain length against the closed form for independent faults.

    With timeout rate p, a task needing L calls succeeds for an agent with r
    retries per call with probability (1 - p^(r+1))^L.
    """
    rows = []
    by_length: dict[int, list] = {}
    for task in suite.tasks:
        calls = len(solution_of(task))
        if calls:
            by_length.setdefault(calls, []).append(task)
    env = suite.env(FaultPolicy(timeout_rate=RATE), seed=SEED)
    for retries in (0, 1):
        agent = RetryAgent(env, max_retries=retries, name=f"retry{retries}")
        for length, tasks in sorted(by_length.items()):
            report = run_experiment(
                tasks, [Variant(agent.name, agent)], scorer, trials=LENGTH_TRIALS, seed=SEED
            ).reports[0]
            rows.append(
                {
                    "retries": retries,
                    "calls": length,
                    "tasks": len(tasks),
                    "runs": report.n,
                    "measured": round(report.success_rate, 4),
                    "expected": round((1 - RATE ** (retries + 1)) ** length, 4),
                }
            )
    return rows


def _capture_cli() -> None:
    relai = [sys.executable, "-m", "relai"]
    commands = {
        "cli_run.txt": [*relai, "run", "reliability", "--agent", "naive", "--agent", "retry:1",
                        "--agent", "retry:3", "--trials", "5", "--timeout-rate", "0.3"],
        "cli_stress.txt": [*relai, "stress", "reliability", "--agent", "naive", "--agent",
                           "retry:1", "--agent", "retry:3", "--trials", "5"],
        "cli_sweep.txt": [*relai, "sweep", "reliability", "--param", "max_retries=0,1,2,3,4",
                          "--timeout-rate", "0.3", "--trials", "5", "--min-success", "0.95"],
        "cli_selfcheck.txt": [*relai, "selfcheck", "--trials", "5"],
        "cli_demo.txt": [*relai, "demo"],
    }
    for name, command in commands.items():
        shown = "relai " + " ".join(command[3:])
        output = subprocess.run(command, capture_output=True, text=True, check=True).stdout
        (OUT / name).write_text(f"$ {shown}\n{output}", encoding="utf-8")


def _write_csv(name: str, rows: list[dict[str, object]]) -> None:
    with (OUT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
