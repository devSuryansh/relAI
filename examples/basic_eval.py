"""Compare two scripted agents with the evaluation harness."""

from relai.demo import DEMO_TASKS, brittle_agent, resilient_agent
from relai.experiment import Variant, run_experiment


def main() -> None:
    report = run_experiment(
        DEMO_TASKS,
        [
            Variant("brittle", brittle_agent()),
            Variant("resilient", resilient_agent()),
        ],
    )
    for summary in report.summary():
        print(summary)


if __name__ == "__main__":
    main()
