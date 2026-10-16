"""Build the Design/Implementation Phase progress review deck from the institute template.

    /path/to/venv-with-python-pptx/bin/python academic/progress-review/build_ppt.py \
        [docs/Project_PPT_template.pptx]

The template stays on each member's machine (docs/ is not tracked). The deck
follows its content format: headings Arial 32 centred, subheadings Arial 18 bold,
text Arial 16, references Times New Roman 12. Speaker notes name the presenter.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DIAGRAMS = ROOT / "academic" / "diagrams"
SNAPS = ROOT / "academic" / "snapshots"
OUTPUT = HERE / "Progress_Review_PPT.pptx"

PURPLE = RGBColor(0x7A, 0x1F, 0x86)
INK = RGBColor(0x1F, 0x29, 0x33)
MUTED = RGBColor(0x48, 0x65, 0x81)

LEFT, RIGHT = 1.35, 12.15
TOP = 1.55
BOTTOM = 7.0

MEMBERS = [
    ("Suryansh Singh", "2301330100208", "Team Lead: architecture, harness, fault injection, store, CLI"),
    ("Simran Kumari", "2301330100200", "Metrics, failure analysis, statistics, optimization"),
    ("Tanishka Sahu", "2301330100210", "Task suites, baseline agents, reports, testing"),
]


def main() -> None:
    template = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "Project_PPT_template.pptx"
    prs = Presentation(str(template))
    title_slide, index_slide, format_slide, thanks_slide, feedback_slide = list(prs.slides)
    content_layout = prs.slide_layouts[1]
    title_only = prs.slide_layouts[5]

    _fill_title_slide(title_slide)
    _fill_index(index_slide)
    _notes(title_slide, "Suryansh", "Greet the panel. Group G053, Agent Reliability Lab, supervisor Mr. Pradeep Kumar. Introduce Simran and Tanishka and say who presents which part.")
    _notes(index_slide, "Suryansh", "Walk the agenda in one breath: requirements, design diagrams, implementation with code and output, results, paper status.")

    built = [title_slide, index_slide]

    s = _content_slide(prs, content_layout, "Problem, Idea and Objectives")
    _text(s, LEFT, TOP, RIGHT - LEFT, BOTTOM - TOP, [
        ("sub", "The problem"),
        ("bullet", "AI agents now plan, call tools, and retry, yet benchmarks report one number: did the agent finish?"),
        ("bullet", "That number hides why runs fail, how consistent the agent is, and what reliability costs."),
        ("sub", "Our idea: a crash-test lab for AI agents"),
        ("bullet", "Break tools on purpose, the same way for every agent, and run every task several times."),
        ("bullet", "Explain each failed run with evidence, then pick the cheapest setup that stays reliable."),
        ("sub", "Objectives and status"),
        ("bullet", "O1 Evaluate: success, pass^k, consistency, cost, latency, recovery, steps (done)"),
        ("bullet", "O2 Explain: five failure modes with evidence, seeded fault injection (done)"),
        ("bullet", "O3 Optimize: paired tests, Pareto front, cheapest reliable setting (done; live LLM study next)"),
    ])
    _notes(s, "Suryansh", "One sentence problem, one sentence idea. Stress that pass or fail hides the reason. Map each objective from the synopsis to what is now implemented.")
    built.append(s)

    s = _content_slide(prs, title_only, "Proposed System")
    _picture(s, DIAGRAMS / "architecture.png", LEFT, TOP, 6.3, BOTTOM - TOP)
    _text(s, 7.85, TOP + 0.1, RIGHT - 7.85, BOTTOM - TOP, [
        ("sub", "Four layers"),
        ("bullet", "Inputs: YAML task suites with mock tools and faults, and any agent with name + run(task)"),
        ("bullet", "Execution: the harness runs every variant x task x trial; ToolEnv injects seeded faults"),
        ("bullet", "Analysis: scorers, metrics, and the failure classifier only read trajectories"),
        ("bullet", "Output: ranking with confidence intervals, paired test, Pareto sweep, SQLite store, HTML report"),
        ("sub", "Runs anywhere"),
        ("bullet", "Offline, CPU only, no API key; live LLMs plug in through an OpenAI-compatible adapter"),
    ], size=14)
    _notes(s, "Suryansh", "Point at each layer top to bottom. Key design rule: only the execution layer calls agents, so every number can be recomputed from stored runs.")
    built.append(s)

    s = _content_slide(prs, title_only, "Software Requirement Analysis")
    half = (RIGHT - LEFT - 0.3) / 2
    _text(s, LEFT, TOP, half, BOTTOM - TOP, [
        ("sub", "Functional requirements"),
        ("bullet", "FR1 Load suites (YAML/JSON) with tools, faults, step budgets"),
        ("bullet", "FR2 Run any agent through name + run(task)"),
        ("bullet", "FR3 Inject reproducible timeouts, outages, fail-first faults"),
        ("bullet", "FR4 Repeat tasks k times; report pass@k, pass^k, consistency"),
        ("bullet", "FR5 Score answers: exact, normalized, numeric, regex"),
        ("bullet", "FR6 Diagnose failures with evidence; keep unknowns unclassified"),
        ("bullet", "FR7 Compare variants with intervals and a paired test"),
        ("bullet", "FR8 Sweep settings; return Pareto front and recommendation"),
        ("bullet", "FR9 Store runs (SQLite, JSONL); render HTML and Markdown"),
        ("bullet", "FR10 Offer a CLI and a Python API"),
    ], size=13)
    _text(s, LEFT + half + 0.3, TOP, half, BOTTOM - TOP, [
        ("sub", "Non-functional requirements"),
        ("bullet", "Reproducibility: same seed, same faults, same numbers"),
        ("bullet", "Fairness: every variant meets the identical fault schedule"),
        ("bullet", "Performance: about 6,500 scored runs per second; 81 tests in under 1 s"),
        ("bullet", "Portability: Python 3.11 to 3.13, any OS, 2 runtime dependencies"),
        ("bullet", "Extensibility: new agents, scorers, suites, modes without harness changes"),
        ("bullet", "Robustness: an agent crash becomes a failed run, not a crashed experiment"),
        ("bullet", "Security: no eval(), escaped HTML, offline by default"),
        ("bullet", "Maintainability: typed models, lint, CI on three Python versions"),
    ], size=13)
    _notes(s, "Tanishka", "Read two or three FRs aloud, not all ten. For NFRs, explain fairness: the same fault hits every agent, which is what makes comparisons valid.")
    built.append(s)

    s = _content_slide(prs, title_only, "Major Modules and Functionalities")
    _table(s, LEFT, TOP + 0.05, RIGHT - LEFT, [
        ("Module", "What it does", "Owner"),
        ("Domain types and agent seam", "Task, Step, Trajectory; FunctionAgent, ScriptedAgent", "Suryansh"),
        ("Tool environment", "Tools, seeded FaultPolicy, Recorder of steps", "Suryansh"),
        ("Evaluation harness", "Trials, timing, crash capture, pass@k, pass^k, experiments", "Suryansh"),
        ("Metrics and scorers", "Cost, latency, tokens, recovery, horizon; five scorers", "Simran"),
        ("Failure analysis", "Five modes, root cause, evidence, unclassified", "Simran"),
        ("Statistics and optimizer", "Wilson, bootstrap, McNemar; sweep, Pareto, recommend", "Simran"),
        ("Suites and baseline agents", "YAML suites, planted-defect agents, classifier self-check", "Tanishka"),
        ("Reports and tests", "HTML and Markdown reports, 81 tests, examples", "Tanishka"),
        ("Store, CLI, LLM adapter", "SQLite and JSONL, relai commands, OpenAI-compatible agent", "Suryansh"),
    ], [3.3, 5.6, 1.9], size=13)
    _notes(s, "Tanishka", "Each row is a file in src/relai. Mention owners so the panel knows whom to ask. Total: about 3,300 lines of code and 1,100 lines of tests.")
    built.append(s)

    s = _content_slide(prs, title_only, "Class Design")
    _picture(s, DIAGRAMS / "class.png", LEFT, TOP - 0.15, RIGHT - LEFT, BOTTOM - TOP + 0.2)
    _notes(s, "Suryansh", "Left: trajectory data. Middle: RunResult composes Score, RunMetrics, FailureReport; EvalReport and ExperimentReport group them. Right: every agent implements the Agent protocol; baselines inherit PolicyAgent.")
    built.append(s)

    s = _content_slide(prs, title_only, "Sequence Diagram: relai run")
    _picture(s, DIAGRAMS / "sequence.png", LEFT, TOP - 0.1, RIGHT - LEFT, BOTTOM - TOP + 0.15)
    _notes(s, "Suryansh", "Follow one run: CLI loads the suite, harness loops variant x task x trial, the tool session decides the fault from the seed, analysis scores and classifies, then stats and reports.")
    built.append(s)

    s = _content_slide(prs, title_only, "Data Flow Diagrams: Level 0 and Level 1")
    _picture(s, DIAGRAMS / "dfd0.png", LEFT, TOP + 0.6, 4.3, 2.4)
    _caption(s, LEFT, TOP + 2.45, 4.3, "Level 0: context diagram")
    _picture(s, DIAGRAMS / "dfd1.png", 5.85, TOP - 0.1, RIGHT - 5.85, BOTTOM - TOP + 0.1)
    _caption(s, LEFT, TOP + 3.1, 4.3, "Level 1: six processes and four data stores. Analysis reads stored run results, never the agent.")
    _notes(s, "Tanishka", "Level 0 shows the researcher, the agent under test, and an optional model API. Level 1 splits the lab into load, execute, score, classify, compare, and store.")
    built.append(s)

    s = _content_slide(prs, title_only, "Database Design: ER Diagram")
    _picture(s, DIAGRAMS / "er.png", LEFT, TOP + 0.1, RIGHT - LEFT, 4.7)
    _caption(s, LEFT, BOTTOM - 0.55, RIGHT - LEFT, "SQLite run store: experiments contain variants, variants produce runs, runs record steps and failure modes. result_json keeps each run lossless.")
    _notes(s, "Tanishka", "One-to-many all the way down. Foreign keys cascade on delete. The steps and failures tables exist so failure counts can be queried in SQL.")
    built.append(s)

    s = _content_slide(prs, title_only, "Gantt Chart")
    _picture(s, DIAGRAMS / "gantt.png", LEFT, TOP - 0.05, RIGHT - LEFT, BOTTOM - TOP + 0.1)
    _notes(s, "Tanishka", "Green is done, amber is planned. We are at the red line: design and v0.2 implementation are complete; live LLM experiments and the paper results come next.")
    built.append(s)

    s = _content_slide(prs, title_only, "Implementation of Core Algorithms")
    _text(s, LEFT, TOP, 5.2, BOTTOM - TOP, [
        ("bullet", "Fault schedule: u = hash(seed, task, trial, tool, call n); timeout if u < p. Every agent meets the same faults."),
        ("bullet", "Repeated trials: pass^k = C(c,k) / C(n,k) for c passes in n trials; pass@k = 1 - C(n-c,k) / C(n,k)."),
        ("bullet", "Classification: five detectors; root cause = mode with the earliest evidence; no match means unclassified."),
        ("bullet", "Paired test: exact McNemar on runs that only one variant passed."),
        ("bullet", "Optimization: keep the Pareto front over success, cost, latency; recommend the cheapest setting that meets the target."),
    ], size=14)
    _picture(s, DIAGRAMS / "classifier.png", 6.75, TOP + 0.1, RIGHT - 6.75, BOTTOM - TOP - 0.1)
    _notes(s, "Simran", "Explain why pass^k matters: 0.77 success can mean only 0.33 of tasks pass all five times. Walk the flowchart: detectors, earliest evidence wins, unknown stays unknown.")
    built.append(s)

    s = _content_slide(prs, title_only, "Code Snapshots: Fault Injection and Retry")
    _picture(s, SNAPS / "code_fault_policy.png", LEFT + 0.55, TOP, 9.6, 2.55)
    _picture(s, SNAPS / "code_retry_agent.png", LEFT + 0.55, TOP + 2.7, 9.6, 2.65)
    _notes(s, "Suryansh", "Top: the fault depends only on seed, task, trial, tool, and call number, never on the agent. Bottom: the retry agent retries only environment faults, with optional backoff.")
    built.append(s)

    s = _content_slide(prs, title_only, "Code Snapshots: Evaluation Loop and Statistics")
    _picture(s, SNAPS / "code_evaluate_1.png", LEFT, TOP - 0.05, 5.75, BOTTOM - TOP + 0.05)
    right = LEFT + 5.95
    _picture(s, SNAPS / "code_evaluate_2.png", right, TOP + 0.1, RIGHT - right, 1.5)
    _picture(s, SNAPS / "code_evaluate_3.png", right, TOP + 1.75, RIGHT - right, 1.2)
    _picture(s, SNAPS / "code_mcnemar_1.png", right, TOP + 3.1, RIGHT - right, 1.3)
    _notes(s, "Simran", "Left: the harness loop passes trial and seed through task metadata and turns crashes into failed runs. Right: the two estimators and the exact McNemar p-value.")
    built.append(s)

    s = _content_slide(prs, title_only, "Implementation Output")
    _picture(s, SNAPS / "term_run.png", LEFT, TOP, RIGHT - LEFT, 3.1)
    _picture(s, SNAPS / "term_tests.png", LEFT, TOP + 3.25, 4.9, 1.6)
    _text(s, LEFT + 5.2, TOP + 3.2, RIGHT - LEFT - 5.2, 1.9, [
        ("bullet", "30% of tool calls time out, 12 tasks, 5 trials each"),
        ("bullet", "Naive agent: 0.58 success but pass^5 only 0.25"),
        ("bullet", "Three retries: 1.00 success, about 2x cost and latency"),
        ("bullet", "McNemar p = 0.0001: the difference is real"),
    ], size=14)
    _notes(s, "Tanishka", "Live demo if time allows: relai run reliability --agent naive --agent retry:1 --agent retry:3 --trials 5 --timeout-rate 0.3. Otherwise read this table. Then show 81 tests and lint passing.")
    built.append(s)

    s = _content_slide(prs, title_only, "Preliminary Results")
    _picture(s, DIAGRAMS / "stress_plot.png", LEFT, TOP, 4.75, 3.75)
    _caption(s, LEFT, TOP + 3.75, 4.75, "Success (solid) and pass^5 (dashed) as timeouts rise")
    _picture(s, SNAPS / "term_selfcheck.png", LEFT + 4.95, TOP, RIGHT - LEFT - 4.95, 2.0)
    _text(s, LEFT + 4.95, TOP + 2.15, RIGHT - LEFT - 4.95, 2.9, [
        ("bullet", "Classifier self-check: every planted defect is found, precision 1.00 for all four modes"),
        ("bullet", "Fault injector matches theory: success (1 - p)^L, e.g. 0.33 measured vs 0.34 expected for 3 calls"),
        ("bullet", "Sweep: 2 retries is the cheapest setting with success >= 0.95"),
    ], size=14)
    _notes(s, "Simran", "Be clear these are offline reference agents: they validate the instrument, they do not rank LLMs. Live model runs are the next phase.")
    built.append(s)

    s = _content_slide(prs, title_only, "Research Paper and Work Status")
    half = (RIGHT - LEFT - 0.3) / 2
    _text(s, LEFT, TOP, half, BOTTOM - TOP, [
        ("sub", "First research paper (IEEE format)"),
        ("para", "Agent Reliability Lab: Controlled Fault Injection and Evidence-Based Failure Analysis for Tool-Using Language Agents"),
        ("bullet", "Done: Abstract, Introduction, Related Work, Problem Statement, Proposed Methodology"),
        ("bullet", "Added: preliminary results with 3 tables and 3 figures"),
        ("bullet", "Next: live LLM results, then submission"),
    ], size=14)
    _text(s, LEFT + half + 0.3, TOP, half, BOTTOM - TOP, [
        ("sub", "Done"),
        ("bullet", "v0.2 package: 17 modules, 81 tests, CI, docs"),
        ("bullet", "SRS, class, sequence, DFD, ER, Gantt"),
        ("sub", "Next (Oct to Dec)"),
        ("bullet", "Live LLM study: hosted and local models"),
        ("bullet", "Suites adapted from public benchmarks"),
        ("bullet", "More fault kinds: rate limits, corrupted outputs"),
        ("bullet", "Semester VIII: dashboard, trace import, release 1.0"),
    ], size=14)
    _notes(s, "Suryansh", "Hand over the hard copy of the paper here. Be honest about what is next: the instrument is finished, the live model study is the next milestone.")
    built.append(s)

    s = _content_slide(prs, title_only, "References")
    _references(s, [
        "[1] S. Yao, J. Zhao, D. Yu et al., \"ReAct: Synergizing Reasoning and Acting in Language Models\", ICLR, 2023.",
        "[2] S. Yao, N. Shinn, P. Razavi, K. Narasimhan, \"tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains\", arXiv:2406.12045, 2024.",
        "[3] S. Kapoor, B. Stroebl, Z. S. Siegel, N. Nadgir, A. Narayanan, \"AI Agents That Matter\", arXiv:2407.01502, 2024.",
        "[4] S. Kapoor et al., \"Holistic Agent Leaderboard: The Missing Infrastructure for AI Agent Evaluation\", ICLR, 2026.",
        "[5] S. Rabanser, S. Kapoor, P. Kirgis et al., \"Towards a Science of AI Agent Reliability\", ICML, 2026.",
        "[6] M. Cemri et al., \"Why Do Multi-Agent LLM Systems Fail?\", arXiv:2503.13657, 2025.",
        "[7] \"ToolMisuseBench: An Offline Deterministic Benchmark for Tool Misuse and Recovery in Agentic Systems\", arXiv:2604.01508, 2026.",
        "[8] \"AgentChaos: Chaos Engineering for Agent Systems via Programmatic Fault Injection\", arXiv:2608.06790, 2026.",
        "[9] M. Chen et al., \"Evaluating Large Language Models Trained on Code\", arXiv:2107.03374, 2021.",
        "[10] Q. McNemar, \"Note on the Sampling Error of the Difference Between Correlated Proportions or Percentages\", Psychometrika, 1947.",
        "[11] E. B. Wilson, \"Probable Inference, the Law of Succession, and Statistical Inference\", J. Amer. Statist. Assoc., 1927.",
        "[12] A. Basiri et al., \"Chaos Engineering\", IEEE Software, vol. 33, no. 3, 2016.",
    ])
    _notes(s, "Simran", "No need to read these. Mention that the paper cites 25 sources and positions the work against 2025 and 2026 reliability research.")
    built.append(s)

    _notes(thanks_slide, "Suryansh", "Thank the panel and invite questions. Each member answers questions on the modules they own.")
    _notes(feedback_slide, "All", "Leave blank; write the panel's feedback here after the review.")
    built += [thanks_slide, feedback_slide]

    _drop_slide(prs, format_slide)
    _reorder(prs, built)
    prs.save(str(OUTPUT))
    print(f"wrote {OUTPUT} with {len(prs.slides)} slides")


def _fill_title_slide(slide) -> None:
    title, body = slide.placeholders[0], slide.placeholders[1]
    _set_title(title, "Agent Reliability Lab")
    frame = body.text_frame
    lines = [
        ("Controlled Fault Injection and Failure Analysis for AI Agents", 16, False, INK),
        ("Department of Computer Science and Engineering", 16, False, INK),
        ("(Supervisor: Mr. Pradeep Kumar)", 16, True, PURPLE),
    ]
    for i, (text, size, bold, color) in enumerate(lines):
        para = frame.paragraphs[i] if i < len(frame.paragraphs) else frame.add_paragraph()
        _clear(para)
        para.alignment = PP_ALIGN.CENTER
        para.space_before = Pt(0)
        para.space_after = Pt(3)
        para.line_spacing = 1.0
        _no_bullet(para)
        run = para.add_run()
        run.text = text
        _font(run, size, bold, color)
    for para in list(frame.paragraphs)[len(lines):]:
        para._p.getparent().remove(para._p)

    table = next(shape for shape in slide.shapes if shape.has_table).table
    rows = list(table.rows)
    for row, (name, roll, role) in zip(rows[1:], MEMBERS, strict=False):
        for cell, value in zip(row.cells, (name, roll, role), strict=True):
            cell.text = value
            for para in cell.text_frame.paragraphs:
                para.alignment = PP_ALIGN.CENTER
                for run in para.runs:
                    _font(run, 12, False, INK)
    for row in rows[1 + len(MEMBERS):]:
        row._tr.getparent().remove(row._tr)

    box = slide.shapes.add_textbox(Inches(2.5), Inches(4.56), Inches(8.86), Inches(0.36))
    para = box.text_frame.paragraphs[0]
    para.alignment = PP_ALIGN.CENTER
    run = para.add_run()
    run.text = "Design/Implementation Phase Progress Review  |  Group CSE/CSPROJECT/2027/G053  |  17 October 2026"
    _font(run, 11, False, MUTED)


def _fill_index(slide) -> None:
    _set_title(slide.placeholders[0], "Index", center=False)
    frame = slide.placeholders[1].text_frame
    items = [
        "Problem, Idea and Objectives",
        "Proposed System",
        "Software Requirement Analysis and Modules",
        "Design: Class, Sequence, DFD, ER, Gantt",
        "Implementation: Algorithms and Code Snapshots",
        "Implementation Output and Preliminary Results",
        "Research Paper and Work Status",
        "References",
    ]
    paragraphs = list(frame.paragraphs)
    first = next((p for p in paragraphs if p.text.strip()), paragraphs[0])
    template_p = copy.deepcopy(first._p)
    for para in paragraphs:
        para._p.getparent().remove(para._p)
    body = frame._txBody
    for item in items:
        p = copy.deepcopy(template_p)
        body.append(p)
    for para, item in zip(frame.paragraphs, items, strict=True):
        _clear(para)
        run = para.add_run()
        run.text = item
        _font(run, 16, False, INK)


def _content_slide(prs, layout, title: str):
    slide = prs.slides.add_slide(layout)
    title_shape = slide.placeholders[0]
    title_shape.left, title_shape.width = Inches(LEFT), Inches(RIGHT - LEFT)
    title_shape.top, title_shape.height = Inches(0.5), Inches(0.95)
    _set_title(title_shape, title)
    for shape in list(slide.placeholders):
        if shape.placeholder_format.idx not in (0,):
            if shape.placeholder_format.type not in (15, 16, 13):
                shape._element.getparent().remove(shape._element)
    return slide


def _set_title(shape, text: str, *, center: bool = True) -> None:
    frame = shape.text_frame
    frame.clear()
    para = frame.paragraphs[0]
    para.alignment = PP_ALIGN.CENTER if center else PP_ALIGN.LEFT
    run = para.add_run()
    run.text = text
    _font(run, 32, False, PURPLE)


def _text(slide, left, top, width, height, items, *, size: int = 16) -> None:
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    frame = box.text_frame
    frame.word_wrap = True
    first = True
    for kind, text in items:
        para = frame.paragraphs[0] if first else frame.add_paragraph()
        first = False
        if kind == "sub":
            para.space_before = Pt(10)
            para.space_after = Pt(4)
            run = para.add_run()
            run.text = text
            _font(run, 18, True, INK)
        elif kind == "para":
            para.space_after = Pt(6)
            run = para.add_run()
            run.text = text
            _font(run, size, False, INK)
        else:
            para.space_after = Pt(5)
            _bullet(para)
            run = para.add_run()
            run.text = text
            _font(run, size, False, INK)


def _caption(slide, left, top, width, text: str) -> None:
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(0.5))
    frame = box.text_frame
    frame.word_wrap = True
    para = frame.paragraphs[0]
    para.alignment = PP_ALIGN.CENTER
    run = para.add_run()
    run.text = text
    _font(run, 12, False, MUTED)


def _picture(slide, path: Path, left, top, max_w, max_h) -> None:
    width, height = Image.open(path).size
    scale = min(max_w / width, max_h / height)
    w, h = width * scale, height * scale
    x = left + (max_w - w) / 2
    slide.shapes.add_picture(str(path), Inches(x), Inches(top), Inches(w), Inches(h))


def _table(slide, left, top, width, rows, col_widths, *, size: int = 13) -> None:
    shape = slide.shapes.add_table(
        len(rows), len(rows[0]), Inches(left), Inches(top), Inches(width), Inches(0.42 * len(rows))
    )
    table = shape.table
    for i, w in enumerate(col_widths):
        table.columns[i].width = Inches(w)
    for r, values in enumerate(rows):
        for c, value in enumerate(values):
            cell = table.cell(r, c)
            cell.text = value
            for para in cell.text_frame.paragraphs:
                for run in para.runs:
                    _font(run, size, r == 0, RGBColor(0xFF, 0xFF, 0xFF) if r == 0 else INK)


def _references(slide, refs) -> None:
    box = slide.shapes.add_textbox(Inches(LEFT), Inches(TOP - 0.1), Inches(RIGHT - LEFT), Inches(BOTTOM - TOP))
    frame = box.text_frame
    frame.word_wrap = True
    for i, ref in enumerate(refs):
        para = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        para.space_after = Pt(3)
        run = para.add_run()
        run.text = ref
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        run.font.color.rgb = INK


def _notes(slide, presenter: str, text: str) -> None:
    slide.notes_slide.notes_text_frame.text = f"Presenter: {presenter}\n{text}"


def _font(run, size, bold, color) -> None:
    run.font.name = "Arial"
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def _clear(para) -> None:
    for run in list(para.runs):
        run._r.getparent().remove(run._r)
    for br in para._p.findall(qn("a:br")):
        para._p.remove(br)


def _no_bullet(para) -> None:
    ppr = para._p.get_or_add_pPr()
    for tag in ("a:buChar", "a:buAutoNum", "a:buNone"):
        for el in ppr.findall(qn(tag)):
            ppr.remove(el)
    ppr.append(ppr.makeelement(qn("a:buNone"), {}))
    ppr.set("indent", "0")
    ppr.set("marL", "0")


def _bullet(para) -> None:
    ppr = para._p.get_or_add_pPr()
    ppr.set("marL", "285750")
    ppr.set("indent", "-285750")
    color = ppr.makeelement(qn("a:buClr"), {})
    srgb = color.makeelement(qn("a:srgbClr"), {"val": "7A1F86"})
    color.append(srgb)
    ppr.append(color)
    ppr.append(ppr.makeelement(qn("a:buFont"), {"typeface": "Arial"}))
    ppr.append(ppr.makeelement(qn("a:buChar"), {"char": "\u2022"}))


def _drop_slide(prs, slide) -> None:
    ids = prs.slides._sldIdLst
    for sld_id in list(ids):
        if prs.slides.part.related_part(sld_id.rId) is slide.part:
            prs.part.drop_rel(sld_id.rId)
            ids.remove(sld_id)
            return


def _reorder(prs, slides) -> None:
    ids = prs.slides._sldIdLst
    by_part = {prs.slides.part.related_part(sld_id.rId): sld_id for sld_id in ids}
    ordered = [by_part[slide.part] for slide in slides]
    for sld_id in list(ids):
        ids.remove(sld_id)
    for sld_id in ordered:
        ids.append(sld_id)


if __name__ == "__main__":
    main()
