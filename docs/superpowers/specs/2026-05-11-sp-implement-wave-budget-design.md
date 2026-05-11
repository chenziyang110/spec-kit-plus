# sp-implement Wave Budget Design

Date: 2026-05-11
Status: Approved for implementation planning

## Summary

This design tightens how `sp-implement` executes parallel-ready work so the
workflow does not make either of these mistakes:

- treat a whole ready parallel batch such as `T012-T021` as one executable
  subagent lane
- fan out every `[P]` task at once just because the tasks are eligible for
  parallel execution

The approved model separates three concepts:

- `parallel-eligible task`: a task marked `[P]` that is allowed to run in
  parallel when its dependencies, write-set isolation, and validation contract
  make that safe
- `parallel batch`: the current ready set of isolated lanes that may run
  concurrently before a downstream join point
- `dispatch wave`: the subset of the current ready batch that the runtime
  actually dispatches in the current turn

`sp-tasks` remains the owner of batch and join-point structure. `sp-implement`
becomes the owner of runtime wave shaping with a fixed budget of four
subagents. Shared integration guidance must preserve the same rule across
generated skills.

## Problem Statement

The current workflow surface already distinguishes `[P]` tasks, parallel
batches, join points, and `parallel-subagents` as a dispatch shape. That is
not enough to prevent two opposite failure modes:

1. the executor reads a range such as `T012-T021` and gives the whole parallel
   batch to one subagent, which collapses concurrency back into serial work
2. the executor sees many `[P]` tasks and interprets "parallel-safe" as "open a
   subagent for every item now", which creates excessive coordination,
   expensive join points, and poor recovery behavior

The core gap is that the current implementation contract explains when
parallelism is allowed, but it does not define a runtime fan-out budget or make
it explicit that one subagent may own one lane but must not own the whole ready
parallel batch.

## Goals

- Preserve `[P]` as a parallel eligibility signal instead of a mandatory
  unlimited fan-out signal.
- Make `parallel batch` a structural planning concept and `dispatch wave` a
  runtime execution concept.
- Add a fixed `sp-implement` fan-out budget of four concurrent subagents.
- Prevent a single subagent from owning an entire ready parallel batch.
- Keep `sp-tasks` integration-neutral and avoid hardcoding runtime wave slices
  into `tasks.md`.
- Preserve resumability and join-point discipline across wave execution.

## Non-Goals

- Do not change the base meaning of `[P]`.
- Do not make `sp-tasks` precompute `wave 1`, `wave 2`, and later runtime wave
  slices.
- Do not introduce a dynamic fan-out budget in this release.
- Do not make `sp-teams` or another durable runtime the default execution path
  for ordinary `sp-implement` runs.
- Do not require every integration to expose named persistent worker processes;
  fixed slot names are execution bookkeeping, not long-lived agent identity.

## Approved Direction

### 1. Three-level concurrency model

The workflow contract should explicitly separate:

- `parallel-eligible task`: a lane-level task that may run concurrently when it
  is ready and isolated
- `parallel batch`: the current ready set of isolated lanes bounded by a join
  point
- `dispatch wave`: the subset of the current batch launched now under the
  runtime fan-out budget

This change makes `[P]` mean "eligible for parallel execution" rather than
"execute every eligible task at the same time."

### 2. `sp-tasks` owns batch structure, not runtime wave slicing

`sp-tasks` should continue to produce the shared execution contract for every
integration. Its responsibility is to emit:

- batch structure
- lane structure
- join points
- write-set isolation and validation expectations

It should not decide how many subagents a specific runtime launches in one
turn.

`sp-tasks` must also tighten one key rule:

- a range expression such as `T012-T021` may appear only as a batch label or
  batch summary, never as one executable lane identity

Each `[P]` task remains a lane-level execution unit unless an explicit wrapper
task defines a serial coordination step.

### 3. `sp-implement` owns wave shaping with a fixed budget of four

`sp-implement` should adopt a fixed runtime budget:

```text
max_parallel_subagents = 4
```

Execution rules:

