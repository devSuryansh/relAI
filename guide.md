# Team Guide: Agent Reliability Lab

For Suryansh, Simran, and Tanishka. Read this before the Design/Implementation
Phase progress review, and keep it for the reviews after it.

## Review day at a glance

| | |
| --- | --- |
| When | Saturday 17 October 2026, 11:30 AM to 1:30 PM. Be there by 11:20 AM. |
| Where | Panel-3 (groups G040 to G060), Room 203, Block-D |
| Group | CSE/CSPROJECT/2027/G053. Double-check this number: the notice's own reference number is also 053. |
| Supervisor | Mr. Pradeep Kumar |
| Slides | [academic/progress-review/Progress_Review_PPT.pptx](academic/progress-review/Progress_Review_PPT.pptx), 20 slides, presenter named in each slide's notes |
| Hard copies | Research paper (mandatory), progress report, Annexure-2 form, Annexure-3 report card |

Bring:

- [ ] Printed research paper: [academic/paper/relai_paper.pdf](academic/paper/relai_paper.pdf). The notice makes this mandatory.
- [ ] Printed progress report: [academic/progress-review/progress_report.pdf](academic/progress-review/progress_report.pdf). Appendix A has every Annexure-2 field ready to copy onto the form.
- [ ] Annexure-2 (Project Progress Evaluation Report) form, header filled in, ready for signatures.
- [ ] Annexure-3 (Project Progress Report Card) for each member. Appendix B of the report lists the work done with dates.
- [ ] Laptop, charged, with the demo already set up (see the demo section), plus the charger and an HDMI adapter.
- [ ] The PPT and its PDF on a USB stick, in case the room PC has to be used.
- [ ] If the Project Approval Form and synopsis hard copy were not yet submitted, ask the coordinator today. The notice deadline was 14 October.

## 1. The project in plain words

### 30-second pitch

> AI agents now do real work: they plan, call tools, and retry when something
> breaks. But benchmarks only tell you whether an agent finished. They don't
> tell you why it failed, whether it succeeds every time, or what that
> reliability costs. Agent Reliability Lab is a crash-test lab for AI agents.
> We break tools on purpose in a repeatable way, run every agent several
> times, explain each failure with evidence, and pick the cheapest setup that
> stays reliable.

### 2-minute version

1. **Problem.** Two agents can both score 60% and fail for completely different
   reasons. One guesses instead of looking things up. The other gives up after
   one timeout. One success number can't tell them apart. It also hides
   inconsistency: an agent with 77% success solves only 33% of our tasks in all
   five attempts.
2. **What we built.** A Python package and command-line tool called `relai`.
   - You give it tasks and any agent that has a name and a `run(task)` method.
   - It runs the agent several times per task while tools time out on a seeded
     schedule.
   - It records every step the agent takes (its trajectory) and measures
     success, cost, latency, recovery, and steps.
   - It labels each failure as planning, tool misuse, context, recovery, or
     horizon, and shows the evidence. Failures it can't explain stay
     "unclassified".
3. **What makes it fair.** A fault depends only on the seed, task, trial, tool,
   and call number, never on the agent. So every agent meets exactly the same
   failures. That makes the runs matched pairs, and we can use a proper paired
   significance test (McNemar).
4. **What we found so far.** These are offline reference agents, not real
   LLMs yet. With 30% of tool calls timing out:
   - An agent that never retries gets 0.58 success.
   - Three retries get 1.00, at about twice the cost and latency.
   - Our classifier finds every planted defect with precision 1.00.
   - The measured effect of faults matches the math, so we know the fault
     injector itself is correct.
5. **Next.** Run real models (hosted ones, and local ones through Ollama)
   through the adapter we already built, and add those results to the paper.

### What this project is not

- Not a chatbot, and not a new model. We do not train anything.
- Not a production monitoring dashboard like LangSmith. It is a laboratory for
  controlled experiments.
- Not a claim about which LLM is best. The current numbers test the
  instrument, not the models.

## 2. What the review asked for and where it is

