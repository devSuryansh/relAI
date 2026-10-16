# Agent Reliability Lab

Python package for evaluating AI agents, classifying trajectory failures,
injecting tool faults, and comparing or tuning variants under a shared task
suite.

## Layout

- `src/relai/types.py`: Task, Step, Trajectory, scores, and reports
- `src/relai/agents.py`: Agent protocol plus FunctionAgent and ScriptedAgent adapters
- `src/relai/env.py`: ToolEnv, seeded FaultPolicy, Recorder, built-in tools
- `src/relai/harness.py`: evaluate(agent, tasks, trials=k), pass@k and pass^k
- `src/relai/metrics.py`: scorers and metric derivation
- `src/relai/analysis.py`: failure-mode classification
- `src/relai/experiment.py`: controlled multi-variant comparison and stress tests
- `src/relai/stats.py`: confidence intervals and paired tests
- `src/relai/optimize.py`: sweeps, Pareto front, recommendation
- `src/relai/suite.py` and `src/relai/suites/`: YAML task suites
- `src/relai/baselines.py` and `src/relai/selfcheck.py`: planted-defect agents
- `src/relai/store.py`: SQLite and JSON Lines persistence
- `src/relai/report.py`: HTML and Markdown reports
- `src/relai/adapters/`: OpenAI-compatible model adapter
- `src/relai/cli.py`: `relai demo`, `suites`, `run`, `sweep`, `stress`, `selfcheck`, `report`
- `documentation/`: architecture and failure taxonomy
- `academic/`: progress review deliverables (paper, slides, report, diagrams)

## Commands

```bash
pip install -e ".[dev]"
pytest
ruff check src tests examples
relai demo
relai run reliability --trials 5 --timeout-rate 0.3
```

## Design

Keep the Agent protocol small: `name` plus `run(task) -> Trajectory`. New model
backends, orchestrators, and memory systems should adapt to that seam rather
than changing the harness. Metrics and failure analysis read trajectories; they
should not call agents.

Faults must depend only on (seed, task, trial, tool, call number) so every
variant meets the same schedule and runs stay paired.

When adding a failure mode, pin it with a trajectory fixture in
`tests/test_analysis.py` and leave unmatched failures unclassified.
