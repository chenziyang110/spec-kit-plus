# Operation-level scenario design

Read before deriving the E2E book. This is a test-analysis method, not a second
workflow, new runtime state machine, or a dependency on browser automation.
The model owns grounded scenario discovery and oracle design. The helper owns
explicit field shapes, declared-dimension accounting and timing/trace checks.

## Derivation sequence

1. Discover the operation independently from tests: intended user goal, actual
   entrypoint, object identity, preconditions, lifecycle and external effects.
   Reconcile implemented behavior with approved requirements; preserve conflicts.
2. List assumptions. Negate each initially, invalidate it at a specific stage,
   retry after restoration, and combine related high-consequence failures.
   Error guessing is a discovery aid, not random enumeration.
3. Partition inputs by behavior; locate actual boundaries and their units.
   Derive decision-rule combinations and state transitions, including rejected
   transitions. Never invent a limit, illegal character set, or UI message.
4. Enumerate other actors and external events independently from checkpoints.
   Expand selected event/checkpoint pairs. Describe the observable synchronization
   condition, mutation action and independent proof before continuing the user
   flow. An unreachable checkpoint is a blocker, not a tested race.
5. Specify each card's setup, ordered steps, assertions and observation channels,
   reset/cleanup, safety, risk priority and actual execution route. Different
   expected outcomes need different cards. Parameter rows never replace order.
6. Independently challenge the resulting inventory, excluded conditions, oracle
   adequacy and compound risks. Filling required fields does not prove semantics.

## Rename example: generate candidate obligations, not universal rules

For a supported client rename action, review at least these candidate families
against the real product. Missing applicability evidence stays a design gap.

| Family | Concrete challenges |
| --- | --- |
| Identity/lifecycle | Already deleted, externally renamed/moved, replaced by another object at the old path; distinguish identity from a displayed name. |
| Timing | Before entry, dialog open, editing complete but before confirm, pending, after commit before refresh. The same event at different points is not one test. |
| Name partitions | Empty/whitespace, same name, conflicting destination, supported Unicode and normalization/case equivalence, product-specific invalid values. |
| Name/path boundaries | Determine limits and units first; below/at/above each relevant name and full-path boundary, including multi-byte input when applicable. |
| Rules/concurrency | Target created by another actor, permission or lock changed, two windows acting on the same object, permission plus conflict combinations. |
| Input mechanics | Keyboard confirm, double activation, IME composition, paste, focus/selection preservation, disabled/pending actions. |
| Recovery | Cancel then reopen, failure then edit/retry, interruption/restart, undo where supported. |
| Consistency | Independent path/content readback, unrelated files unchanged, list/search/recent items/open documents/other windows updated. |

A candidate is not a guaranteed supported requirement. Resolve intended behavior
from sources. Safety invariants such as not falsely reporting success and not
modifying an unrelated object can be checked separately from unspecified UX.
Do not assume the application must follow a particular filename-versus-identity
strategy without a product contract. A check/use timing risk is not by itself a
confirmed TOCTOU vulnerability.

## Scenario book and helper

Use `e2e_scenarios.py schema` for the exact book and trace JSON Schemas and
`catalog` for the question set. `check` also enforces cross-links and fresh
project-contained source hashes. Every operation has every standard dimension;
custom dimensions are additive. Each not-applicable decision carries a reason
and source refs. Available tools do not determine feature applicability.

Operations own `checkpoints: [{id, observation}]` and
`events: [{id, change, checkpoints}]`. Each scenario's
`perturbations: [{event, checkpoint, step_id}]` binds a required timing pair to
an actual explicit step. The checker detects an uncovered event/checkpoint even
when another scenario covers the same event at a different time.

Scenarios own ordered `steps: [{id, actor, action, observe}]` and
`oracles: [{id, channel, assertion, check}]`. Actors can be user, visual-model,
fixture, system, runner or human; observation channels are visual, filesystem,
API, CLI, database, log, accessibility or human. Side-effecting operations need
an independent-effect oracle; visual/accessibility/human judgment alone does
not close durable-state proof. A missing readback tool is a blocked execution,
not permission to delete the oracle from the design.

`derive` only expands declared timing obligations and reports design gaps. It
cannot invent an operation or infer the correct behavior. `check` returning
scenario_design_ready is planning accounting only. Keep original expected
behavior separate from actual observations; never prefill passing outcomes.

## Visual execution protocol

Observe the actual screen and target before an action. Execute bounded actions
with the live interaction tool, capture/inspect checkpoints, and continue from
observed feedback. Reacquire targets after layout changes; stale coordinates
can act on the wrong object. Use isolated fixture tooling for external events,
with proof of when the change occurred. Mere elapsed time is not a barrier.

For each run record actual executor/target/build identity and times. Evidence
rows bind ID, declared kind, project-relative path, SHA-256 and capture time.
Each passed attempt binds every step and every oracle to actual observations
and evidence IDs, and records verified cleanup. Match evidence kind to oracle
channel: a screenshot cannot fill a filesystem oracle. Keep original captures,
logs and all attempts; fail-then-pass stays flaky. Failed/skipped/blocked/not-run
and cleanup failures cannot close the run. Unexecuted cards stay in the book.

The trace checker cannot attest that captures are authentic, the model inspected
them, commands really ran, or assertions were adequate. Native-runner lanes also
require their original runner/coverage audit; trace green cannot erase native
failure or establish t-way coverage. Preserve all exclusions, discovery gaps,
visual-review qualifications and the Review/Accept boundary.
