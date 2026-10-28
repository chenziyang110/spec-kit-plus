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

Use `e2e_scenarios.py schema --schema-version 2` for the exact book and trace JSON Schemas and
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

`derive` only expands declared condition/timing obligations and reports design gaps. It
cannot invent an operation or infer the correct behavior. `check` returning
scenario_design_ready is planning accounting only. Keep original expected
behavior separate from actual observations; never prefill passing outcomes.

## Version 2 condition ledger

New books use schema_version 2. The conditions array enumerates each source-
and requirement-bound operation/dimension family before cases are selected.
A boundary supplies its discrete limit, explicit unit and below/at/above expected
outcomes; the helper generates all three obligations. Other families enumerate
partition/state/rule/sequence/example variants with exact input and expected
outcome descriptions. The model must discover those variants; no generic
checklist or algorithm can certify missing product semantics.

Scenario condition_bindings name each condition/variant and its ordered stimulus
step_ids plus oracle_ids. Expected outcomes must match specific bound oracle
assertions. Sibling variants use distinct steps and oracles, not one action
relabelled three ways. Every declared dimension needs condition bindings or the
existing explicit perturbation coverage. Missing families and individual variants
stay visible even when a broad dimension has some test coverage.

Use --require-v2 for derive/check/audit; legacy v1 schemas and reads remain
available only for explicit compatibility inspection. Never relabel an old book
or transplant old passes: author conditions, refreeze the book and execute new
observations. Condition and timing coverage credit cleanly passed scenarios
only; global run completion still rejects any failed/skipped/blocked/not-run/
flaky scenario, even when another scenario covers an overlapping obligation.

## Compound risk and strength review

Before Stage 2 acceptance, preserve a source-backed risk intent for each discovered
high-risk input × boundary/state/timing interaction. Name the interaction cause,
condition variants or event/checkpoint, ordered stimulus and independent outcome
oracle. Expected behavior comes from requirements/rules; unknown expectations or
unobservable checkpoints remain pending with reasons. Use multibyte and
supplementary-plane input when length units matter: ASCII cannot distinguish
bytes, UTF-16 units and code points. Side effects require independent readback.

Read `python .specify/scripts/shared/e2e_assets.py schema strength`, then use
`strength-prepare <risk-intent> --book <v2-book> --root .` and
`strength-audit <frozen-strength> --root .`. This stdout-only helper creates no
runtime state or pass. Register its frozen ordinary asset as a Stage 2 output
and downstream input through the existing E2E owner; separately validate risk
discovery and oracle semantics against the original scope. Ready declarations
are not executed strength. When safely feasible, run a disposable known-wrong
control and prove the oracle detects it; preserve failure and all not-run rows.
Do not mutate product source for a control. Later `strength-audit --trace <trace>`
uses the existing scenario auditor and retains failed, flaky and missing evidence.

## Frozen independent books and impact

Before execution, partition against the accepted original parent request/sources,
all operation and cross-feature obligations, dependencies, gaps and justified
exclusions. Map the entire denominator into independent v2 books and actual
shared journey books; each binds strength assets, fixture definitions and real
target inputs. Read `python .specify/scripts/shared/e2e_assets.py schema bundle`,
then `bundle-prepare <intent> --parent <parent> --root .`. Save its stdout as an
ordinary Stage 2 output, independently accept the frozen bundle, and bind its
exact file digest plus selected books/fixtures/targets in Stage 3/4 packets.
Never partition after failure to reduce an execution denominator.

Before each book execution, author the schema's ordinary `execution_binding`
with `schema_version`, `bundle_file_sha256`, `book_binding_sha256`, `book_id`,
`run_id` and `target`. Stage 3/4 binds its exact bytes. Original trace evidence
contains exactly one log with ID `bundle-execution-binding`, path and SHA-256;
the optional runs index's `execution_binding` references that same file.
Consistency is not proof of creation time, real execution or agent identity;
the independent validator checks actual records and semantic adequacy.

`bundle-impact <bundle> --expected-bundle-sha256 <accepted-Stage-2-file-digest>
--root . [--runs <index>]` detects parent/intent refreeze and source/book/strength/
fixture/target changes, including actual dependent shared journeys. Preserve
original evidence for an unaffected book only when every binding and original
auditor remains valid. Relabelling a runs index or receipt cannot rebind an old
trace. A changed whole-book hash needs fresh whole-book evidence. Design and
preparation reuse never grants a pass to a new run; retain original failed,
flaky, not-run and excluded rows throughout.

## Scenario/native evidence crosswalk

For hybrid execution, read `e2e_assets.py schema crosswalk`. Before execution,
declare native lanes (root, manifest/bindings digests, runner, target, book IDs)
whose native sources are already frozen in associated book sources/fixtures/
target inputs. Map exact scenario/step/oracle IDs and scenario/condition/timing
obligations to native case/journey/parameter IDs, with rationale and requirement
links supporting every many-to-many edge. Retain all unmapped rows as gaps.
Use `crosswalk-prepare <intent> --bundle <bundle> --expected-bundle-sha256
<accepted-bundle-file-digest> --root .`; independently accept the ordinary
Stage 2 output and freeze its raw file digest in Stage 3/4 packets.

The crosswalk `execution_binding` contains exactly `schema_version`,
`crosswalk_file_sha256`, `book_id`, `run_id`, `target`. Preserve its original
file as the trace's unique log evidence `crosswalk-execution-binding`, alongside
the separate `bundle-execution-binding` and exact native report/results/execution
evidence. A declared digest does not prove execution time or process identity.

Run `crosswalk-audit <crosswalk> --expected-crosswalk-sha256
<accepted-crosswalk-file-digest> --expected-bundle-sha256
<accepted-bundle-file-digest> --scenario-runs <bundle-runs-index>
--native-runs <native-runs-index> --root .`. It reuses the original scenario and
coverage auditors and native adapter report interpretation/freshness checks;
retain their reports and all attempts. Missing/unknown/conflicting/duplicate
credit and native failed/skipped/retry/flaky/empty selections remain incomplete
even with a passing visual trace. `crosswalk_accounting_complete` proves
accounting consistency, not product success or a new-run pass. Go remains the
sole workflow state/acceptance owner.

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
