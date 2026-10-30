# Failure taxonomy

`relai.analysis.analyze(task, trajectory, score)` runs five detectors on every
run. Several can fire on the same run. The **root cause** is the mode whose
first evidence appears earliest in the trajectory, because the first
breakdown usually explains the later symptoms. A failed run that no detector
matches is **unclassified**; the classifier never forces a label.

Each rule below is pinned by fixtures in `tests/test_analysis.py`, including
fixtures that show when it must stay silent.

## Planning

The agent chose a path that could not work.

Fires on an unsuccessful run that produced a final answer, met no tool
failure and no environment error, and either:

- the task needs tools (`requires_tools` tag or a non-empty `allowed_tools`)
  but no tool was called, or
- the task is tagged `planning` but the run has no plan step, or
- the answer is wrong and no tool was used at all.

Silent when the run succeeded, when it never answered (that is a horizon
failure), or when tools failed (the failure is explained elsewhere).

Example: asked for an order status, the agent answers "processing" from
memory.

## Tool misuse

The agent used tools wrongly.

Fires when the agent calls a tool outside `allowed_tools`, or a tool call
fails without an environment error right after it. That second case covers
unknown tools and bad arguments. It can fire on a successful run, because
calling a forbidden tool is a problem even when the answer is right.

Silent for injected timeouts and outages, which are followed by an `error`
step and belong to recovery.

Example: the agent runs `shell` before following its plan.

## Context

The agent ignored what it just learned.

Fires when the agent repeats a tool call with exactly the same name and
arguments right after receiving an observation from it.

Silent for retries after an error, because a retry follows an error step, not
an observation.

Example: `search(q="a")`, observation "Paris", `search(q="a")` again.

## Recovery

The agent did not get back on track after an error.

Every `error` step opens an episode. The episode is recovered when a later
call of the tool that failed succeeds (any working tool call when the error
did not follow a tool call), or when the run ends with a correct answer.
Failed retries inside the episode do not close it, so a chain of retries that
ends in success counts as recovered.

Fires when any episode is not recovered. The evidence says whether there was
no recovery attempt at all or the attempts did not work.
`recovery_effectiveness` is the share of recovered episodes.

Example: the weather tool times out and the agent answers "unknown".

## Horizon

The run did not finish within its budget.

Fires when the run has more steps than `task.max_steps`, or when it ends
without a final answer (out of turns, gave up, or crashed). An over-budget run
is flagged even when its answer is right: the answer cost more steps than the
task allows.

Example: three retries on a three-call chain take 14 steps against a budget
of 12.

## Unclassified

A failed run with no matching mode, for example a correct tool sequence
followed by a wrong final answer. Unclassified runs are counted separately in
every report so they can be studied before a new rule is written.

## Adding a mode

1. Add the value to `FailureMode` in `types.py`.
2. Write a detector in `analysis.py` that returns the index of the first
   evidence and appends a plain-language evidence string.
3. Add fixtures to `tests/test_analysis.py`: at least one trajectory where it
   fires and one similar trajectory where it must stay silent.
4. If a baseline agent can carry the defect, add it to `baselines.py` so
   `relai selfcheck` covers it.
