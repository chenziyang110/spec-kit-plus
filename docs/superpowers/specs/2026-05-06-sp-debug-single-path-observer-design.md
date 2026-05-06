# sp-debug Single-Path Observer Design

Date: 2026-05-06
Status: Approved for implementation planning
Supersedes as the active product contract:
- `docs/superpowers/specs/2026-05-03-sp-debug-dual-observer-design.md`
- `docs/superpowers/specs/2026-05-05-sp-debug-expanded-observer-runtime-logs-design.md`

## Goal

Replace the current multi-branch observer model in `sp-debug` with a single
mandatory intake path that always produces:

- `causal map`
- `investigation contract`
- `log investigation plan`

before any reproduction, log review, test inspection, source-code read, fix
attempt, or verification action begins.

The purpose of this redesign is not to make `sp-debug` heavier for its own
sake. The purpose is to make the command contractually consistent: every new
debug session must establish a complete causal intake before evidence
collection, so the workflow stops oscillating between optional observer depth,
fast-path shortcuts, and user-declinable expansion branches.

## Problem Statement

`sp-debug` currently carries several front-half dynamic branches:

- `fast-path gate`
- `observer_mode: compressed | full`
- optional expanded observer
- user-approved or user-declined expanded observer

The design work completed on 2026-05-03 and 2026-05-05 improved candidate
quality, family coverage, and runtime log planning, but it still left the
workflow with multiple observer-entry paths. That creates four product
problems:

1. The workflow contract is harder to teach because "observer" means different
   things depending on the branch taken.
2. The runtime state model remains burdened by mode-selection fields instead of
   focusing on gate completion and investigation truth.
3. Template, graph, persistence, and test complexity stays elevated because
   each observer variant must remain live and coherent.
4. Repeated-failure escalation is partially entangled with observer-shape
   selection instead of being focused on stronger evidence and root-cause
   discipline.

The result is a workflow that already knows the right artifacts but still
spends too much semantic space deciding whether to require them fully.

## Locked Decisions

The following decisions are fixed by this design:

- New `sp-debug` sessions do not use `fast-path`.
- New `sp-debug` sessions do not use `compressed observer framing`.
- New `sp-debug` sessions do not use optional expanded observer.
- New `sp-debug` sessions always execute `full + expanded observer` behavior as
  the default intake.
- New `sp-debug` sessions must produce all three intake artifacts before any
  evidence collection or fixing activity:
  - `causal map`
  - `investigation contract`
  - `log investigation plan`
- Repeated failure no longer decides whether the observer gets stronger. It
  only decides whether the downstream investigation upgrades into
  `root_cause`-oriented execution and stronger instrumentation discipline.

## Design Principles

- **One contract, not several observer flavors**: `sp-debug` should teach a
  single intake path, not a menu of early-stage behaviors.
- **Artifacts over mode flags**: the workflow should gate on completed intake
  artifacts, not on whether a thinner or thicker observer mode was selected.
- **Depth may vary, path may not**: simple and complex bugs can differ in
  candidate breadth, queue depth, and lane count, but not in whether complete
  intake happens.
- **Logs are part of intake, not an optional afterthought**: every session must
  establish a structured log investigation plan before investigation begins.
- **Compatibility is a migration concern, not a live product branch**: legacy
  sessions may be read and normalized, but new sessions must not keep old
  branches alive.

## Options Considered

### Option A: Single-Path Hard Contract

Define one mandatory intake path for all new sessions:

`full expanded observer -> causal map -> investigation contract -> log investigation plan -> evidence -> fix -> verify -> human verify`

Advantages:

- Removes the observer-branch state machine instead of merely hiding it.
- Makes templates, runtime, persistence, and tests converge on one semantic
  contract.
- Gives `sp-debug` a clear product identity centered on causal discipline.

Trade-offs:

- Even straightforward bugs still pay the fixed intake cost.
- Legacy compatibility must be handled explicitly instead of relying on old
  branches.

### Option B: Single Default, Hidden Override Paths

Teach and document the single-path contract externally, but keep internal
runtime override branches for compressed or optional observer behavior.

Advantages:

- Smoother migration.
- Easier short-term recovery for unusual legacy states.

Trade-offs:

- The real state machine remains complex.
- Hidden branches tend to become accidental permanent behavior.

### Option C: Template-First Convergence, Runtime Later

Update templates and tests first, while delaying most runtime-state and graph
cleanup until a later pass.

Advantages:

- Fastest to ship.
- Useful only if the immediate goal is prompt-contract experimentation.

Trade-offs:

- Contract and runtime diverge in the interim.
- This repository is building the product surface itself, so a prompt-only
  partial migration is the wrong level of change.

## Selected Model

This design selects **Option A: Single-Path Hard Contract**.

