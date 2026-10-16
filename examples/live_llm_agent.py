"""Evaluate a real model on the reliability suite through an OpenAI-compatible API.

Hosted:  OPENAI_API_KEY=sk-... RELAI_MODEL=gpt-4o-mini python examples/live_llm_agent.py
Local:   OPENAI_BASE_URL=http://localhost:11434/v1 RELAI_MODEL=qwen2.5:7b \
         python examples/live_llm_agent.py

The same tool environment, faults, scorer, and failure analysis apply as for the
offline baselines, so a live model can be ranked next to them.
"""

import os

from relai import FaultPolicy, Variant, load_suite, make_baseline, run_experiment, to_html
from relai.adapters import OpenAICompatAgent
from relai.metrics import get_scorer


def main() -> None:
    model = os.environ.get("RELAI_MODEL", "gpt-4o-mini")
    suite = load_suite("reliability")
    env = suite.env(FaultPolicy(timeout_rate=0.2))
    llm = OpenAICompatAgent(
        model,
        env,
        model=model,
        usd_per_1k_prompt=float(os.environ.get("RELAI_USD_PER_1K_PROMPT", "0")),
        usd_per_1k_completion=float(os.environ.get("RELAI_USD_PER_1K_COMPLETION", "0")),
    )
    experiment = run_experiment(
        suite.tasks,
        [Variant(llm.name, llm), Variant("retry:2", make_baseline("retry:2", env))],
        get_scorer(suite.scorer),
        trials=3,
        name=f"live {model}",
        suite=suite.name,
    )
    for row in experiment.summary():
        print(row["variant"], f"success={row['success_rate']:.2f}", row["failure_counts"])
    with open("live_report.html", "w", encoding="utf-8") as handle:
        handle.write(to_html(experiment))
    print("wrote live_report.html")


if __name__ == "__main__":
    main()