| The notice asks for | Where it is |
| --- | --- |
| Proposed system | Slides 3 to 4; report chapter 1 |
| Functional and non-functional requirements | Slide 5; report sections 2.1 and 2.2 |
| Major modules and their functionalities | Slide 6; report section 2.3 |
| Class design | Slide 7; [academic/diagrams/class.png](academic/diagrams/class.png) |
| Sequence diagrams | Slide 8; [academic/diagrams/sequence.png](academic/diagrams/sequence.png) |
| Database design (DFD and ER) | Slides 9 to 10; `dfd0`, `dfd1`, `er` in [academic/diagrams/](academic/diagrams/) |
| Gantt or PERT chart | Slide 11; [academic/diagrams/gantt.png](academic/diagrams/gantt.png) |
| Implementation of modules and algorithms | Slide 12; report section 4.1 |
| Code snapshots | Slides 13 to 15; [academic/snapshots/](academic/snapshots/) |
| 15 to 20 slides | 20 slides |
| Research paper: abstract, introduction, problem statement, proposed methodology | [academic/paper/relai_paper.pdf](academic/paper/relai_paper.pdf). It has all four, plus related work and preliminary results. |

## 3. Who did what

The work is split by ownership. Owning a part means you designed it, you can
explain every line of it, you present it, and you answer the panel's
questions about it. The split follows the roles on our first-draft
presentation, so it matches what the panel already saw at the synopsis
review.

Be honest about two things. First, the git history shows commits from the
lead's machine, because the repository was put together there. From now on,
each member should commit their own work from their own account. Second,
before the review, each member must run the commands for their part and read
their files, so that ownership is real. If the panel asks who wrote
something, say exactly what you did.

### Suryansh Singh (team lead): architecture and execution

| Owns | Files |
| --- | --- |
| Overall architecture and design rules | `AGENTS.md`, `documentation/architecture.md` |
| Domain types and the agent interface | `src/relai/types.py`, `src/relai/agents.py` |
| Tool environment and fault injection | `src/relai/env.py` |
| Harness, repeated trials, crash capture, pass@k and pass^k | `src/relai/harness.py` |
| Controlled experiments and stress tests | `src/relai/experiment.py` |
| SQLite and JSON Lines store | `src/relai/store.py` |
| Command-line interface | `src/relai/cli.py` |
| Live LLM adapter | `src/relai/adapters/openai_compat.py` |
| Integration, release, research paper drafting | `CHANGELOG.md`, `academic/paper/` |

Must be able to explain:
- Why the agent interface is only `name` + `run(task)`.
- How a fault is decided (see the snapshot `code_fault_policy.png`) and why
  that makes comparisons fair.
- How trials and the seed reach the agent through `task.metadata`.
- What happens when an agent crashes.
- How the store's tables relate (the ER diagram).

Presents slides 1 to 4, 7, 8, 13, 17, and 19.

### Simran Kumari: measurement and analysis

| Owns | Files |
| --- | --- |
| Scorers and metric derivation | `src/relai/metrics.py` |
| Failure taxonomy and classifier | `src/relai/analysis.py`, `documentation/failure-taxonomy.md` |
| Confidence intervals and the paired test | `src/relai/stats.py` |
| Configuration sweep, Pareto front, recommendation | `src/relai/optimize.py` |
| Results analysis and related-work survey | `academic/results/`, paper sections II and V |

Must be able to explain:
- pass@k versus pass^k, using numbers. For example, 2 passes out of 4 trials
  gives pass^2 = 1/6.
- The five failure modes, with one example each.
- Why the root cause is the earliest evidence.
- Why "unclassified" exists.
- How McNemar works, and why it is valid here.
- Why the Wilson interval is used with one trial, and the task bootstrap with
  several trials.
- What the Pareto front is.

Presents slides 12, 14, 16, and 18.

### Tanishka Sahu: suites, agents, reports, and quality

| Owns | Files |
| --- | --- |
| Task suite format and the built-in suites | `src/relai/suite.py`, `src/relai/suites/*.yaml` |
| Baseline agents with planted defects | `src/relai/baselines.py` |
| Classifier self-check | `src/relai/selfcheck.py` |
| HTML and Markdown reports | `src/relai/report.py` |
| Tests, examples, CI | `tests/`, `examples/`, `.github/workflows/ci.yml` |
| Diagrams, slides, and progress report | `academic/diagrams/`, `academic/progress-review/` |

Must be able to explain:
- How to write a task in YAML, including `solution`, `guess`, and `max_steps`.
- What each baseline agent does wrong on purpose.
- How the self-check proves the classifier works.
- What the 81 tests check.
- How to run the demo.
- The SRS, the DFDs, and the Gantt chart.

Presents slides 5, 6, 9, 10, 11, and 15 (the demo).

### Shared

