"""Build the final synopsis (Word and PDF) in the institute synopsis format.

    /path/to/venv-with-python-docx/bin/python academic/docs_build/build_synopsis.py

Base template: docs/Synopsis_First_Draft.docx (cover logo, page numbering).
Format rules from docs/Final_synopsis_format: headings Times New Roman 18 bold
centred, text 16 justified, subheadings 16 bold left, index 24, references 12.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from docxkit import NAVY, Builder, Style, build_twice  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DIAGRAMS = ROOT / "academic" / "diagrams"
OUT_DIR = ROOT / "academic" / "synopsis"
TEMPLATE = ROOT / "docs" / "Synopsis_First_Draft.docx"

STYLE = Style(body=16, line=1.15, after=6, h1=18, h2=16, h3=16, caption=12, table=12,
              h1_upper=False, numbered_heading=True)

INDEX_ROWS = [
    ("1", "Introduction", "1. Introduction"),
    ("1.1", "Background and Motivation", "1.1 Background and Motivation"),
    ("1.2", "Field of the Project and Technology Used", "1.2 Field of the Project and Technology Used"),
    ("1.3", "Important Technical Terms", "1.3 Important Technical Terms"),
    ("1.4", "Objectives and Scope", "1.4 Objectives and Scope"),
    ("2", "Existing Systems", "2. Existing Systems"),
    ("2.1", "Literature and Tool Survey (Tabular)", "2.1 Literature and Tool Survey"),
    ("2.2", "Comparative Discussion and Research Gaps", "2.2 Comparative Discussion and Research Gaps"),
    ("3", "Problem Statement", "3. Problem Statement"),
    ("4", "Proposed Methodology", "4. Proposed Methodology"),
    ("4.1", "System Architecture", "4.1 System Architecture"),
    ("4.2", "Overview of Modules", "4.2 Overview of Modules"),
    ("4.3", "Use Cases", "4.3 Use Cases"),
    ("4.4", "Entity-Relationship Model", "4.4 Entity-Relationship Model"),
    ("4.5", "Data Flow Diagrams", "4.5 Data Flow Diagrams"),
    ("4.6", "Flowcharts of Core Processes", "4.6 Flowcharts of Core Processes"),
    ("4.7", "Core Algorithms and Implementation Plan", "4.7 Core Algorithms and Implementation Plan"),
    ("5", "Feasibility Study", "5. Feasibility Study"),
    ("6", "Facilities Required for Proposed Work", "6. Facilities Required for Proposed Work"),
    ("7", "Conclusion", "7. Conclusion"),
    ("8", "References", "8. References"),
]


def make(pages: dict[str, str] | None) -> Builder:
    b = Builder(TEMPLATE, STYLE, pages)
    cover(b)
    b.end_section(0)
    index(b)
    b.end_section(1)
    introduction(b)
    existing_systems(b)
    problem_statement(b)
    methodology(b)
    feasibility(b)
    facilities(b)
    conclusion(b)
    references(b)
    b.set_properties(
        title="Agent Reliability Lab: Final Synopsis",
        subject="B.Tech CSE Final Year Project Synopsis, Group G053",
        author="Suryansh Singh, Simran Kumari, Tanishka Sahu",
        keywords="agent reliability, fault injection, failure analysis, pass^k",
    )
    return b


def cover(b: Builder) -> None:
    b.logo_picture(2.3)
    b.paragraph("Synopsis on", size=16, italic=True, align="center", line=1.5, before=4, after=4)
    b.paragraph("AGENT RELIABILITY LAB", size=20, bold=True, align="center", line=1.5, after=2, color=NAVY)
    b.paragraph("Controlled Fault Injection and Evidence-Based Failure Analysis for AI Agents",
                size=16, bold=True, align="center", line=1.3, after=4)
    b.paragraph("in partial fulfillment of the requirement for the degree", size=16, italic=True,
                align="center", line=1.5, before=4, after=2)
    b.paragraph("of", size=16, align="center", line=1.5, after=2)
    b.paragraph("Bachelor of Technology In", size=16, align="center", line=1.5, after=2)
    b.paragraph("COMPUTER SCIENCE AND ENGINEERING", size=16, bold=True, align="center", line=1.5, after=6, color=NAVY)
    b.paragraph("Submitted by", size=16, italic=True, align="center", line=1.5, after=2)
    for name in ("Suryansh Singh (2301330100208)", "Simran Kumari (2301330100200)", "Tanishka Sahu (2301330100210)"):
        b.paragraph(name, size=16, bold=True, align="center", line=1.3, after=1)
    b.paragraph("Group: CSE/CSPROJECT/2027/G053", size=14, align="center", line=1.5, before=4, after=2)
    b.paragraph("Under the supervision of", size=14, italic=True, align="center", line=1.5, after=1)
    b.paragraph("Mr. Pradeep Kumar (Asst. Professor, CSE)", size=14, bold=True, align="center", line=1.5, after=8)
    b.paragraph("NOIDA INSTITUTE OF ENGINEERING AND TECHNOLOGY", size=16, bold=True, align="center", line=1.3, after=1, color=NAVY)
    b.paragraph("GREATER NOIDA", size=16, bold=True, align="center", line=1.3, after=1, color=NAVY)
    b.paragraph("(An Autonomous Institute)", size=14, italic=True, align="center", line=1.3, after=1)
    b.paragraph("Department of Computer Science and Engineering", size=14, align="center", line=1.3, after=1)
    b.paragraph("Session 2026-27", size=14, bold=True, align="center", line=1.3, after=0)


def index(b: Builder) -> None:
    b.paragraph("Index", size=24, bold=True, align="center", line=1.5, after=10)
    rows = [("Sr. No.", "Topics", "Page No.")]
    rows += [(no, topic, b.pages.get(label, "0")) for no, topic, label in INDEX_ROWS]
    b.table(rows, [0.9, 4.5, 1.0], size=14, align=["center", "left", "center"])
    b.paragraph("", after=18)
    b.paragraph("Supervisor Sign: ______________________________", size=16, bold=True, align="left", before=18)


def introduction(b: Builder) -> None:
    b.chapter("Introduction")
    b.section("Background and Motivation")
    b.paragraph(
        "Agents built on large language models (LLMs) no longer answer a single question. "
        "They plan, call tools such as search engines, databases, and calculators, read what "
        "comes back, recover from errors, and continue for many steps. This shift has created "
        "a practical reliability problem. An agent may finish a task in one attempt and fail "
        "the same task in the next. It may skip a tool it needed, call a tool it was never "
        "given, repeat a call after the answer arrived, or give up after a single timeout. "
        "Most benchmarks still report one number, the share of tasks finished, measured once "
        "per task in a clean environment where nothing breaks."
    )
    b.paragraph(
        "That number hides three things a team needs before it trusts an agent: why runs fail, "
        "how consistently the agent succeeds, and what its reliability costs in money and time. "
        "Agent Reliability Lab is proposed as a crash-test laboratory for AI agents. It breaks "
        "tools on purpose in a repeatable way, runs every agent several times on the same tasks, "
        "explains each failed run with evidence, and selects the cheapest configuration that "
        "stays reliable. It does not train a new model; it provides the experiment around the "
        "model, so that two agents can be compared fairly and the difference can be explained."
    )
    b.section("Field of the Project and Technology Used")
    b.paragraph(
        "The project belongs to Computer Science and Engineering, in the area of agentic AI, "
        "evaluation of LLM systems, and software reliability engineering. It borrows two ideas "
        "from outside machine learning: fault injection from chaos engineering, where failures "
        "are introduced deliberately to test resilience, and paired experimental design from "
        "statistics, where two treatments are compared on the same subjects."
    )
    b.paragraph(
        "The implementation is a Python 3.11+ package named `relai` with a command-line "
        "interface. Pydantic models describe tasks and trajectories, task suites are YAML files, "
        "results are stored in SQLite, and reports are rendered as HTML. Testing uses pytest and "
        "linting uses Ruff. Live models connect through any OpenAI-compatible API, including "
        "local models served by Ollama."
    )
    b.section("Important Technical Terms")
    b.bullets([
        "**Agent:** a program that works on a task by planning and calling tools; here, anything with a name and a `run(task)` method.",
        "**Trajectory:** the ordered list of steps in one run: plan, tool call, observation, error, recovery, and final answer.",
        "**Trial:** one attempt at a task; every task is attempted several times.",
        "**Fault injection:** making tool calls time out or fail on purpose, on a seeded schedule.",
        "**pass@k and pass^k:** the chance that at least one, or all, of k attempts succeed.",
        "**Failure mode:** a diagnosed cause of failure: planning, tool misuse, context, recovery, or horizon.",
        "**Unclassified:** a failed run that no rule explains, kept separate instead of being forced into a mode.",
        "**Paired test:** a significance test (McNemar) that compares two agents on the same task and trial.",
        "**Pareto front:** the settings that cannot be improved on success without costing more money or time.",
    ])
    b.section("Objectives and Scope")
    b.paragraph("The objectives of the proposed work are:")
    b.numbered([
        "To build an evaluation framework that measures success, correctness, cost, latency, tool use, recovery, step use, and reliability across repeated trials.",
        "To develop automated failure analysis and recovery evaluation, using seeded fault injection and an evidence-based failure taxonomy.",
        "To enable controlled experiments and optimization: fair comparison of models, prompts, and policies, and selection of the cheapest setting that meets a reliability target.",
    ])
    b.paragraph(
        "The scope is a local, offline-capable laboratory that any agent can plug into. A hosted "
        "monitoring service, model training, and a graphical dashboard are outside the scope of "
        "the first version and are planned as later extensions."
    )


def existing_systems(b: Builder) -> None:
    b.chapter("Existing Systems")
    b.paragraph(
        "Evaluation of LLMs and agents is an active field. Some systems measure models on static "
        "prompts, some score agents in task environments, some record traces for debugging, and "
        "recent work studies reliability and fault injection directly. Table 2.1 places the most "
        "relevant approaches side by side."
    )
    b.section("Literature and Tool Survey")
    b.table(
        [
            ("S. No.", "System / Work", "Primary focus", "Limitation for this problem"),
            ("1", "HELM; LM Evaluation Harness", "Broad benchmarking of models on static datasets", "Scores single responses, not multi-step agent trajectories"),
            ("2", "AgentBench, GAIA, SWE-bench, WebArena", "Agent tasks and environments with task success", "Report success once per task; no failure diagnosis"),
            ("3", "tau-bench (2024)", "Tool-agent-user tasks; introduced pass^k", "No injected faults or per-run diagnosis"),
            ("4", "HAL leaderboard (ICLR 2026)", "Cost-aware evaluation of agents at scale", "Benchmark infrastructure; no shared fault schedule"),
            ("5", "Agent reliability metrics (ICML 2026)", "Twelve metrics: consistency, robustness, predictability, safety", "Metrics on benchmarks; no paired test or self-checked classifier"),
            ("6", "ToolMisuseBench, ToolBench-X (2026)", "Replayable tool faults and hazards", "Benchmark datasets; faults not used as a paired factor"),
            ("7", "AgentChaos (2026)", "Chaos engineering through an LLM API proxy", "Injects at model layer; no taxonomy of agent failures"),
            ("8", "MAST, TRAIL, Who&When (2025)", "Failure taxonomies and attribution in traces", "Human or LLM labels; best step attribution only 14.2%"),
            ("9", "LangSmith, Langfuse, Phoenix", "Production tracing and scoring", "Observe live traffic; no controlled experiments"),
            ("10", "Inspect AI, DeepEval, Promptfoo", "Evaluation frameworks and CI tests", "General scoring; no agent fault schedule or recovery metric"),
        ],
        [0.6, 1.7, 2.1, 2.1],
        "Survey of existing evaluation approaches",
        size=11,
    )
    b.section("Comparative Discussion and Research Gaps")
    b.paragraph(
        "Model benchmarks answer whether a model can solve a prompt. Agent benchmarks add "
        "environments, but their contribution is the task, not an analysis layer. Tracing "
        "platforms capture rich logs and are the right choice for production debugging, but "
        "they observe traffic rather than run controlled experiments. Recent reliability and "
        "fault-injection research is the closest to this project; it proposes metrics and "
        "benchmarks, while this project provides a small laboratory in which any team can run "
        "the experiment on its own agent."
    )
    b.paragraph("The survey shows five gaps that this project addresses:")
    b.bullets([
        "**Success-only reporting:** one score hides why a run failed and how consistent the agent is.",
        "**Unfair comparison:** when failures are random per run, two agents never meet the same conditions.",
        "**Missing recovery accounting:** retry quality after timeouts is rarely measured.",
        "**Unverified diagnosis:** automated failure labels are seldom checked against known ground truth.",
        "**Cost-blind selection:** reliability is reported without the cost and latency it requires.",
    ])


def problem_statement(b: Builder) -> None:
    b.chapter("Problem Statement")
    b.paragraph(
        "**Background.** Tool-using AI agents fail in ways that a single accuracy number cannot "
        "explain. One agent guesses without calling a required tool, another calls a forbidden "
        "tool, a third repeats a call it has already answered, and a fourth abandons a task "
        "after one timeout. Existing benchmarks publish task success measured once in a clean "
        "environment, and existing tracers publish logs. Neither lets a team run a fair, "
        "repeatable experiment in which agents meet the same failures, every failure is "
        "explained, and the cost of reliability is visible."
    )
    b.paragraph(
        "**Problem.** Design and implement Agent Reliability Lab, a framework that runs any "
        "agent on a shared task suite for several trials under seeded tool faults that are "
        "identical for every agent; records each trajectory; measures success, pass^k, "
        "consistency, cost, latency, recovery, and step use with confidence intervals; "
        "classifies planning, tool-misuse, context, recovery, and horizon failures with evidence "
        "while leaving unexplained failures unclassified; tests whether two agents differ "
        "significantly; and recommends the cheapest configuration that meets a reliability target."
    )
    b.paragraph(
        "**Expected resolution.** A small agent interface, analysis that only reads stored "
        "trajectories, a fault schedule independent of the agent, rules pinned by tests, and a "
        "self-check that proves the classifier finds defects planted on purpose."
    )


def methodology(b: Builder) -> None:
    b.chapter("Proposed Methodology")
    b.paragraph(
        "The methodology is organized as modules that follow the data. Domain types come first "
        "because every later pass reads the same objects. The agent interface and the tool "
        "environment come next, so that offline policies and live models share one seam. The "
        "harness, metrics, failure analysis, statistics, and optimizer then operate on recorded "
        "trajectories without calling agents again."
    )
    b.section("System Architecture")
    b.paragraph(
        "Fig. 4.1 shows four layers. Inputs are a task suite and an agent. The execution layer "
        "runs trials through a fault-injecting environment. The analysis layer reads "
        "trajectories only. The output layer compares, optimizes, stores, and reports."
    )
    b.figure(DIAGRAMS / "architecture.png", "System architecture of Agent Reliability Lab", width=5.6, max_height=6.0)
    b.section("Overview of Modules")
    b.table(
        [
            ("Module", "Functionality"),
            ("Domain types and agent seam", "Task, Step, Trajectory, Score, RunMetrics, FailureReport; any agent with name and run(task)"),
            ("Tool environment", "Mock tools, seeded fault policy (timeouts, outages, fail-first), recorder of steps"),
            ("Evaluation harness", "Every variant on every task for k trials; timing; crash capture; pass@k, pass^k, consistency"),
            ("Metrics and scorers", "Exact, normalized, numeric, regex scorers; cost, latency, tokens, recovery, steps"),
            ("Failure analysis", "Five failure modes with evidence, root cause, unclassified outcome"),
            ("Statistics", "Wilson and bootstrap intervals; exact McNemar paired test"),
            ("Optimizer", "Grid sweep, Pareto front, cheapest setting meeting a target"),
            ("Suites and baselines", "YAML task suites; reference agents with planted defects; classifier self-check"),
            ("Store, reports, CLI", "SQLite and JSON Lines; HTML and Markdown reports; relai commands; LLM adapter"),
        ],
        [2.1, 4.3],
        "Modules of the proposed system",
        size=12,
    )
    b.section("Use Cases")
    b.paragraph(
        "The primary actor is a researcher or developer who defines suites, configures faults, "
        "plugs in agents, runs evaluations, compares variants, and sweeps settings. The agent "
        "under test is a secondary actor that only produces trajectories; a model API is used "
        "by live agents (Fig. 4.2)."
    )
    b.figure(DIAGRAMS / "usecase.png", "Use case diagram", width=6.2, max_height=5.6)
    b.section("Entity-Relationship Model")
    b.paragraph(
        "Results persist in a database whose entities mirror the in-memory reports. An "
        "experiment contains variants, a variant produces runs, and each run records steps and "
        "diagnosed failure modes (Fig. 4.3). Each run also keeps its complete record as JSON, "
        "so stored experiments reload without loss."
    )
    b.figure(DIAGRAMS / "er.png", "Entity-relationship model of the run store", width=6.2)
    b.section("Data Flow Diagrams")
    b.paragraph(
        "The context diagram (Fig. 4.4) shows the researcher, the agent under test, and an "
        "optional model API around the laboratory. The level 1 diagram (Fig. 4.5) divides the "
        "laboratory into six processes and four data stores."
    )
    b.figure(DIAGRAMS / "dfd0.png", "Level 0 data flow diagram", width=6.2)
    b.figure(DIAGRAMS / "dfd1.png", "Level 1 data flow diagram", width=5.6, max_height=5.0)
    b.section("Flowcharts of Core Processes")
    b.paragraph(
        "Fig. 4.6 is the classifier: five detectors run, the earliest evidence becomes the root "
        "cause, and an unexplained failure stays unclassified. Fig. 4.7 is the evaluation loop: "
        "for every variant, task, and trial the harness times the agent, records crashes as "
        "failed runs, and scores, measures, and classifies each trajectory. Fig. 4.8 is the "
        "configuration search."
    )
    b.figure(DIAGRAMS / "classifier.png", "Flowchart of failure classification", width=5.6)
    b.figure(DIAGRAMS / "flow_harness.png", "Flowchart of the evaluation harness", width=4.2, max_height=7.4)
    b.figure(DIAGRAMS / "flow_sweep.png", "Flowchart of configuration search", width=4.6, max_height=5.6)
    b.section("Core Algorithms and Implementation Plan")
    b.bullets([
        "**Seeded fault schedule:** the n-th call to a tool in trial t of a task draws u = h(seed, task, t, tool, n); the call times out when u is below the timeout rate. The draw never depends on the agent, so every agent meets the same faults.",
        "**Reliability estimators:** with c successes in n trials, pass@k = 1 - C(n-c, k) / C(n, k) and pass^k = C(c, k) / C(n, k).",
        "**Paired comparison:** runs of two agents are paired by task and trial, and the exact McNemar test uses the pairs where only one agent succeeded.",
        "**Selection:** the Pareto front over success, cost, and latency, then the cheapest setting whose success meets the target.",
    ])
    b.paragraph(
        "Development follows a test-first plan: domain types and the agent seam, then metrics and "
        "the failure rules with fixtures, then the fault environment and trials, then statistics, "
        "optimization, storage, reports, and the command-line interface (Fig. 4.9)."
    )
    b.figure(DIAGRAMS / "gantt.png", "Project schedule (Gantt chart)", width=6.2)


def feasibility(b: Builder) -> None:
    b.chapter("Feasibility Study")
    b.paragraph(
        "Feasibility is the first step of software engineering: whether the laboratory is "
        "needed, whether it can be built with the available skills and tools, and whether it can "
        "be completed in the project calendar."
    )
    b.section("Technical Feasibility")
    b.paragraph(
        "The stack is mature and already taught in the department: Python, Pydantic, pytest, "
        "SQLite, and YAML. No GPU, distributed system, or paid service is required. Offline "
        "reference agents remove the dependence on model APIs during development, and the "
        "failure rules are deterministic predicates over steps that are easy to test. A working "
        "prototype already runs about 6,500 scored runs per second on a laptop."
    )
    b.section("Operational Feasibility")
    b.paragraph(
        "Users install the package in a virtual environment and run one command per experiment. "
        "Results appear as terminal tables, JSON, or a standalone HTML report that supervisors "
        "can read without extra software. Later batches can plug in their own agents through the "
        "same interface."
    )
    b.section("Economic Feasibility")
    b.paragraph(
        "All tools are free and open source, and the package is MIT licensed. Offline experiments "
        "cost nothing. When live models are used, cost is itself a measured quantity, so "
        "expensive configurations are visible, and local models through Ollama keep cost at zero."
    )
    b.section("Schedule Feasibility")
    b.paragraph(
        "Every module has a testable exit criterion, and work can proceed without model access "
        "because analysis never calls agents. The main risk is scope growth; it is controlled by "
        "the rule that a new failure mode is added only with a test, and that agents attach "
        "through one interface."
    )
    b.section("Need and Significance")
    b.paragraph(
        "Agents are entering products, internships, and coursework, yet teams still compare them "
        "by anecdote or by a single success rate. A shared laboratory makes those comparisons "
        "fair, repeatable, and explainable. For the department it is a reusable evaluation asset; "
        "for students it is practice in experimental design, metric definition, and evidence-based "
        "failure analysis."
    )


def facilities(b: Builder) -> None:
    b.chapter("Facilities Required for Proposed Work")
    b.paragraph("The work is software-intensive and needs no special laboratory instrument.")
    b.table(
        [
            ("Category", "Item", "Purpose"),
            ("Hardware", "Laptop or lab PC, 8 GB RAM, 20 GB free disk, CPU only", "Development, tests, demonstration"),
            ("Operating system", "Linux, macOS, or Windows", "Any platform with Python"),
            ("Language", "Python 3.11 or newer, venv, pip", "Implementation"),
            ("Libraries", "Pydantic 2, PyYAML", "Typed models, task suites"),
            ("Development", "pytest, Ruff, Git, GitHub Actions", "Tests, lint, version control, CI"),
            ("Documentation", "LaTeX, Word or LibreOffice", "Synopsis, report, paper"),
            ("Optional", "OpenAI-compatible API key or Ollama", "Live LLM experiments"),
            ("Data", "Built-in task suites", "Repeatable experiments without downloads"),
        ],
        [1.4, 2.8, 2.2],
        "Facilities required",
        size=12,
    )
    b.paragraph(
        "A GPU is not required. A machine with more memory helps only if a large local model is "
        "served with Ollama. Internet access is needed for installing packages and for hosted "
        "models, not for offline experiments."
    )
    b.paragraph(
        "**Human resources and time.** The work is carried out by a team of three students under "
        "the supervision of a faculty member, over two semesters: the design and core "
        "implementation in semester VII and the live model study, extensions, and final report "
        "in semester VIII. Institute laboratory PCs are sufficient for the viva demonstration."
    )


def conclusion(b: Builder) -> None:
    b.chapter("Conclusion")
    b.paragraph(
        "This synopsis proposes Agent Reliability Lab, a crash-test laboratory for AI agents, as a "
        "final-year project of the Department of Computer Science and Engineering, Noida "
        "Institute of Engineering and Technology. The work addresses a concrete gap: teams can "
        "see whether an agent finished a task, but rarely why it failed, how consistently it "
        "succeeds, or what its reliability costs."
    )
    b.paragraph(
        "The proposed method keeps the agent interface small, injects tool faults on a seeded "
        "schedule shared by all variants, runs repeated trials, derives metrics only from "
        "trajectories, explains failures with evidence while leaving unknown failures "
        "unclassified, compares variants with paired tests, and recommends the cheapest reliable "
        "setting. Use cases, the entity-relationship model, data flow diagrams, and flowcharts "
        "show how the parts connect, and the feasibility study is favorable on every axis."
    )
    b.paragraph(
        "A working implementation already validates the design: with reference agents, the "
        "measured effect of faults matches its closed-form expectation and the classifier "
        "recovers every planted defect. The next phase evaluates live LLM agents and adds more "
        "suites and fault kinds. The outcome is not another chatbot but a reliability "
        "instrument that later batches can extend."
    )
    b.paragraph("The expected outcomes of the completed project are:")
    b.bullets([
        "An installable, tested Python package and a failure taxonomy validated with planted defects.",
        "Reproducible experiments comparing live LLM agents under identical faults, and a research paper.",
    ])


REFERENCES = [
    '[1] S. Yao, J. Zhao, D. Yu, N. Du, I. Shafran, K. Narasimhan, Y. Cao, "ReAct: Synergizing Reasoning and Acting in Language Models", ICLR, 2023.',
    '[2] X. Liu et al., "AgentBench: Evaluating LLMs as Agents", ICLR, 2024.',
    '[3] G. Mialon et al., "GAIA: A Benchmark for General AI Assistants", ICLR, 2024.',
    '[4] C. E. Jimenez et al., "SWE-bench: Can Language Models Resolve Real-World GitHub Issues?", ICLR, 2024.',
    '[5] S. Zhou et al., "WebArena: A Realistic Web Environment for Building Autonomous Agents", ICLR, 2024.',
    '[6] S. Yao, N. Shinn, P. Razavi, K. Narasimhan, "tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains", arXiv:2406.12045, 2024.',
    '[7] S. Kapoor, B. Stroebl, Z. S. Siegel, N. Nadgir, A. Narayanan, "AI Agents That Matter", arXiv:2407.01502, 2024.',
    '[8] S. Kapoor et al., "Holistic Agent Leaderboard: The Missing Infrastructure for AI Agent Evaluation", ICLR, 2026.',
    '[9] S. Rabanser, S. Kapoor, P. Kirgis, K. Liu, S. Utpala, A. Narayanan, "Towards a Science of AI Agent Reliability", ICML, PMLR 306, 2026.',
    '[10] "ToolMisuseBench: An Offline Deterministic Benchmark for Tool Misuse and Recovery in Agentic Systems", arXiv:2604.01508, 2026.',
    '[11] "Beyond Function Calling: Benchmarking Tool-Using Agents under Tool-Environment Unreliability", arXiv:2606.25819, 2026.',
    '[12] "AgentChaos: Chaos Engineering for Agent Systems via Programmatic Fault Injection", arXiv:2608.06790, 2026.',
    '[13] M. Cemri et al., "Why Do Multi-Agent LLM Systems Fail?", arXiv:2503.13657, 2025.',
    '[14] D. Deshpande, V. Gangal, H. Mehta, J. Krishnan, A. Kannappan, R. Qian, "TRAIL: Trace Reasoning and Agentic Issue Localization", arXiv:2505.08638, 2025.',
    '[15] S. Zhang et al., "Which Agent Causes Task Failures and When? On Automated Failure Attribution of LLM Multi-Agent Systems", ICML, PMLR 267, 2025.',
    '[16] P. Liang et al., "Holistic Evaluation of Language Models", Transactions on Machine Learning Research, 2023.',
    '[17] UK AI Security Institute, "Inspect: A Framework for Large Language Model Evaluations", 2024.',
    '[18] M. Chen et al., "Evaluating Large Language Models Trained on Code", arXiv:2107.03374, 2021.',
    '[19] A. Basiri et al., "Chaos Engineering", IEEE Software, vol. 33, no. 3, pp. 35-41, 2016.',
    '[20] Q. McNemar, "Note on the Sampling Error of the Difference Between Correlated Proportions or Percentages", Psychometrika, vol. 12, no. 2, pp. 153-157, 1947.',
    '[21] E. B. Wilson, "Probable Inference, the Law of Succession, and Statistical Inference", Journal of the American Statistical Association, vol. 22, no. 158, pp. 209-212, 1927.',
    '[22] R. S. Pressman, B. R. Maxim, "Software Engineering: A Practitioner\'s Approach", 9th ed., McGraw-Hill, 2020.',
]


def references(b: Builder) -> None:
    b.chapter("References")
    for ref in REFERENCES:
        b.paragraph(ref, size=12, align="left", after=5, line=1.1)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "Synopsis_Agent_Reliability_Lab.docx"
    pdf = build_twice(make, out)
    print(f"wrote {out} and {pdf}")


if __name__ == "__main__":
    main()