Compatibility remains important, but compatibility is implemented as a
read/normalize/block migration policy rather than as a continuing live branch
of the product contract.

The new canonical flow for fresh sessions is:

`full expanded observer -> causal map -> investigation contract -> log investigation plan -> evidence collection -> fix -> verify -> human verify`

The front half is fixed. The back half remains adaptive in depth, lane count,
and escalation intensity.

## Workflow Contract

### New Canonical Intake

The intake phase is now a mandatory two-subagent sequence that yields three
required artifacts:

1. `Stage 1A: Causal Map`
2. `Stage 1B: Investigation Contract + Log Investigation Plan`

Even though there are two subagent stages, the workflow still produces three
distinct intake artifacts:

- `causal map`
- `investigation contract`
- `log investigation plan`

This keeps the artifact model explicit while avoiding a third front-half
planner stage in the graph.

### Hard Gate Semantics

No stage may enter reproduction, log review, test inspection, source-code
reads, evidence collection, or fixing until all three intake artifacts exist
and are recorded as completed.

The observer gate is therefore no longer "did some observer framing happen?" It
becomes "did the session complete the entire causal intake package?"

### What Still Varies

The following remain intentionally variable:

- family coverage depth
- candidate queue depth
- related-risk target breadth
- evidence-lane count
- downstream use of `one-subagent`, `parallel-subagents`, or
  `subagent-blocked`
- escalation into `root_cause` mode after repeated failure or insufficient
  evidence

What no longer varies is whether the session completes the full intake package.

## State Model

### Keep and Reframe

The following fields remain useful and should stay live:

- `project_runtime_profile`
- `symptom_shape`
- `log_readiness`
- `investigation_mode`

These fields now support evidence planning and downstream escalation rather than
observer-shape selection.

### Retire as Live New-Session Semantics

The following current fields are legacy-only and should no longer govern fresh
sessions:

- `observer_mode`
- `skip_observer_reason`
- `observer_expansion_status`
- `observer_expansion_reason`

They may still be parsed while reading older debug sessions, but new sessions
must not generate them as active workflow choices.

### Canonical Intake Completion Fields

The new state contract should explicitly model intake completion with:

- `causal_map_completed`
- `investigation_contract_completed`
- `log_investigation_plan_completed`

`observer_framing_completed` remains valuable only as a derived summary gate:

`observer_framing_completed = causal_map_completed && investigation_contract_completed && log_investigation_plan_completed`

It must no longer be manually promoted to `true` by a shortcut path.

### Payload Placement

The intake payload should be normalized around three first-class structures:

- `causal_map`
- `investigation_contract`
- `log_investigation_plan`

Recommended payload ownership:

- `dimension_scan` belongs under `causal_map`
- `candidate_board` belongs under `causal_map`
- `top_candidates` belongs under `investigation_contract`
- `log_investigation_plan` is a first-class artifact, not merely an
  "expanded observer" attachment

### State Invariants

Fresh-session invariants:

- `observer_framing_completed` cannot be `true` before all three intake
  completion fields are `true`.
- `evidence`, `reproduction_verified`, log-reading actions, test-inspection
  actions, source-code investigation actions, and fix attempts cannot occur
  before the intake gate passes.
- `fixing` cannot begin while `log_readiness` is still effectively unassessed
  for the active path.
- `awaiting_human_verify` and `resolved` require a completed intake package,
  not merely a successful fix and verification cycle.

## Runtime And Graph Changes

### Fixed Front-Half Graph

The graph should converge on the following front-half sequence:

`Stage 1A Causal Map -> Stage 1B Contract + Log Plan -> Stage 2 Evidence Loop -> Stage 3 Fix -> Stage 4 Verify -> Stage 5 Human Verify`

This removes two front-half branch families:

- `fast-path gate`
- optional expanded observer suggestion and user-decline flow

### Observer Gate Becomes a Completion Gate

The runtime no longer decides whether to route through a thinner or thicker
observer. It only decides whether the mandatory intake package is complete.

The only valid gate check is:

- `causal_map_completed == true`
- `investigation_contract_completed == true`
- `log_investigation_plan_completed == true`

### Two Subagents, Three Artifacts

The recommended runtime responsibility split is:

- think subagent:
  - `causal map`
  - `dimension scan`
  - `family coverage`
  - `candidate board`
- contract-planner subagent:
  - `primary candidate`
  - `contrarian candidate`
  - `candidate queue`
  - `related risk targets`
  - `top candidates`
  - `log investigation plan`
- leader:
  - gate enforcement
  - state updates
  - lane dispatch
  - evidence integration
  - fix and verification admission decisions

### Depth Variation Moves Inside Artifacts