Everyone reviewed the requirements, the slides, and the paper. Everyone
should be able to give the 30-second pitch and the key numbers in section 9.

## 4. How to present

### Timing (about 12 minutes, then questions)

| Slides | Speaker | Minutes | Say this, in short |
| --- | --- | --- | --- |
| 1 to 2 | Suryansh | 0.5 | Group, title, team, agenda |
| 3 | Suryansh | 1.0 | One-line problem, the crash-test idea, three objectives all implemented |
| 4 | Suryansh | 1.0 | Four layers; only the execution layer calls agents |
| 5 to 6 | Tanishka | 1.5 | Two or three requirements, fairness and reproducibility, the module owners |
| 7 to 8 | Suryansh | 1.5 | Main classes; follow one run through the sequence diagram |
| 9 to 11 | Tanishka | 1.5 | Level 0 and level 1 data flow, the run store tables, where we are on the Gantt chart |
| 12 | Simran | 1.0 | Five algorithms; the classification flowchart |
| 13 to 14 | Suryansh, Simran | 1.5 | Real code: fault decision, retry, the harness loop, the estimators |
| 15 | Tanishka | 1.5 | Live demo, or the output screenshot |
| 16 | Simran | 1.0 | Stress curve, self-check precision 1.00, the injector matches theory |
| 17 | Suryansh | 0.5 | Paper status (hand over the hard copy), what comes next |
| 18 to 20 | Simran, Suryansh | 0.5 | References, thanks, invite questions |

Tips:
- Talk in numbers. "0.58 versus 1.00 with a p-value of 0.0001" lands harder
  than "much better".
- Say "reference agents" every time you show results, so nobody thinks they
  are LLM results.
- When you show a diagram, point at one path through it instead of reading
  every box.
- If you don't know an answer, say so, and say how you would find out. Never
  guess at numbers.

### Live demo

Set this up the night before, and test it again in the morning:

```bash
cd relAI
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q                          # 81 passed
```

During the review (about 2 minutes), run three commands:

```bash
relai run reliability --agent naive --agent retry:1 --agent retry:3 --trials 5 --timeout-rate 0.3
relai selfcheck --trials 5
relai sweep reliability --param max_retries=0,1,2,3,4 --timeout-rate 0.3 --trials 5 --min-success 0.95
```

If the panel wants to see more:

```bash
relai stress reliability --agent naive --agent retry:1 --agent retry:3 --trials 5
relai run reliability --trials 5 --timeout-rate 0.3 --html report.html   # then open report.html
relai run reliability --agent examples.custom_agent:make_agent --timeout-rate 0.3
```

If anything fails, do not debug in front of the panel. Show these instead:
the screenshots in [academic/snapshots/](academic/snapshots/) (`term_run.png`,
`term_selfcheck.png`, `term_sweep.png`, `term_tests.png`) and the sample report
[academic/results/sample_report.html](academic/results/sample_report.html).
They are produced by the same commands.

## 5. Questions the panel may ask, with answers

Answers are short on purpose. The person in brackets answers first.

### Concept and motivation

**Q1. What problem does your project solve?** (Suryansh)
Agent benchmarks report one success rate. That hides why agents fail, how
consistent they are, and what reliability costs. We built a lab that measures
all three under controlled tool failures.

**Q2. Why not just use success rate or an existing benchmark?** (Suryansh)
Benchmarks give you tasks and a score. We give you the experiment around
them: the same faults for every agent, repeated trials, a diagnosis of each
failed run, significance tests, and a cost-aware choice of settings. Any
suite, including tasks taken from existing benchmarks, can run inside it.

**Q3. What is a trajectory?** (Suryansh)
The ordered list of steps in one run: plan, tool call, observation, error,
recovery, final answer. Each step can carry latency, tokens, and cost.
Everything we measure is computed from trajectories.

**Q4. Do you train a model?** (Suryansh)
No. This is an evaluation and reliability tool. It works with any agent that
has a name and a `run(task)` method: scripted policies, hand-written agents,
or real LLMs through the adapter.

**Q5. Who would use it?** (Simran)
Developers choosing a model, prompt, or retry policy before deployment.
Researchers comparing agent designs fairly. Students learning about agent
reliability without paying for an API.

### Design

**Q6. Why is the agent interface so small?** (Suryansh)
So that anything can plug in without the harness changing: LangChain agents,
custom code, local models. New backends adapt to the interface instead of
the other way round.

