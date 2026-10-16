"""A hand-written agent that plugs into the CLI.

    relai run reliability --agent examples.custom_agent:make_agent --timeout-rate 0.3

The factory receives the suite's ToolEnv. The agent only needs a name and
run(task) -> Trajectory; the Recorder turns its tool calls into steps.
"""

from relai import Recorder, Task, ToolEnv, Trajectory
from relai.baselines import solution_of


class StubbornAgent:
    """Retries every failed call until it works or five attempts are spent."""

    name = "stubborn"

    def __init__(self, env: ToolEnv) -> None:
        self.env = env

    def run(self, task: Task) -> Trajectory:
        rec: Recorder = self.env.recorder(task)
        rec.plan("follow the reference plan and never give up early")
        outputs: list[str] = []
        for call in solution_of(task):
            args = {key: str(value).format(*outputs) for key, value in call.args.items()}
            result = rec.call(call.tool, args)
            attempts = 1
            while not result.ok and attempts < 5:
                rec.recovery(f"attempt {attempts + 1}")
                result = rec.call(call.tool, args)
                attempts += 1
            if not result.ok:
                return rec.final("unknown")
            outputs.append(result.output)
        return rec.final(outputs[-1] if outputs else str(task.metadata.get("answer", "")))


def make_agent(env: ToolEnv) -> StubbornAgent:
    return StubbornAgent(env)