- if the current ready batch has exactly one dispatch-ready lane, dispatch
  `one-subagent`
- if the current ready batch has two or more dispatch-ready isolated lanes,
  dispatch `parallel-subagents`
- when `parallel-subagents` is selected, dispatch only the current wave, where
  one wave contains at most four lanes
- when the batch contains more than four lanes, execute multiple waves with a
  join-point-style integration pass between waves

This keeps runtime concurrency bounded while still preserving the intent of
parallel-ready batches.

### 4. Fixed execution slot names

For deterministic tracking and resume behavior, `sp-implement` should use four
fixed execution slot names:

- `implement-slot-1`
- `implement-slot-2`
- `implement-slot-3`
- `implement-slot-4`

These are worker slot names, not task IDs. A later wave may reuse the same
slots after the leader has consumed the prior wave's structured handoffs.

### 5. Hard prohibition on whole-batch single-lane dispatch

The implementation contract should explicitly forbid these behaviors:

- dispatching one subagent with a batch-wide objective such as
  "Implement T012-T021 migrations"
- treating a batch range label as if it were one `WorkerTaskPacket`
- launching the first subagent of a parallel wave and immediately waiting
  before dispatching the remaining selected lanes for that wave

The legal unit of delegated implementation remains one validated lane packet,
not one batch label.

## Execution Model

### Dispatch-ready lane criteria

A lane is dispatch-ready only when:

- its dependencies are satisfied in the current phase
- its `WorkerTaskPacket` is complete
- its `write_scope` does not overlap with the other lanes selected for the same
  wave
- its validation checks and done condition are explicit

The existing packet validation contract remains in force. This design adds a
wave budget on top of it; it does not weaken packet readiness requirements.

### Stable selection order

To keep resume behavior deterministic, the current wave should be selected in a
stable order:

1. current phase order from `tasks.md`
2. within the same ready batch, tasks that unlock more downstream work first
3. remaining ties by task ID order

This avoids drift where resume runs choose a different subset of lanes each
time.

### Wave lifecycle

For a ready parallel batch with more than one isolated lane:

1. the leader identifies the current ready batch
2. the leader compiles validated lane packets
3. the leader selects up to four lanes for the current wave
4. the leader dispatches every selected lane before waiting
5. the leader waits only at the wave join point
6. the leader consumes all structured handoffs and validates them
7. if the batch still has queued lanes, the leader forms the next wave
8. after the final wave, the leader decides whether the batch-level join point
   may be crossed

Wave completion does not automatically mean batch completion. The batch-level
join point is crossed only after the full ready batch has been accepted or
explicitly blocked/deferred according to the workflow contract.

### Join-point discipline

The design keeps the existing join-point model and adds wave-level discipline:

- a wave must not be considered complete until every selected lane has either
  returned a valid structured handoff or has been explicitly classified as
  blocked, stale, or deferred
- a batch join point must not be crossed while the batch still has unresolved
  failed lanes or unconsumed results
- a later wave must not start until the leader has integrated the current wave
  results and updated execution state

## State and Recovery Changes

`implement-tracker.md` should make wave state explicit enough to support resume.
Without changing the existing tracker structure wholesale, the design should
make the following current-batch details obvious:

- current batch identifier
- current wave identifier
- active slots
- queued lanes still waiting for a future wave
- completed lanes already integrated

Resume behavior should prefer recovering the partially-completed current wave
instead of recomputing a new batch shape from chat narration.

### Stale-lane handling

If a subagent becomes idle or reports completion before the promised handoff is
written, the leader must treat that lane as stale rather than silently
successful. The recovery flow is:

1. probe once for the missing handoff
2. if the handoff still does not exist, re-dispatch, block, or defer explicitly
3. do not cross the join point on narration alone

### Partial wave failure

If one lane in the wave fails while others succeed:

- successful lane results may be integrated
- the batch join point remains closed
- the failed lane must be repaired, re-dispatched, or explicitly deferred
  before downstream work continues

This preserves useful completed work without treating the full batch as green.

## Surface Changes

### `templates/commands/tasks.md`