**Q7. Why do metrics and analysis never call the agent?** (Suryansh)
Reproducibility. Every number is a function of the stored trajectory, so you
can recompute it from the database later, and you can test it without any
model.

**Q8. Walk us through the class diagram.** (Suryansh)
- `Task` goes into an `Agent`, which produces a `Trajectory` of `Step`s.
- A `RunResult` combines that trajectory with its `Score`, `RunMetrics`, and
  `FailureReport`.
- `EvalReport` holds all the runs of one variant, and `ExperimentReport`
  holds all the variants.
- `ToolEnv` and `FaultPolicy` decide the faults. `Recorder` turns tool calls
  into steps.

**Q9. Why SQLite? And why keep both `result_json` and the `steps` and `failures` tables?** (Suryansh)
SQLite needs no server and ships with Python. `result_json` makes reloading
exact (lossless). The normalized tables let you ask questions in SQL, for
example "failure counts per variant", without parsing JSON.

**Q10. Why YAML for task suites?** (Tanishka)
Non-programmers can write tasks. Each file is self-contained (tasks, mock
tools, faults, and reference plans), and it is validated on load, so a typo
in a tool name fails early with a clear message.

**Q11. Explain your level 1 DFD.** (Tanishka)
1. Load the suite and build the environment.
2. Execute trials, with the agent outside the system boundary.
3. Score and measure.
4. Classify failures.
5. Compare and optimize.
6. Store and report.

Data stores: suite files, run results, the SQLite store, and reports.

### Fault injection

**Q12. How do you inject faults?** (Suryansh)
Every tool call goes through `ToolEnv`. For the n-th call to a tool, we seed
a random generator with (seed, task, trial, tool, n). If the draw is below
the timeout rate, the call times out. The next band is an outage. Otherwise
the tool runs. The first N calls can also be forced to fail.

**Q13. Why does the fault depend on the call number and not on the agent?** (Suryansh)
So that two agents making the same calls meet the same faults. Statistics
calls this common random numbers. It turns two separate samples into matched
pairs, which removes noise and makes a paired test valid.

**Q14. How do you know the fault injector is correct?** (Simran)
We checked it against the math. A no-retry agent on a task with L tool calls
should succeed with probability (1 - p)^L. At p = 0.3 we measured 0.69, 0.52,
0.33, and 0.16 for 1, 2, 3, and 5 calls. The expected values are 0.70, 0.49,
0.34, and 0.17. Unit tests also check that the schedule is reproducible and
identical across agents.

**Q15. Are timeouts realistic? What else could fail?** (Suryansh)
Timeouts and outages are the most common transient failures of real APIs.
Next we will add rate limits, slow responses, truncated or corrupted outputs,
and changed tool schemas. They plug into the same `FaultPolicy`.

### Metrics and statistics

**Q16. What is the difference between pass@k and pass^k?** (Simran)
- pass@k: the chance that at least one of k attempts succeeds. That
  measures capability.
- pass^k: the chance that all k attempts succeed. That measures
  dependability.
- With c passes in n trials: pass@k = 1 - C(n-c,k)/C(n,k), and
  pass^k = C(c,k)/C(n,k).
- Example: one retry gives 0.77 success but only 0.33 pass^5.

**Q17. What is consistency?** (Simran)
The share of tasks whose trials all agree: all pass or all fail.

**Q18. Why confidence intervals? Why Wilson and bootstrap?** (Simran)
With 12 tasks, a success rate is uncertain, and the interval shows how
uncertain. Wilson behaves well near 0 and 1, where the simple formula breaks.
With repeated trials, runs of the same task are correlated. So the bootstrap
resamples whole tasks, not single runs. Otherwise the interval would be too
narrow.

**Q19. What is McNemar's test, and why use it?** (Simran)
It compares two variants on the same items using only the pairs where they
disagree. Three retries passed 14 runs that one retry failed, and lost none.
The exact p-value is 0.0001, so the difference is real. It is valid because
our fault schedule makes the runs genuine pairs.

**Q20. How is the recovery rate computed?** (Simran)
Each error step is an episode. An episode counts as recovered if a later call
of the same tool works, or the run ends with a correct answer. Failed retries
in between don't break the episode. Recovery rate = recovered episodes /
error steps.

**Q21. What is the difference between latency and wall latency?** (Simran)
Latency is the sum of recorded step latencies: tool time, timeout time,
backoff, and model time. Wall latency is the clock time around `run`. For
simulated agents the step latency is the meaningful number. For live models
the two are close.

