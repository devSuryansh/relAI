"""Check the failure classifier against agents whose defects are planted on purpose."""

from __future__ import annotations

from pydantic import BaseModel, Field

from relai.baselines import BASELINES
from relai.env import FaultPolicy
from relai.experiment import Variant, run_experiment
from relai.metrics import get_scorer
from relai.suite import Suite
from relai.types import FailureMode

COLUMNS = [mode.value for mode in FailureMode] + ["unclassified", "none"]


class DefectCheck(BaseModel):
    """Diagnosed root causes per planted-defect agent.

    "none" counts runs where the defect never surfaced, such as a naive agent
    that happened to meet no injected fault. The retry agent has no planted
    defect and serves as the control row.
    """

    planted: dict[str, str | None] = Field(default_factory=dict)
    matrix: dict[str, dict[str, int]] = Field(default_factory=dict)

    def agreement(self, agent: str) -> float:
        """Planted agents: share of diagnosed runs blamed on the planted defect.

        Control agent: share of runs with no diagnosis at all.
        """
        row = self.matrix[agent]
        planted = self.planted[agent]
        if planted is None:
            total = sum(row.values())
            return row["none"] / total if total else 1.0
        diagnosed = sum(count for column, count in row.items() if column != "none")
        return row.get(planted, 0) / diagnosed if diagnosed else 0.0

    def precision(self, mode: str) -> float:
        """Among planted agents, share of runs blamed on a mode that carried that defect."""
        blamed = {
            agent: row.get(mode, 0)
            for agent, row in self.matrix.items()
            if self.planted[agent] is not None
        }
        total = sum(blamed.values())
        right = sum(count for agent, count in blamed.items() if self.planted[agent] == mode)
        return right / total if total else 1.0


def planted_defect_check(
    suite: Suite,
    *,
    faults: FaultPolicy | None = None,
    trials: int = 3,
    seed: int = 0,
) -> DefectCheck:
    """Run every baseline under the same faults and tabulate the diagnosed root causes."""
    env = suite.env(faults if faults is not None else FaultPolicy(timeout_rate=0.3), seed=seed)
    variants = [Variant(name, cls(env, name=name)) for name, cls in BASELINES.items()]
    experiment = run_experiment(
        suite.tasks,
        variants,
        get_scorer(suite.scorer),
        trials=trials,
        seed=seed,
        name="selfcheck",
        suite=suite.name,
    )
    check = DefectCheck()
    for report in experiment.reports:
        planted = BASELINES[report.variant].planted
        check.planted[report.variant] = planted.value if planted else None
        row = dict.fromkeys(COLUMNS, 0)
        for result in report.results:
            if result.failures.root_cause is not None:
                row[result.failures.root_cause.value] += 1
            elif result.failures.unclassified:
                row["unclassified"] += 1
            else:
                row["none"] += 1
        check.matrix[report.variant] = row
    return check
