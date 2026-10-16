"""Persist experiments in SQLite and exchange run results as JSON Lines."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from relai.experiment import ExperimentReport
from relai.harness import EvalReport
from relai.types import RunResult

SCHEMA = """
CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    suite TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    trials INTEGER NOT NULL,
    seed INTEGER NOT NULL,
    config_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE (experiment_id, name)
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id INTEGER NOT NULL REFERENCES variants(id) ON DELETE CASCADE,
    task_id TEXT NOT NULL,
    trial INTEGER NOT NULL,
    success INTEGER NOT NULL,
    correctness REAL NOT NULL,
    cost_usd REAL NOT NULL,
    latency_ms REAL NOT NULL,
    step_latency_ms REAL NOT NULL,
    tokens INTEGER NOT NULL,
    tool_calls INTEGER NOT NULL,
    recovery_rate REAL NOT NULL,
    horizon_steps INTEGER NOT NULL,
    root_cause TEXT,
    unclassified INTEGER NOT NULL,
    result_json TEXT NOT NULL,
    UNIQUE (variant_id, task_id, trial)
);
CREATE TABLE IF NOT EXISTS steps (
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    idx INTEGER NOT NULL,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    tool_name TEXT,
    tool_ok INTEGER,
    latency_ms REAL NOT NULL,
    cost_usd REAL NOT NULL,
    PRIMARY KEY (run_id, idx)
);
CREATE TABLE IF NOT EXISTS failures (
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    mode TEXT NOT NULL,
    PRIMARY KEY (run_id, mode)
);
"""


class StoredExperiment(BaseModel):
    id: int
    name: str
    suite: str
    created_at: str
    variants: int
    runs: int


class RunStore:
    """SQLite store of experiments, variants, runs, steps, and failure modes."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)

    def __enter__(self) -> RunStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self.conn.close()

    def save(self, experiment: ExperimentReport) -> int:
        """Store a whole experiment in one transaction and return its id."""
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO experiments (name, suite, created_at) VALUES (?, ?, ?)",
                (
                    experiment.name,
                    experiment.suite,
                    datetime.now(UTC).isoformat(timespec="seconds"),
                ),
            )
            experiment_id = _rowid(cur)
            for report in experiment.reports:
                self._save_variant(experiment_id, report)
        return experiment_id

    def experiments(self) -> list[StoredExperiment]:
        rows = self.conn.execute(
            """
            SELECT e.id, e.name, e.suite, e.created_at,
                   COUNT(DISTINCT v.id), COUNT(r.id)
            FROM experiments e
            LEFT JOIN variants v ON v.experiment_id = e.id
            LEFT JOIN runs r ON r.variant_id = v.id
            GROUP BY e.id ORDER BY e.id
            """
        ).fetchall()
        return [
            StoredExperiment(
                id=row[0],
                name=row[1],
                suite=row[2],
                created_at=row[3],
                variants=row[4],
                runs=row[5],
            )
            for row in rows
        ]

    def load(self, experiment_id: int | None = None) -> ExperimentReport:
        """Rebuild an experiment, the most recent one when no id is given."""
        if experiment_id is None:
            row = self.conn.execute("SELECT MAX(id) FROM experiments").fetchone()
            experiment_id = row[0] if row else None
        head = self.conn.execute(
            "SELECT name, suite FROM experiments WHERE id = ?", (experiment_id,)
        ).fetchone()
        if experiment_id is None or head is None:
            raise LookupError(f"no experiment {experiment_id!r} in {self.path}")
        reports = []
        variants = self.conn.execute(
            "SELECT id, name, trials, seed, config_json FROM variants "
            "WHERE experiment_id = ? ORDER BY id",
            (experiment_id,),
        ).fetchall()
        for variant_id, name, trials, seed, config_json in variants:
            results = [
                RunResult.model_validate_json(payload)
                for (payload,) in self.conn.execute(
                    "SELECT result_json FROM runs WHERE variant_id = ? ORDER BY id",
                    (variant_id,),
                )
            ]
            reports.append(
                EvalReport(
                    variant=name,
                    trials=trials,
                    seed=seed,
                    config=json.loads(config_json),
                    results=results,
                )
            )
        return ExperimentReport(name=head[0], suite=head[1], reports=reports)

    def failure_counts(self, experiment_id: int) -> dict[str, dict[str, int]]:
        """Failure-mode counts per variant, computed in SQL."""
        counts: dict[str, dict[str, int]] = {}
        rows = self.conn.execute(
            """
            SELECT v.name, f.mode, COUNT(*)
            FROM failures f
            JOIN runs r ON r.id = f.run_id
            JOIN variants v ON v.id = r.variant_id
            WHERE v.experiment_id = ?
            GROUP BY v.name, f.mode
            """,
            (experiment_id,),
        )
        for variant, mode, count in rows:
            counts.setdefault(variant, {})[mode] = count
        return counts

    def _save_variant(self, experiment_id: int, report: EvalReport) -> None:
        cur = self.conn.execute(
            "INSERT INTO variants (experiment_id, name, trials, seed, config_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                experiment_id,
                report.variant,
                report.trials,
                report.seed,
                json.dumps(report.config, default=str),
            ),
        )
        variant_id = _rowid(cur)
        for result in report.results:
            metrics = result.metrics
            failures = result.failures
            run = self.conn.execute(
                """
                INSERT INTO runs (
                    variant_id, task_id, trial, success, correctness, cost_usd,
                    latency_ms, step_latency_ms, tokens, tool_calls, recovery_rate,
                    horizon_steps, root_cause, unclassified, result_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    variant_id,
                    result.task_id,
                    result.trial,
                    int(metrics.success),
                    metrics.correctness,
                    metrics.cost_usd,
                    metrics.latency_ms,
                    metrics.step_latency_ms,
                    metrics.tokens.total,
                    metrics.tool_calls,
                    metrics.recovery_rate,
                    metrics.horizon_steps,
                    failures.root_cause.value if failures.root_cause else None,
                    int(failures.unclassified),
                    result.model_dump_json(),
                ),
            )
            run_id = _rowid(run)
            self.conn.executemany(
                "INSERT INTO steps (run_id, idx, kind, content, tool_name, tool_ok, "
                "latency_ms, cost_usd) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        run_id,
                        idx,
                        step.kind.value,
                        step.content,
                        step.tool_name,
                        None if step.tool_ok is None else int(step.tool_ok),
                        step.latency_ms,
                        step.cost_usd,
                    )
                    for idx, step in enumerate(result.trajectory.steps)
                ],
            )
            self.conn.executemany(
                "INSERT INTO failures (run_id, mode) VALUES (?, ?)",
                [(run_id, mode.value) for mode in failures.modes],
            )


def write_jsonl(results: Iterable[RunResult], path: str | Path) -> int:
    count = 0
    with Path(path).open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(result.model_dump_json() + "\n")
            count += 1
    return count


def read_jsonl(path: str | Path) -> list[RunResult]:
    with Path(path).open(encoding="utf-8") as handle:
        return [RunResult.model_validate_json(line) for line in handle if line.strip()]


def experiment_from_results(
    results: Iterable[RunResult],
    *,
    name: str = "imported",
    suite: str = "",
) -> ExperimentReport:
    grouped: dict[str, list[RunResult]] = {}
    for result in results:
        grouped.setdefault(result.variant, []).append(result)
    reports = [
        EvalReport(
            variant=variant,
            trials=max(run.trial for run in runs) + 1,
            results=runs,
        )
        for variant, runs in grouped.items()
    ]
    return ExperimentReport(name=name, suite=suite, reports=reports)


def _rowid(cursor: sqlite3.Cursor) -> int:
    rowid: Any = cursor.lastrowid
    if rowid is None:
        raise RuntimeError("insert did not return a row id")
    return int(rowid)