### Failure taxonomy

**Q22. What are your five failure modes?** (Simran)

| Mode | What happened | Example |
| --- | --- | --- |
| Planning | Answered wrongly without using a needed tool | Says "processing" without checking the order |
| Tool misuse | Called a forbidden tool, or a call failed through the agent's own fault | Runs `shell`; passes a wrong argument name |
| Context | Repeated the same call right after getting its answer | Searches the same query again after seeing the result |
| Recovery | Did not get back on track after an error | Weather API times out, agent answers "unknown" |
| Horizon | Never answered, or took more steps than allowed | Retries push a 12-step task to 14 steps |

**Q23. Several modes fire at once. Which is the root cause?** (Simran)
The mode whose first evidence appears earliest in the trajectory. The first
breakdown usually explains the later symptoms. For example, a looping agent
that also runs out of steps is blamed on context, not horizon.

**Q24. Why keep "unclassified"?** (Simran)
Forcing every failure into a label creates false explanations. Unclassified
runs are counted separately so they can be studied, and a new rule is added
only when a test proves when it fires and when it stays silent.

**Q25. How do you know the classifier is right?** (Tanishka)
Two ways. First, 13 unit tests pin each rule, including cases where it must
stay silent. Second, the self-check runs agents with one planted defect each.
Every diagnosed run was blamed on the planted defect, so precision is 1.00 for
all four modes. The retry agent is the control.

**Q26. Can it tell when the agent's reasoning is wrong?** (Simran)
Not from free text. The rules read structure: which tools were called, in
what order, and what happened. Judging reasoning text needs an LLM judge or
human review, which is future work as an optional scorer.

**Q27. The 3-retry agent succeeded. Why does it show 12 horizon failures?** (Simran)
On long tasks its retries pushed the run past the step budget. The answer was
right, but the agent used more steps than the task allows. Flagging that is
deliberate: it is the hidden cost of retrying.

### Optimization

**Q28. What is the Pareto front, and why is every retry setting on it?** (Simran)
A setting is on the front if no other setting is at least as good on
success, cost, and latency while being better on one. Each extra retry buys
success with cost and latency, so none dominates another. That is a real
trade-off, not a bug.

**Q29. Why does the tool recommend 2 retries?** (Simran)
It is the cheapest setting that reaches our target of at least 0.95 success:
0.98 success and 0.92 pass^5. Three retries reach 1.00, but they are not
cheaper.

### Results and validity

**Q30. Are these results from real LLMs?** (Suryansh)
No, and we say so on every results slide and in the paper. They come from
reference agents whose behaviour we control. That lets us check that the lab
measures correctly. Running real LLMs is the next phase, and the adapter for
it is already built and tested.

**Q31. Twelve tasks is small. Is that enough?** (Simran)
For checking the instrument, yes. With trials there are 60 runs per agent,
and we report confidence intervals and exact p-values instead of hiding the
sample size. For the LLM study, we will add suites adapted from public
benchmarks.

**Q32. Can it run a real model today?** (Suryansh)
Yes. `OpenAICompatAgent` works with OpenAI, Groq, vLLM, or a local Ollama
server through `OPENAI_BASE_URL`. See `examples/live_llm_agent.py`. It
records tokens, cost, and latency per step. The paper doesn't report live
runs yet.

### Comparison and novelty

**Q33. How is this different from LangSmith or Langfuse?** (Suryansh)
They are tracing and observability platforms. They log production runs and
let you score them, and they are excellent at that. We run controlled
experiments: injected faults that are identical for every variant, repeated
trials, rule-based diagnosis, paired tests, and configuration search. We
complement them. Trace import is on our roadmap.

**Q34. How is it different from tau-bench or the Holistic Agent Leaderboard (HAL)?** (Simran)
- tau-bench introduced pass^k and gives realistic customer-service tasks. We
  adopted pass^k.
- HAL runs many benchmarks at scale with cost tracking. The Princeton team
  behind HAL also published a 12-metric reliability framework (ICML 2026).
- Both are mainly benchmarks and leaderboards. Ours is a small library you
  point at your own agent to run your own controlled experiment, offline,
  with a per-run diagnosis.

**Q35. Fault injection already exists (ToolMisuseBench, ToolBench-X, AgentChaos). What is new?** (Suryansh)
Fault injection itself is not new, and we cite these works. What we add is
the combination:
1. The fault schedule is a controlled factor, identical across variants, which
   enables paired tests.
