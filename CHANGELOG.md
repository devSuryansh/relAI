# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-10-17

### Added

- Tool environment with seeded fault injection: timeouts, outages, and
  fail-first-N, identical for every variant.
- Repeated trials per task with pass@k, pass^k, and consistency.
- Horizon failure mode for runs that never answer or overrun their step
  budget.
- Normalized, numeric, and regex scorers.
- YAML and JSON task suites, with a demo suite and a twelve-task
  customer-support suite.
- Offline baseline agents with planted defects, and `relai selfcheck` to
  check the classifier against them.
- Wilson and bootstrap confidence intervals and an exact McNemar paired test.
- Grid sweeps, Pareto-front selection, and a cheapest-reliable-setting
  recommendation.
- SQLite run store and JSON Lines export.
- Standalone HTML and Markdown reports.
- Agent adapter for OpenAI-compatible chat APIs, hosted or local.
- CLI commands: `suites`, `run`, `sweep`, `stress`, `selfcheck`, `report`.

### Changed

- A chain of retries that ends in success now counts as a recovery, and an
  error is recovered only by a working call of the tool that failed or by a
  correct answer.
- Ranking breaks ties on recorded step latency before wall-clock time, so
  simulated runs rank the same way every time.
- An agent that raises an exception produces a failed run instead of stopping
  the experiment.

## [0.1.0] - 2026-09-16

### Added

- Trajectory schema, Agent protocol, evaluation harness, metrics, four failure
  modes, multi-variant experiments, and `relai demo`.
