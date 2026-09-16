# Agent Reliability Lab

Open-source platform for systematically evaluating AI agents across task success,
correctness, cost, latency, tool usage, recovery, and long-horizon reliability.

The lab captures agent trajectories and analyzes failure modes such as planning
errors, tool misuse, context failures, and ineffective recovery. It supports
controlled comparisons of models, agent architectures, and orchestration
strategies so you can see not only whether an agent succeeds, but why it
succeeds or fails and how its reliability can be improved.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quickstart

```bash
relai demo
```

That command evaluates two scripted agents on a small suite covering short-horizon
QA, tool use, and error recovery. Use `--json` for machine-readable summaries.

Programmatically:

```python
from relai import FunctionAgent, Task, Trajectory, Step, evaluate, run_experiment, Variant

task = Task(id="math", prompt="What is 6 * 7?", expected="42")

def solve(task: Task) -> Trajectory:
    return Trajectory(steps=[Step.final("42")])

report = evaluate(FunctionAgent("toy", solve), [task])
print(report.summary())
```

See `examples/basic_eval.py` for a side-by-side comparison.

## What gets measured

Each run records a **trajectory** (plan, tool calls, observations, errors,
recovery, final answer). From that trace the harness derives:

| Area | Signals |
| --- | --- |
| Reliability | task success, correctness |
| Efficiency | cost, wall latency, step latency, tokens |
| Tool use | call count, unnecessary repeated calls |
| Recovery | attempts, successes, recovery rate |
| Horizon | steps taken on the task |

Failure analysis then classifies root causes:

- **Planning**: required tools skipped, or an incorrect answer with no tool use
- **Tool misuse**: disallowed tools, or tool failures that are not environment errors
- **Context**: repeating the same tool call after an observation
- **Recovery**: an error with no retry, or a retry that does not restore a working path

Failures that do not match a known mode are marked unclassified rather than forced
into the taxonomy.

## Project layout

```
src/relai/     core library (types, harness, analysis, experiments)
tests/         unit tests for metrics, analysis, and comparisons
examples/      runnable comparison script
```

The **Agent** protocol is the seam for plugging in real systems. Wrap any
`task -> trajectory` callable with `FunctionAgent`, or supply canned traces with
`ScriptedAgent` while you build model and framework adapters.

## Development

```bash
pytest
ruff check src tests examples
```

## License

MIT