2. The injector is validated against its closed-form expectation.
3. The failure classifier is validated with planted defects.
4. A cost-aware search returns the cheapest reliable setting.
5. All of it in one small, offline, open-source library.

**Q36. What is your research contribution in one line?** (Suryansh)
A reproducible method for reliability experiments on agents: agent-independent
fault schedules for paired comparison, plus evidence-based diagnosis that is
validated against planted defects.

### Implementation

**Q37. What is the tech stack, and why?** (Tanishka)
Python 3.11+, with Pydantic for typed, validated, serializable models and
PyYAML for suites. Tests use pytest and lint uses Ruff. Storage is SQLite
from the standard library. Few dependencies means it installs anywhere,
including lab PCs.

**Q38. How did you test it?** (Tanishka)
81 automated tests, one file per module. They run in under a second, and CI
runs them on Python 3.11, 3.12, and 3.13. The adapter is tested with a fake
model, so the tests never need the network.

**Q39. How fast is it?** (Tanishka)
About 6,500 fully scored and classified simulated runs per second on a
laptop. Live runs are limited by the model API, not by the lab.

**Q40. What about security?** (Suryansh)
- The calculator tool never uses `eval`. It parses arithmetic with a
  whitelist and caps exponents.
- HTML reports escape all agent output.
- API keys come from environment variables.
- Everything runs offline by default.

**Q41. What if an agent crashes?** (Suryansh)
The harness catches the exception and records a failed run with an error
step. The experiment continues. A crash is data, not a stopped experiment.

### Process, teamwork, and ethics

**Q42. How did you divide the work?** (Suryansh)
By ownership: execution and architecture (Suryansh), measurement and analysis
(Simran), suites, agents, reports, and quality (Tanishka). Each person
presents and answers for their part. Section 3 of this guide has the file
list.

**Q43. What was the hardest problem?** (Simran)
Defining recovery correctly. Our first rule judged each error only up to the
next error. So a chain like "timeout, retry, timeout, retry, success" was
wrongly flagged as a recovery failure. The self-check exposed it: the control
agent showed 13 false recovery failures. We fixed the rule and pinned it with
tests. After the fix, precision went to 1.00.

**Q44. Did you use AI tools?** (Everyone, honestly)
Answer truthfully and specifically: say which tools you used and for what.
Then say what you checked yourselves: we ran every command, every number comes
from scripts in the repository, and each owner can explain their code. Follow
the institute's policy on disclosure.

**Q45. Which SDG does this map to?** (Tanishka)
SDG 9, Industry, Innovation and Infrastructure: dependable AI infrastructure.
It also supports responsible AI use, because unreliable agents are tested
before they reach users.

### Future

**Q46. What comes next?** (Suryansh)
Real LLM experiments, suites adapted from public benchmarks, more fault kinds,
and the paper results. In semester VIII: a dashboard, importing traces from
tracing platforms, and a 1.0 release.