Simple and complex bugs still differ in investigation depth, but that variation
shows up inside the artifacts rather than by choosing different observer paths.

Examples:

- a simpler issue may produce a shorter `candidate_queue`
- a runtime-cross-layer issue may produce a wider `candidate_board`
- a straightforward log surface may yield a small `existing_log_targets` list
- a harder runtime bug may require fuller `candidate_signal_map`,
  `missing_observability`, and `instrumentation_targets`

### Repeated Failure Semantics

Repeated failure no longer reopens observer-selection questions. Instead, it
strengthens the downstream investigation by:

- setting `investigation_mode: root_cause`
- requiring stronger instrumentation or observability work
- generating or refreshing debug-local research checkpoints when needed
- tightening related-risk and falsifier expectations before another fix cycle

## Migration And Compatibility

### Policy

Compatibility follows a strict three-part rule:

- **read old**
- **normalize to new**
- **block unsafe legacy resume**

### New Sessions

Fresh sessions use only the new single-path contract. They must not generate
new live branching semantics for:

- `compressed`
- `skip_observer_reason`
- optional expanded observer
- user-declined expanded observer

### Legacy Session Reads

Older markdown sessions may still contain:

- `observer_mode`
- `skip_observer_reason`
- `observer_expansion_status`
- `observer_expansion_reason`
- `expanded_observer.*` payload structures

The persistence layer should still read these fields so historical work does
not become unreadable.

### Normalize On Write

When a legacy session is resumed and can be represented cleanly under the new
contract, the write path should normalize it into the new structure. For
example:

- legacy `expanded_observer.log_investigation_plan` should be promoted into the
  canonical `log_investigation_plan` location
- legacy observer-shape fields may be preserved for compatibility notes, but
  must not remain the controlling truth for resumed execution

### Unsafe Legacy Resume

If an older session cannot be safely interpreted as satisfying the new intake
gate, the system must not silently assume success. It should explicitly mark
the session as requiring renewed intake, using a clear blocker such as
`legacy-session-needs-reintake`, before evidence collection or fixing resumes.

## Test And Documentation Surface

### Required Product Surfaces

This redesign must propagate through:

- `templates/commands/debug.md`
- `templates/worker-prompts/debug-thinker.md`
- `templates/debug.md`
- `src/specify_cli/debug/schema.py`
- `src/specify_cli/debug/graph.py`
- `src/specify_cli/debug/persistence.py`

If these surfaces do not change together, the product contract will drift.

### Regression Families

The test plan should lock four families of behavior:

1. **Template contract tests**
   - no `fast-path`
   - no `compressed observer framing`
   - no optional expanded observer semantics
   - explicit requirement for `causal map`, `investigation contract`, and
     `log investigation plan` before downstream work
2. **Session template tests**
   - intake completion fields exist
   - state invariants are represented
   - the three-artifact intake contract is visible in the session file
3. **Graph behavior tests**
   - fresh sessions always pass through the fixed intake sequence
   - downstream evidence or fix actions cannot begin early
   - repeated failure upgrades investigation intensity rather than observer
     selection
4. **Persistence compatibility tests**
   - legacy sessions can be read
   - legacy payload can be normalized
   - unsafe legacy resume is blocked explicitly instead of passing silently

### Key Anti-Regression Assertions

The following assertions are especially important:

- new templates do not mention `compressed observer framing`
- new templates do not mention `optional expanded observer`
- new templates do not mention "user can agree or decline"
- new templates do not mention `fast-path`
- `observer_framing_completed` becomes true only after all three intake
  artifacts are complete
- evidence, repro, test, source, and fix actions cannot precede intake
  completion
- repeated failure escalates `root_cause` and instrumentation behavior rather
  than changing observer mode

### Documentation Follow-Through

If `README.md` or `PROJECT-HANDBOOK.md` describe `sp-debug`, they must be
updated to teach the new single-path intake contract rather than the previous
dual-observer or optional-expansion framing.

## Non-Goals

This design does not attempt to:

- remove adaptive downstream investigation behavior
- collapse all evidence work into one lane
- change the same-issue / derived-issue / unrelated-issue lifecycle semantics
- redefine human verification closeout rules beyond requiring completed intake

## Final Decision

`sp-debug` should become a command with a fixed causal-intake front half and an
adaptive investigation back half.

The product contract is therefore:

- fixed intake:
  - `full expanded observer`
  - `causal map`
  - `investigation contract`
  - `log investigation plan`
- adaptive downstream execution:
  - evidence-lane depth
  - candidate-queue depth
  - lane parallelism
  - `root_cause` escalation
- migration rule:
  - `read old / normalize to new / block unsafe legacy resume`

This is the smallest design that actually removes the current front-half branch
complexity instead of merely documenting around it.
