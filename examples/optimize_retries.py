"""Find the cheapest retry budget that keeps an agent reliable under faults."""

from relai import FaultPolicy, RetryAgent, load_suite, pareto_front, recommend, sweep
from relai.metrics import get_scorer


def main() -> None:
    suite = load_suite("reliability")
    env = suite.env(FaultPolicy(timeout_rate=0.3))
    experiment = sweep(
        suite.tasks,
        lambda max_retries, backoff_ms: RetryAgent(
            env, max_retries=max_retries, backoff_ms=backoff_ms
        ),
        {"max_retries": [0, 1, 2, 3], "backoff_ms": [0, 200]},
        get_scorer(suite.scorer),
        trials=5,
    )
    for report in experiment.ranking():
        print(
            f"{report.variant:<28} success {report.success_rate:.2f}  "
            f"pass^5 {report.pass_hat_k_value:.2f}  cost ${report.mean_cost_usd:.4f}  "
            f"latency {report.mean_step_latency_ms:.0f} ms"
        )
    front = [report.variant for report in pareto_front(experiment.reports)]
    print("\nPareto front:", ", ".join(front))
    best = recommend(experiment.reports, min_success=0.95)
    print("Cheapest setting with success >= 0.95:", best.variant if best else "none")


if __name__ == "__main__":
    main()