**Q47. Could this become a product or a patent?** (Suryansh)
It could become a reliability gate in CI ("fail the build if pass^5 drops
below 0.9"). For the patent route, the candidate is the agent-independent
fault schedule combined with paired testing and planted-defect validation.
We would need a prior-art search first, because fault injection itself is
known.

## 6. What is done, what is left, what could come later

### Done (as of 17 October 2026)

- `relai` v0.2: 17 modules, about 3,300 lines, 81 tests, CI on three Python
  versions.
- Seeded fault injection, repeated trials, pass@k, pass^k, consistency.
- Five failure modes with evidence, unclassified outcome, planted-defect
  self-check.
- Wilson and bootstrap intervals, exact McNemar test.
- Grid sweep, Pareto front, recommendation.
- YAML suites, five baseline agents, OpenAI-compatible LLM adapter.
- SQLite and JSONL store, HTML and Markdown reports, seven CLI commands.
- Documentation: README, architecture, failure taxonomy, changelog.
- Review pack: requirements, class, sequence, DFD 0 and 1, ER, Gantt,
  classifier flowchart, plots, code snapshots, 20-slide deck, progress report,
  research paper.

### In progress

- Research paper: the live LLM results section.
- Annexure-2 and Annexure-3 forms, which need signatures.

### Next (October to December 2026)

1. Live LLM study: a hosted model and a local model through Ollama on the
   reliability suite, with real cost per model.
2. Suites adapted from public benchmarks (retail and airline style tasks,
   coding tasks).
3. More fault kinds: rate limits, slow responses, truncated or corrupted
   outputs, schema drift.
4. Capstone Project 1 final report and review.

### Could come later (semester VIII and beyond)

- A web dashboard over the run store.
- Import traces from tracing platforms (OpenTelemetry, Langfuse) and diagnose
  them.
- An optional LLM-judge scorer for free-text answers.
- Multi-agent systems: map our modes onto the MAST taxonomy.
- Parallel and distributed execution, and adaptive search instead of a grid.
- Predictability (calibrated confidence) and safety metrics from the 2026
  reliability literature.
- Sequential testing that stops trials early once a decision is clear, to
  save API cost.
- Paper submission, then release 1.0 on PyPI.

## 7. Benefits

- **Developers** find out why an agent fails before users do, and get the
  cheapest configuration that meets a reliability target instead of guessing.
- **Researchers** get fair, paired, reproducible comparisons with honest
  uncertainty, so claims like "variant B is better" are tested, not eyeballed.
- **Teams in production** can turn reliability into a CI check, for example
  "pass^5 must stay at least 0.9 under 20% timeouts".
- **Students and teachers** can study agent reliability offline at zero API
  cost.
- **The department** gets a reusable, tested asset that later batches can
  extend with new agents, suites, and failure modes.

## 8. How it compares to existing tools and research

We researched these in October 2026. Each row says what the work is good at,
and where we differ. Where they are stronger, the table says so.

### Tools and platforms

| Tool | Good at | Where we differ |
| --- | --- | --- |
| [LangSmith](https://www.langchain.com/langsmith) | Hosted tracing and evaluation, best fit for LangChain and LangGraph | Closed platform. We are an open, offline experiment library with injected faults and paired tests. They are far stronger for production monitoring. |
| [Langfuse](https://langfuse.com) | Open-source (MIT core) tracing, datasets, LLM judges, self-hosting | They score traffic you already have. We generate controlled runs under identical faults. Complementary: trace import is on our roadmap. |
| [Arize Phoenix](https://phoenix.arize.com) | OpenTelemetry tracing and evaluators, local-first | Source-available (Elastic 2.0). No controlled fault schedule or paired comparison. |
| [Braintrust](https://www.braintrust.dev) | Eval-driven development, datasets, CI release gates | Proprietary. Strong product UX we don't try to match. Our edge is the experiment design, not the platform. |
| [W&B Weave](https://wandb.ai/site/weave) | Tracing and evals inside Weights and Biases | Same contrast as other platforms. HAL uses Weave for logging. |
| [DeepEval](https://github.com/confident-ai/deepeval) | Pytest-style LLM tests, many metrics | Unit tests on outputs. We run experiments over trajectories with faults and trials. |
| [Promptfoo](https://www.promptfoo.dev) | YAML evals and red-teaming in CI | Strong for prompt regression and security. No agent fault schedule or failure taxonomy. |
| [Inspect AI](https://inspect.aisi.org.uk) (UK AI Security Institute) | Research-grade evals, sandboxes, many ready benchmarks | Much broader and more mature. We are narrower and focused on reliability experiments and diagnosis. |
| [OpenAI Evals](https://github.com/openai/evals) | Registry of evals and graders | Task grading. No trajectory-level failure analysis. |

### Research

| Work | Contribution | Relation to ours |
| --- | --- | --- |
| [tau-bench](https://arxiv.org/abs/2406.12045) (Yao et al., 2024) | Tool-agent-user benchmark; introduced pass^k | We adopt pass^k. They provide tasks; we provide the experiment around tasks. |
| [AI Agents That Matter](https://arxiv.org/abs/2407.01502) (Kapoor et al., 2024) | Cost must be measured; accuracy and cost Pareto | We build the cost-aware Pareto search into the tool. |
| [HAL](https://arxiv.org/abs/2510.11977) (Kapoor et al., ICLR 2026) | Standardized, cost-aware harness at scale, LLM-aided log inspection | Far larger scale. We add fault schedules identical across variants and rule-based diagnosis. |
| [Towards a Science of AI Agent Reliability](https://arxiv.org/abs/2602.16666) (Rabanser et al., ICML 2026) | 12 reliability metrics: consistency, robustness, predictability, safety | Closest in spirit. Their predictability and safety metrics are future work for us. We add paired testing and per-run diagnosis. |
| [ToolMisuseBench](https://arxiv.org/abs/2604.01508) (2026) | Deterministic, replayable tool faults with budgets | Similar fault idea, delivered as a benchmark dataset. We make faults a controlled factor and check them against theory. |
| [ToolBench-X](https://arxiv.org/abs/2606.25819) (2026) | Recoverable tool-environment hazards | Richer hazard types than ours today. Their hazard ideas are on our roadmap. |
| [AgentChaos](https://arxiv.org/abs/2608.06790) (2026) | Chaos engineering through an LLM API proxy | Injects at the model API layer. We inject at the tool layer, inside the experiment. |
| [MAST](https://arxiv.org/abs/2503.13657) (Cemri et al., 2025) | 14 failure modes for multi-agent systems, from annotated traces | Larger taxonomy built from human annotation. Ours is small, rule-based, and validated by planted defects. |
| [TRAIL](https://arxiv.org/abs/2505.08638) (2025) and [Who&When](https://arxiv.org/abs/2505.00212) (ICML 2025) | Locating errors in long traces | Shows that automated attribution is hard (best step accuracy 14.2%). Our rules trade coverage for certainty, and say "unclassified" when unsure. |

### Honest positioning

- **Not new:** measuring agents, fault injection, pass^k, cost awareness,
  failure taxonomies. We cite all of these.
- **What we contribute:**
  1. Fault schedules that are identical across variants, which makes runs
     paired, so exact significance tests apply.
  2. A fault injector checked against its closed-form expectation.
  3. A rule-based classifier that explains each run with evidence, refuses to
     guess, and is validated with planted defects.
  4. A cost-aware search for the cheapest reliable setting.
  5. All of it in a small, offline, open-source library that works with any
     agent.
- **Where others are stronger:** scale, ready-made benchmarks, production
  tracing, dashboards, and multi-agent coverage.

## 9. Numbers to remember

| Fact | Value |
| --- | --- |
| Code | 17 modules, about 3,300 lines; 81 tests in under 1 s; CI on Python 3.11 to 3.13 |
| Speed | About 6,500 scored and classified runs per second |
| Suite | 12 support-desk tasks needing 0 to 5 tool calls; 5 trials each = 60 runs per agent |
| At 30% timeouts | naive 0.58 (pass^5 0.25); 1 retry 0.77 (0.33); 3 retries 1.00 (1.00) |
| Cost and latency per run | $0.0016 and 543 ms; $0.0025 and 947 ms; $0.0030 and 1116 ms |
| Paired test | 3 retries vs 1 retry: 14 to 0, p = 0.0001 |
| Self-check | Precision 1.00 for planning, tool misuse, context, recovery |
| Injector check | 3 calls, no retry: 0.33 measured vs 0.34 expected |
| Sweep | 2 retries is the cheapest setting with success at least 0.95 (0.98) |

Every number comes from `python academic/results/make_results.py`.

## 10. Glossary

- **Agent:** a program that works on a task by planning and calling tools. Here, anything with `name` and `run(task)`.
- **Trajectory:** the list of steps one run took.
- **Trial:** one attempt at a task. We run several per task.
- **Fault injection:** making tool calls fail on purpose.
- **Seed:** the number that fixes the random fault schedule, so a run can be repeated exactly.
- **pass@k / pass^k:** the chance that at least one / all of k attempts succeed.
- **Consistency:** the share of tasks whose attempts all agree.
- **Root cause:** the earliest failure mode found in a run.
- **Unclassified:** a failed run that no rule explains.
- **Confidence interval:** a range that likely contains the true success rate.
- **McNemar test:** a test comparing two variants on the same items, using only the items where they disagree.
- **Pareto front:** the settings that cannot be improved on one goal without getting worse on another.
- **Horizon:** how many steps a run took; a horizon failure means no answer, or over budget.
- **Planted defect:** a known mistake built into a test agent, so we can check that the classifier finds it.

## 11. Where everything is

| Path | What |
| --- | --- |
| `src/relai/` | The package |
| `tests/` | 81 tests |
| `examples/` | Runnable scripts, including a live LLM example and a custom agent |
| `documentation/` | Architecture and failure taxonomy |
| `academic/paper/` | Research paper source and PDF |
| `academic/progress-review/` | Slides, slide builder, progress report |
| `academic/diagrams/` | All diagrams, as TikZ source, PDF, and PNG |
| `academic/results/` | Data and captured output behind every number |
| `academic/snapshots/` | Code and terminal images |
| `docs/` | Institute templates and forms. Local only, not tracked in git. |
