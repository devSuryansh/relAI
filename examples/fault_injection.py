"""Stress the same agents with rising tool timeouts and print their success curves.

Every agent meets the same fault schedule at each rate, because faults depend on
(seed, task, trial, tool, call number) and not on which agent is calling.
"""

from relai import FaultPolicy, Variant, load_suite, make_baseline, stress_test
from relai.metrics import get_scorer

AGENTS = ["naive", "retry:1", "retry:3"]
RATES = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]


def main() -> None:
    suite = load_suite("reliability")

    def variants_at(rate: float) -> list[Variant]:
        env = suite.env(FaultPolicy(timeout_rate=rate))
        return [Variant(spec, make_baseline(spec, env)) for spec in AGENTS]

    levels = stress_test(
        suite.tasks, variants_at, RATES, get_scorer(suite.scorer), trials=5, seed=0
    )
    print("timeout rate  " + "  ".join(f"{name:>8}" for name in AGENTS))
    for rate, experiment in levels:
        cells = "  ".join(f"{experiment.report_for(name).success_rate:>8.2f}" for name in AGENTS)
        print(f"{rate:>12.1f}  {cells}")


if __name__ == "__main__":
    main()