Tighten `sp-tasks` guidance so that:

- `[P]` means lane-level parallel eligibility
- `parallel batch` is the current ready set bounded by a join point
- batch range labels such as `T012-T021` are summaries, not executable lane
  identities
- `tasks.md` should enumerate or clearly identify the lane members of a batch
  instead of relying on a range label alone

`sp-tasks` should not encode four-slot wave slicing. That remains a runtime
policy owned by `sp-implement`.

### `templates/commands/implement.md`

Add a hard runtime contract that:

- defines `max_parallel_subagents = 4`
- defines fixed slot names `implement-slot-1..4`
- states that `parallel-subagents` selects a current wave, not unlimited fan-out
- requires dispatching all lanes in the current wave before `wait`
- forbids giving one subagent the objective of implementing the whole ready
  parallel batch
- makes wave-to-wave progression and wave-level integration explicit

### `src/specify_cli/integrations/base.py`

Shared integration augmentation should inject the same rule for integrations
with native subagent support:

- launch all selected lanes in the current `parallel-subagents` wave before
  waiting
- wait only at the current wave join point
- do not assign the whole ready parallel batch to one implementer subagent

This keeps Codex, Claude, and other native-subagent-capable integrations aligned
instead of solving the issue only in one adapter.

### Codex-specific generated guidance

Codex-generated `sp-implement` skills should preserve the same shared rule while
mapping it to `spawn_agent`, `wait_agent`, and `close_agent`:

- `spawn_agent` is used once per selected lane in the current wave
- `wait_agent` is used only after the wave has been fully dispatched
- `close_agent` happens only after the leader has integrated the handoff

The generated wording should explicitly discourage "one subagent owns the whole
batch" behavior because Codex tends to follow the visible contract literally.

## Acceptance Criteria

The design is implemented correctly when all of the following are true:

1. `sp-tasks` guidance explicitly distinguishes parallel-eligible tasks,
   parallel batches, and non-executable batch-range summaries.
2. `sp-implement` guidance defines a fixed budget of four parallel subagents.
3. `sp-implement` guidance defines `implement-slot-1..4` as runtime slot names.
4. `sp-implement` guidance explicitly states that all lanes in the current wave
   must be dispatched before any `wait`.
5. `sp-implement` guidance explicitly forbids a whole ready parallel batch from
   being delegated as one implementation lane.
6. Shared integration augmentation carries the same wave rule into generated
   skills for native-subagent-capable integrations.
7. Regression tests fail if generated skills regress back to either unlimited
   fan-out or whole-batch single-lane delegation.

## Tests and Regression Coverage

### Template-level assertions

Add or update assertions so that:

- `tasks` guidance contains the range-is-not-lane rule
- `implement` guidance contains the four-slot wave budget
- `implement` guidance contains the "dispatch full wave before wait" rule
- `implement` guidance contains the whole-batch single-lane prohibition

### Integration-generation assertions

Generated `sp-implement` skills for Codex and other relevant integrations
should be checked for:

- `spawn_agent`
- `wait_agent`
- `close_agent`
- wave fan-out wording
- the four-slot budget
- the whole-batch prohibition

### Behavior-contract tests

Add or update behavior-oriented tests that model:

- one ready lane -> `one-subagent`
- two to four ready lanes -> one `parallel-subagents` wave
- five or more ready lanes -> multiple waves, each capped at four
- rejection of a whole-batch owner prompt such as
  "Implement T012-T021 migrations"

## Risks

- Over-specifying runtime slot behavior could make the implementation guidance
  feel too prescriptive for integrations that abstract subagent identity.
- A fixed budget of four may be conservative for some future environments.
- Tightening batch/lane wording could force some existing `tasks.md` examples to
  be rewritten.

## Mitigations

- Treat slot names as runtime bookkeeping, not as a requirement for persistent
  worker identities.
- Keep the budget fixed for this release and revisit only after real usage data
  shows a need for dynamic tuning.
- Limit the `sp-tasks` change to structural clarity and do not push runtime wave
  planning into shared planning artifacts.
