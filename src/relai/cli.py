"""Command-line entry point for evaluation, analysis, and comparison."""

from __future__ import annotations

import argparse
import json
import sys

from relai import __version__
from relai.demo import DEMO_TASKS, brittle_agent, resilient_agent
from relai.experiment import Variant, run_experiment
from relai.harness import EvalReport


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="relai",
        description="Agent Reliability Lab: evaluate, analyze, and compare AI agents.",
    )
    parser.add_argument("--version", action="version", version=f"relai {__version__}")
    sub = parser.add_subparsers(dest="command")

    demo = sub.add_parser("demo", help="run the built-in comparison suite")
    demo.add_argument(
        "--json",
        action="store_true",
        help="print machine-readable summaries instead of a table",
    )

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "demo":
        return _demo(as_json=args.json)
    parser.print_help()
    return 1


def _demo(*, as_json: bool) -> int:
    experiment = run_experiment(
        DEMO_TASKS,
        [
            Variant("brittle", brittle_agent()),
            Variant("resilient", resilient_agent()),
        ],
    )
    if as_json:
        json.dump(experiment.summary(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    _print_table(experiment.reports)
    return 0


def _print_table(reports: list[EvalReport]) -> None:
    headers = ("variant", "success", "cost", "latency", "recovery", "horizon")
    rows = [
        (
            report.variant,
            f"{report.success_rate:.2f}",
            f"${report.mean_cost_usd:.4f}",
            f"{report.mean_latency_ms:.2f}ms",
            f"{report.mean_recovery_rate:.2f}",
            f"{report.mean_horizon_steps:.1f}",
        )
        for report in reports
    ]
    widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) for i in range(len(headers))]
    fmt = "  ".join(f"{{:<{width}}}" for width in widths)
    print(fmt.format(*headers))
    print(fmt.format(*("-" * width for width in widths)))
    for row in rows:
        print(fmt.format(*row))
    print()
    for report in reports:
        counts = report.failure_counts()
        active = {k: v for k, v in counts.items() if v}
        print(f"failure modes ({report.variant}): {active or 'none'}")


if __name__ == "__main__":
    raise SystemExit(main())
