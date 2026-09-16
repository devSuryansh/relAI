# Agent Reliability Lab

Python package for evaluating AI agents, classifying trajectory failures, and
comparing variants under a shared task suite.

## Layout

- `src/relai/types.py`: Task, Step, Trajectory, scores, and reports
- `src/relai/agents.py`: Agent protocol plus FunctionAgent and ScriptedAgent adapters
- `src/relai/metrics.py`: scorers and metric derivation
- `src/relai/analysis.py`: failure-mode classification
- `src/relai/harness.py`: evaluate(agent, tasks)
- `src/relai/experiment.py`: controlled multi-variant comparison
- `src/relai/cli.py`: `relai demo`

## Commands

```bash
pip install -e ".[dev]"
pytest
ruff check src tests examples
relai demo
```

## Design

Keep the Agent protocol small: `name` plus `run(task) -> Trajectory`. New model
backends, orchestrators, and memory systems should adapt to that seam rather
than changing the harness. Metrics and failure analysis read trajectories; they
should not call agents.

When adding a failure mode, pin it with a trajectory fixture in
`tests/test_analysis.py` and leave unmatched failures unclassified.
