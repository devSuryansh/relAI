"""Command-line entry point for evaluation, analysis, and comparison."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from relai import __version__
from relai.agents import Agent
from relai.baselines import BASELINES, make_baseline
from relai.demo import DEMO_TASKS, brittle_agent, resilient_agent
from relai.env import FaultPolicy, ToolEnv
from relai.experiment import ExperimentReport, Variant, run_experiment, stress_test
from relai.metrics import get_scorer
from relai.optimize import pareto_front, recommend, sweep
from relai.report import summary_rows, to_html, to_markdown
from relai.selfcheck import COLUMNS, planted_defect_check
from relai.stats import compare
from relai.store import RunStore
from relai.suite import builtin_suites, load_suite

DEFAULT_AGENTS = ["naive", "retry"]


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        return args.handler(args)
    except (ValueError, FileNotFoundError, LookupError, ImportError) as exc:
        print(f"relai: error: {exc}", file=sys.stderr)
        return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="relai",
        description="Agent Reliability Lab: evaluate, analyze, and compare AI agents.",
    )
    parser.add_argument("--version", action="version", version=f"relai {__version__}")
    sub = parser.add_subparsers(dest="command")

    demo = sub.add_parser("demo", help="compare a brittle and a resilient scripted agent")
    _add_outputs(demo, store=False)
    demo.set_defaults(handler=_demo)

    suites = sub.add_parser("suites", help="list the built-in task suites")
    suites.set_defaults(handler=_suites)

    run = sub.add_parser("run", help="evaluate one or more agents on a suite")
    run.add_argument("suite", help="built-in suite name or path to a .yaml or .json suite")
    run.add_argument(
        "--agent",
        action="append",
        metavar="SPEC",
        help="baseline such as naive, retry:3, looping, careless, guessing, or a "
        "module:factory that takes a ToolEnv; repeatable (default: naive and retry)",
    )
    _add_conditions(run)
    _add_outputs(run)
    run.set_defaults(handler=_run)

    tune = sub.add_parser("sweep", help="search agent settings for the cheapest reliable one")
    tune.add_argument("suite", help="built-in suite name or path to a suite file")
    tune.add_argument("--agent", default="retry", help="baseline to configure (default: retry)")
    tune.add_argument(
        "--param",
        action="append",
        metavar="KEY=V1,V2",
        help="values to try for one setting; repeatable (default: max_retries=0,1,2,3)",
    )
    tune.add_argument(
        "--min-success",
        type=float,
        default=0.9,
        help="reliability target for the recommendation (default: 0.9)",
    )
    _add_conditions(tune)
    _add_outputs(tune)
    tune.set_defaults(handler=_sweep)

    stress = sub.add_parser("stress", help="measure how success falls as tool timeouts rise")
    stress.add_argument("suite", help="built-in suite name or path to a suite file")
    stress.add_argument("--agent", action="append", metavar="SPEC", help="repeatable")
    stress.add_argument(
        "--rates",
        default="0,0.1,0.2,0.3,0.4,0.5",
        help="comma-separated timeout rates (default: 0,0.1,0.2,0.3,0.4,0.5)",
    )
    _add_conditions(stress, faults=False)
    stress.add_argument("--json", action="store_true", help="print JSON instead of a table")
    stress.set_defaults(handler=_stress)

    check = sub.add_parser(
        "selfcheck", help="check the failure classifier on agents with planted defects"
    )
    check.add_argument("suite", nargs="?", default="reliability", help="(default: reliability)")
    _add_conditions(check, default_trials=3)
    check.add_argument("--json", action="store_true", help="print JSON instead of a table")
    check.set_defaults(handler=_selfcheck)

    report = sub.add_parser("report", help="list or render experiments saved with --store")
    report.add_argument("store", help="SQLite file written by --store")
    report.add_argument("--experiment", type=int, help="experiment id (default: latest)")
    report.add_argument("--list", action="store_true", help="list stored experiments")
    report.add_argument("--html", metavar="PATH", help="write a standalone HTML report")
    report.add_argument("--markdown", metavar="PATH", help="write a Markdown report")
    report.set_defaults(handler=_report)
    return parser


def _add_conditions(
    parser: argparse.ArgumentParser,
    *,
    faults: bool = True,
    default_trials: int = 1,
) -> None:
    parser.add_argument(
        "--trials",
        type=int,
        default=default_trials,
        help=f"attempts per task (default: {default_trials})",
    )
    parser.add_argument("--seed", type=int, default=0, help="fault schedule seed (default: 0)")
    parser.add_argument("--scorer", help="exact, contains, normalized, numeric, or regex")
    if faults:
        parser.add_argument("--timeout-rate", type=float, help="share of tool calls that time out")
        parser.add_argument("--error-rate", type=float, help="share of tool calls that fail")
        parser.add_argument("--fail-first", type=int, help="fail the first N calls of each tool")


def _add_outputs(parser: argparse.ArgumentParser, *, store: bool = True) -> None:
    parser.add_argument("--json", action="store_true", help="print JSON summaries")
    parser.add_argument("--html", metavar="PATH", help="write a standalone HTML report")
    parser.add_argument("--markdown", metavar="PATH", help="write a Markdown report")
    if store:
        parser.add_argument("--store", metavar="PATH", help="save runs to a SQLite file")


def _demo(args: argparse.Namespace) -> int:
    experiment = run_experiment(
        DEMO_TASKS,
        [
            Variant("brittle", brittle_agent()),
            Variant("resilient", resilient_agent()),
        ],
        name="demo",
        suite="scripted demo",
    )
    _emit(experiment, args)
    return 0


def _suites(args: argparse.Namespace) -> int:
    for name in builtin_suites():
        suite = load_suite(name)
        print(f"{name:<12} {len(suite.tasks):>2} tasks  {suite.description}")
    return 0


def _run(args: argparse.Namespace) -> int:
    suite = load_suite(args.suite)
    env = suite.env(_faults(args), seed=args.seed)
    agents = [_agent(spec, env) for spec in args.agent or DEFAULT_AGENTS]
    experiment = run_experiment(
        suite.tasks,
        [Variant(agent.name, agent) for agent in agents],
        get_scorer(args.scorer or suite.scorer),
        trials=args.trials,
        seed=args.seed,
        name="run",
        suite=suite.name,
    )
    _emit(experiment, args)
    return 0


def _sweep(args: argparse.Namespace) -> int:
    suite = load_suite(args.suite)
    if args.agent not in BASELINES:
        raise ValueError(f"sweep works on baselines: {', '.join(BASELINES)}")
    env = suite.env(_faults(args), seed=args.seed)
    if not env.faults.active:
        print("relai: note: no faults injected; try --timeout-rate 0.3", file=sys.stderr)
    space = _space(args.param or ["max_retries=0,1,2,3"])
    cls = BASELINES[args.agent]
    experiment = sweep(
        suite.tasks,
        lambda **config: cls(env, **config),
        space,
        get_scorer(args.scorer or suite.scorer),
        trials=args.trials,
        seed=args.seed,
        name=f"sweep of {args.agent}",
        suite=suite.name,
    )
    _emit(experiment, args)
    if not args.json:
        front = ", ".join(report.variant for report in pareto_front(experiment.reports))
        print(f"\nPareto front (success, cost, latency): {front}")
        best = recommend(experiment.reports, min_success=args.min_success)
        if best is None:
            print(f"No setting reaches success >= {args.min_success:.2f}.")
        else:
            print(
                f"Recommended: {best.variant} (success {best.success_rate:.2f}, "
                f"${best.mean_cost_usd:.4f} and {best.mean_step_latency_ms:.0f} ms per run), "
                f"the cheapest setting with success >= {args.min_success:.2f}."
            )
    return 0


def _stress(args: argparse.Namespace) -> int:
    suite = load_suite(args.suite)
    rates = [float(value) for value in args.rates.split(",") if value.strip()]
    specs = args.agent or DEFAULT_AGENTS

    def variants_at(rate: float) -> list[Variant]:
        env = suite.env(FaultPolicy(timeout_rate=rate), seed=args.seed)
        return [Variant(agent.name, agent) for agent in (_agent(s, env) for s in specs)]

    levels = stress_test(
        suite.tasks,
        variants_at,
        rates,
        get_scorer(args.scorer or suite.scorer),
        trials=args.trials,
        seed=args.seed,
    )
    names = [report.variant for report in levels[0][1].reports] if levels else []
    curves = {
        name: [experiment.report_for(name).success_rate for _, experiment in levels]
        for name in names
    }
    if args.json:
        json.dump({"timeout_rates": rates, "success_rate": curves}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    headers = ["agent \\ timeout rate", *(f"{rate:g}" for rate in rates)]
    rows = [[name, *(f"{value:.2f}" for value in curve)] for name, curve in curves.items()]
    print("success rate as tool timeouts increase")
    _print_rows(headers, rows)
    return 0


def _selfcheck(args: argparse.Namespace) -> int:
    suite = load_suite(args.suite)
    faults = _faults(args) or FaultPolicy(timeout_rate=0.3)
    check = planted_defect_check(suite, faults=faults, trials=args.trials, seed=args.seed)
    if args.json:
        payload = {
            "planted": check.planted,
            "matrix": check.matrix,
            "agreement": {agent: check.agreement(agent) for agent in check.matrix},
        }
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    headers = ["agent", "planted", *COLUMNS, "agreement"]
    rows = [
        [
            agent,
            check.planted[agent] or "(control)",
            *(str(row[column]) for column in COLUMNS),
            f"{check.agreement(agent):.2f}",
        ]
        for agent, row in check.matrix.items()
    ]
    print(
        f"diagnosed root cause per agent, {suite.name} suite, "
        f"timeout rate {faults.timeout_rate:g}"
    )
    _print_rows(headers, rows)
    planted = sorted({mode for mode in check.planted.values() if mode})
    precision = ", ".join(f"{mode} {check.precision(mode):.2f}" for mode in planted)
    print(f"\nprecision by mode: {precision}")
    return 0


def _report(args: argparse.Namespace) -> int:
    with RunStore(args.store) as store:
        if args.list:
            for item in store.experiments():
                print(
                    f"{item.id:>3}  {item.created_at}  {item.name:<24} "
                    f"suite={item.suite or '-'}  variants={item.variants}  runs={item.runs}"
                )
            return 0
        experiment = store.load(args.experiment)
    _emit(experiment, args, save=False)
    return 0


def _emit(experiment: ExperimentReport, args: argparse.Namespace, *, save: bool = True) -> None:
    if save and getattr(args, "store", None):
        with RunStore(args.store) as store:
            experiment_id = store.save(experiment)
        print(f"relai: saved experiment {experiment_id} to {args.store}", file=sys.stderr)
    if getattr(args, "html", None):
        Path(args.html).write_text(to_html(experiment), encoding="utf-8")
        print(f"relai: wrote {args.html}", file=sys.stderr)
    if getattr(args, "markdown", None):
        Path(args.markdown).write_text(to_markdown(experiment), encoding="utf-8")
        print(f"relai: wrote {args.markdown}", file=sys.stderr)
    if getattr(args, "json", False):
        json.dump(experiment.summary(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return
    _print_table(experiment)


def _print_table(experiment: ExperimentReport) -> None:
    rows = summary_rows(experiment)
    trials = max((row["trials"] for row in rows), default=1)
    headers = ["variant", "success", "95% CI"]
    if trials > 1:
        headers += ["pass^k", "consistent"]
    headers += ["cost", "latency", "recovery", "horizon"]
    table = []
    for row in rows:
        low, high = row["ci"]
        cells = [row["variant"], f"{row['success']:.2f}", f"[{low:.2f}, {high:.2f}]"]
        if trials > 1:
            cells += [f"{row['pass_hat_k']:.2f}", f"{row['consistency']:.2f}"]
        cells += [
            f"${row['cost']:.4f}",
            f"{row['latency']:.0f}ms",
            f"{row['recovery']:.2f}",
            f"{row['horizon']:.1f}",
        ]
        table.append(cells)
    _print_rows(headers, table)
    print()
    for row in rows:
        active = {mode: count for mode, count in row["failures"].items() if count}
        print(f"failure modes ({row['variant']}): {active or 'none'}")
    ranked = experiment.ranking()
    if len(ranked) >= 2:
        try:
            result = compare(ranked[0], ranked[1])
        except ValueError:
            return
        verdict = "significant" if result.significant() else "not significant"
        print(
            f"\n{result.a} vs {result.b} on {result.pairs} paired runs: "
            f"{result.a} alone passed {result.a_only}, {result.b} alone passed "
            f"{result.b_only}; McNemar p = {result.p_value:.4f} ({verdict})"
        )


def _print_rows(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
    widths = [
        max(len(headers[i]), *(len(row[i]) for row in rows)) if rows else len(headers[i])
        for i in range(len(headers))
    ]
    fmt = "  ".join(f"{{:<{width}}}" for width in widths)
    print(fmt.format(*headers).rstrip())
    print(fmt.format(*("-" * width for width in widths)).rstrip())
    for row in rows:
        print(fmt.format(*row).rstrip())


def _faults(args: argparse.Namespace) -> FaultPolicy | None:
    given = {
        "timeout_rate": getattr(args, "timeout_rate", None),
        "error_rate": getattr(args, "error_rate", None),
        "fail_first_n": getattr(args, "fail_first", None),
    }
    chosen = {key: value for key, value in given.items() if value is not None}
    return FaultPolicy(**chosen) if chosen else None


def _agent(spec: str, env: ToolEnv) -> Agent:
    if spec.partition(":")[0] in BASELINES:
        return make_baseline(spec, env)
    module_name, sep, attr = spec.partition(":")
    if not sep or not attr:
        raise ValueError(
            f"agent {spec!r} is neither a baseline ({', '.join(BASELINES)}) nor module:factory"
        )
    if os.getcwd() not in sys.path:
        sys.path.insert(0, os.getcwd())
    factory = getattr(importlib.import_module(module_name), attr)
    agent = factory(env)
    if not isinstance(agent, Agent):
        raise ValueError(f"{spec!r} did not return an object with name and run(task)")
    return agent


def _space(params: Sequence[str]) -> dict[str, list[Any]]:
    space: dict[str, list[Any]] = {}
    for param in params:
        key, eq, values = param.partition("=")
        if not eq or not values:
            raise ValueError(f"--param {param!r} should look like key=1,2,3")
        space[key.strip()] = [_value(value.strip()) for value in values.split(",")]
    return space


def _value(text: str) -> Any:
    for cast in (int, float):
        try:
            return cast(text)
        except ValueError:
            continue
    return text


if __name__ == "__main__":
    raise SystemExit(main())
