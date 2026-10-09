---
description: Systematically derive E2E tests for desktop, mobile, web, CLI, and service operations; cover abnormal inputs, boundaries, external changes and event order, then execute through available visual-model or runner tools without hiding gaps.
workflow_contract:
  when_to_use: Explicitly requested project-wide, feature-scoped, or regression E2E work; scenario design can precede execution and does not require a web project or an automation harness.
  primary_objective: Identify the complete declared operation inventory, challenge its assumptions, design concrete observable scenarios, execute feasible scenarios through the actual product, and account for every unverified obligation.
  primary_outputs: Runtime-owned task, submission and independent acceptance records, a complete test ledger, source-bound scenario book, immutable per-run visual/action/readback evidence and audit, plus executable assets and native runner reports for selected automation lanes.
  default_handoff: Return scenario-design and execution coverage separately with precise gaps; formal delivery still requires /sp.review followed by /sp.accept.
---

{{spec-kit-include: ../command-partials/common/user-input.md}}

# Scenario-First End-to-End Testing

The primary capability is **test analysis and design**, not a web-runner wrapper.
Desktop/mobile clients, web products, command-line tools, and services are equal
subjects. Use the model's reasoning to discover what should be tested and, when
available, its visual understanding with real interaction tools to execute it.
A visual-model test does not need a Playwright selector or executable test file.
A plan is not a test execution, and a green smoke suite is not full coverage.

{{spec-kit-include: ../command-partials/common/execution-bootstrap.md}}

## Verified Handoffs and the Complete Todo Ledger

Use a leader, bounded execution subagents, and separate read-only validator
subagents for substantive stage work. The leader owns the complete scope,
dependencies, dispatch, integration and acceptance; workers deliver artifacts.
A worker's DONE message, successful tool call, file existence or green check is
a submission, never permission to start a dependent task.

Keep the complete task contract through `specify-runtime e2e`; its owner holds
`.planning/e2e/<run-id>/state.json` and immutable content-addressed snapshots.
Bound inputs, outputs and raw evidence also retain their original bytes through
`archive_ref` entries in `blobs/<raw-sha256>.bin`; preserve these historical
records when a repair writes a new attempt to an existing source path.
An ordinary `tests/e2e/workflow-ledger.md` (or existing equivalent) may index
the records and explain progress; it cannot override runtime acceptance.
Record every requested operation/platform obligation before dispatch, including
unknown, blocked and not-yet-attempted work. Expand scope through `e2e scope-add`
when discovery finds more; do not shrink the denominator to the work already done.

Each task row records `task_id`, stage, `scope_ids`, `depends_on`, worker,
validator, exact input/output paths and revisions or SHA-256 digests,
acceptance rows, reproduction command/manual sequence, preconditions and target,
expected versus actual outcomes, evidence refs, status, and gaps/next action.
Dependency bindings name the accepted producer record and output digest, not a
mutable path or chat summary. Record each acceptance row's verdict and evidence.
Runtime-produced immutable submission/review snapshots hold these bindings;
the mutable ledger is their index, never a frozen input to every later task.
Scenario books, fixture definitions, traces and reports remain ordinary test
assets with their existing schemas. The Go E2E owner enforces task transitions,
complete declared row sets, dependency acceptance, fresh byte bindings and
scoped closeout; the Python helpers remain stateless test-asset validators.

### Negotiate and use the real runtime

Before dispatch, negotiate all ten E2E operations through the installed launcher:

`{{specify-subcmd:specify-runtime api ensure --capabilities e2e.init,e2e.status,e2e.scope-add,e2e.task-start,e2e.task-submit,e2e.review-start,e2e.review-submit,e2e.task-accept,e2e.reopen,e2e.close --format json}}`

Read the bounded input contracts instead of inventing state JSON:

`{{specify-subcmd:specify-runtime api pack --capabilities e2e.init,e2e.scope-add,e2e.task-submit,e2e.review-submit --include-schema --format json}}`

1. Preserve the original request in a scoped test document and reference it as
   an input. Prepare the semantic `e2e-plan-input`: requested target/operation
   scope IDs; all seven stages' task placeholders; complete acceptance criteria;
   input paths; owned output paths; exact dependencies and exclusive resource
   IDs. Future outputs need not exist. Include cross-feature journeys and a
   required row for every selected visual/native/combination audit. Make the
   stage 6/7 rows explicitly reconcile the complete original request. Initial
   discovery uncertainty remains a required obligation, not an omitted scope.
   Initialize once with `e2e init --run-id <run> --leader-id <native-session-id>
   --input-json <object|@path|-> --format json`; never reset an existing run to
   erase unfinished work. Explicit planning-only mode is `planning`.
2. Read `e2e status --run-id <run> --format json` on resume and before selecting
   a next task. `e2e task-start` with the actual worker ID and current
   `--expected-revision` returns the pinned packet, attempt and submission
   template. Dispatch that packet through native subagent tools. Consume the
   standard `worker_task_packet` view and its `worker_task_packet_binding`
   together with the enclosing E2E target, attempt, digests and dependencies;
   the existing shared packet parser accepts that view. A result's `packet_id`
   binds the outer packet digest, not an invented lifecycle field. Consume the
   returned exact upstream snapshots; a `require: passed` dependency is stricter
   than `require: accepted`. Serialize overlapping outputs and declared
   devices/accounts/fixture namespaces; use Work Board ownership across runs.
   Every output-to-input relationship needs a dependency path, including
   cross-target tasks; runtime also refuses overlapping active reads/writes.
3. The worker fills every assigned scope/acceptance pair's actual observation,
   expected result, preconditions, reproduction and raw evidence refs, embeds
   the existing `WorkerTaskResult`, and calls `e2e task-submit --result-json`.
   Use runtime-returned packet bindings and current revision. A successful
   command only submits the result; it cannot accept it.
   A passing result must not contain failed validation rows or nonzero runner
   exit codes; retain the original report instead of normalizing failures away.
4. A separate native subagent uses `e2e review-start` under its actual validator
   ID. Give it the returned original task, full row set, immutable submission
   and raw files. It submits every review row with `e2e review-submit`, stating
   whether it inspected or replayed the check.
   The shared packet validator's review path is explicitly
   `read_only_review=True`; keep its write scope empty and retain the complete
   intent/context/acceptance contract. The leader then calls
   `e2e task-accept` for that verified version. A reviewer that edits an output
   has become an author: obtain a new submission and another validator.
5. On rejection, repair the named rows and produce a new attempt and review.
   On drift or downstream counterevidence, the leader calls `e2e reopen` for
   the earliest affected producer with a reason and evidence. Dependent
   attempts/acceptances are invalidated transitively. Read the returned current
   revision and resume instructions after a conflict; never retry stale argv
   blindly or edit runtime-owned files through another artifact/result channel.

After terminal closeout (`blocked`, `reported`, `complete` or `planning-complete`),
read current `e2e status` before resuming: ordinary task/review/accept mutations
are refused while the run is closed. The leader must explicitly call `e2e reopen`
for the earliest affected task with the current revision, a recovery reason and
evidence. For blocked/reported runs, `next_argv` proposes the earliest unresolved
or nonpassing task; fill its recovery placeholders with the actual reason and
evidence. Passing terminal runs offer no ordinary next action. Preserve the old
closeout and attempt/review history; use the new revision to revalidate the reopened task and
affected descendants. Existing source-drift invalidation and `scope-add` expansion
remain supported reopening routes.

Use inline JSON, project-contained `@path`, or stdin only as documented by
`api pack`; the input is semantic intent, not a hand-written state replacement.
Unavailable E2E capabilities block required acceptance until the runtime is
updated and the same run is rechecked. Never import an old ledger's DONE marks
as accepted receipts or bypass the gate on an older installation.

Recorded distinct IDs are a consistency check, not authentication of separate
agent processes. Native dispatch and independent semantic review remain the
leader's responsibility. Hashes detect changed bytes; they do not prove a
screenshot's provenance, a correct oracle or complete product discovery.

For **each** stage and bounded work item, run this loop:

1. Verify required upstream outputs are `accepted` at the pinned version and
   satisfy this consumer's prerequisites. Only independent dependency-ready
   work may run in parallel; serialize shared files, devices, accounts and
   mutable fixture namespaces. Separate scopes before dispatch and retain
   their parent inventory; never use an unannounced partial scope.
2. Dispatch the original task, complete acceptance rows, exact inputs, owned
   outputs and reproduction/evidence requirements. Track
   `pending -> running -> submitted -> verified -> accepted`; workers may
   submit, the validator may verify, and only the leader may accept.
3. Give a **different** validator the original request/contracts, full scope,
   actual artifacts and raw evidence, not only the producer's summary. Check
   completeness, correctness, source freshness and downstream usability
   against every acceptance row. Inspect captures/readbacks and independently
   replay decisive checks; state which checks were rerun and which inspected.
4. Reject missing, incorrect, stale or irreproducible evidence with exact unmet
   row IDs. Keep the task open, dispatch bounded repair to its worker, obtain a
   new submission and independent validation, then let the leader accept.
   A validator who repairs an artifact becomes its author and cannot validate
   that revision. Use `rejected` or `blocked` explicitly; never auto-check todo.
5. If accepted inputs change or downstream evidence disproves an upstream
   assumption, reopen the earliest affected producer and invalidate dependent
   acceptance transitively. Revalidate before consumers resume. Preserve old
   runs as history. A changed book invalidates its **whole** `book_sha256`
   trace binding: rerun that book, never copy old passes into a new trace.
   Unchanged, independently scoped books may retain their own valid evidence.

An accepted stage artifact is not a passing product. A complete, verified
failure report can feed repair, audit and reporting; it cannot satisfy a
prerequisite requiring successful execution. Missing oracles, fixtures or
platform capabilities block the affected execution scope. Auditing/reporting
may read rejected or blocked records diagnostically without accepting them or
unlocking their dependents. Continue other safe, independent work.

If subagents or necessary validator tools are unavailable, record the actual
capability gap. Safe draft/preparation and a documented self-check may continue,
but required independent acceptance remains blocked; never label a same-agent
second pass independent. Keep working through all ready items after a batch;
stop only at the requested planning-only boundary, verified scoped completion,
or a concrete external/human blocker with evidence and a resume point.

## 1. Establish Scope, Product Inventory, and Capabilities

**Inputs:** The original request, selected project, current requirements and
live source/entrypoint evidence. Start by establishing what product and targets
must be covered; selecting a browser or writing test scripts comes later.

1. Resolve the explicit project/feature and inspect the working tree. Unqualified
   full E2E means the current product, not just the latest diff. A narrower
   feature/regression scope retains affected cross-feature journeys. Never infer
   a feature from a branch name; preserve unrelated work.
2. Read relevant Learning and use project cognition as navigation, verifying
   claims against current requirements, code/configuration, and official product
   entrypoints. Test Design is optional read-only input through its supported
   verification routes; retain its IDs/gaps. Do not create a Test Design `e2e`
   projection, mutate its publications, or require a feature Plan to start.
3. Probe live image inspection, screenshot capture, UI interaction, accessibility,
   filesystem/API observation, fixture setup, and installed runners separately.
   Do not infer them from the agent name. Inspection without interaction cannot
   execute a scenario; interaction without inspection cannot prove visual quality.
   Missing browser automation must not block a usable desktop visual route.
4. Own only scoped test plans, fixtures, tests, adapters, and necessary harness
   configuration. Product source, migrations, design approvals, feature state,
   deployment and production data are outside scope. Never weaken assertions to
   get green. Product defects return to their owner with a reproduction; do not
   silently invoke another workflow. Runtime help/discovery is authoritative:
   use the supported `specify-runtime e2e` owner; never invent `specify e2e` or
   an `execution announce` E2E enum. Use the bootstrap's **other modifying workflows** Work Board route;
   unsupported runtime/cognition tokens are capability gaps, not permission to
   impersonate another workflow or hand-write runtime state.
5. Use isolated test accounts/data, deterministic setup, per-worker namespaces,
   reset/cleanup, service readiness and actual build/OS/device/entrypoint notes.
   External deletion/rename/permission changes target only explicit disposable
   fixtures. Production transactions, real payments/messages, credentials,
   dependency installation/upgrades, licenses and external writes require their
   existing authorization. An unavailable external dependency is a blocked test,
   never a reason to substitute a mock and call it full-stack coverage.

### Identify actual target capabilities

Record each declared product target separately; a framework name does not prove
that its installed build can run here. Keep build/source identity, OS/runtime
version, browser or device/simulator identity, installation/launch route, accounts,
service dependencies, inspection, interaction, independent readback and reset
capabilities with probe evidence. Scope target variants from the request and
supported product surfaces, not from the easiest available tool.

| Product surface | Establish before claiming its execution is available |
| --- | --- |
| Web app | Actual deployed/local build and URL, required browser targets, session, UI capture/control and backend readback. |
| Desktop app: Windows, Linux, macOS | Actual native package/process/window on each declared OS, UI/accessibility or supported driver, filesystem/OS/backend effects. A browser renderer alone does not prove the desktop shell. |
| iOS / iPadOS | Installed app/build and bundle identity, declared simulator or physical device/OS, launch/control/capture, permission and lifecycle controls, observable app/backend state. Simulator evidence is not physical-device evidence. |
| Android | Installed package/build, emulator or physical device/OS, actual activity/launch/control/capture, permission/lifecycle controls and state readback. |
| CLI, service, library or other software | Its real consumer entrypoint: command/process, API/job/message, consumer program, extension host or device/protocol. Bind observable outputs/effects and an actual harness or manual route; do not force a UI. |

Missing infrastructure is a named blocker, never evidence that a platform is
not applicable. Use the platform's available tools; the current native wrapper
supports serial pytest and local Playwright Test only. Other native/mobile or
device routes require working interaction tools or validated adapters.

### Discover Operations Before Selecting Test Cases

Reconcile intended requirements/acceptance/design contracts with implemented
menus, routes, commands, permissions, objects, jobs, integrations and persisted
state. Existing tests do not define the denominator. Give operations and
requirements stable IDs and source refs; record unread/unknown surfaces and
contradictions as discovery gaps rather than silently shrinking scope.

For each operation describe its user goal, real entrypoint, object identity,
preconditions, assumed invariants, lifecycle, dependencies and observable effects.
Write assumptions explicitly: for example, the file still exists, still denotes
the same object, has the required permissions, and the destination is available.
Challenge each assumption: false initially, invalidated during the operation,
restored before retry, or invalidated together with a related assumption.

Use the installed Python 3.11+ interpreter to retrieve the shared question set:

```text
python .specify/scripts/shared/e2e_scenarios.py catalog
python .specify/scripts/shared/e2e_scenarios.py schema --schema-version 2
```

For **every operation**, decide applicability for `happy_path`,
`input_partitions`, `input_boundaries`, `object_lifecycle`, `external_mutation`,
`event_order`, `permissions`, `conflict_concurrency`, `repeat_cancel_retry`,
`interruption_recovery`, `persistence_consistency`, `environment_compatibility`,
`visual_interaction`, and `cross_feature`. Add product-specific dimensions when
needed. A not-applicable decision needs a concrete reason and bound source;
missing tools, fixtures, time, or oracle knowledge are gaps, not inapplicability.
Do not label one happy-path case with every dimension to satisfy a checker.

**Outputs:** A source-bound target/capability matrix and complete declared
requirement/operation inventory in the test ledger/book draft, with source refs,
assumptions, cross-feature dependencies and named discovery/capability gaps.
**Acceptance:** A separate validator reconciles the request and live entrypoints
against the inventory, including negative/unknown surfaces and every declared
target. The leader accepts the exact inventory version. Unresolved semantics
remain gaps; they cannot become invented oracles downstream.

## 2. Derive Concrete Scenarios, Including Event Order

**Inputs:** The accepted stage 1 inventory, target matrix, source contracts and
gap IDs. Work against these IDs; do not reconstruct scope from existing tests.

Apply error guessing to assumptions and failure history; equivalence partitioning
to valid/invalid input classes; boundary value analysis to exact discovered limits
and units; decision tables to interacting business rules; state-transition and
event-sequence analysis to lifecycle and ordering. Use these as complementary
ways to discover test conditions, not synonyms for pairwise parameter coverage.
Unknown expected behavior is an oracle gap, not an invented product rule.

For rename, ask about missing/moved/externally renamed/replaced objects, a new
object at the old path, target-name conflicts, permission/lock changes, invalid
names, exact length boundaries, duplicate confirmation, cancel/retry, interruption,
other windows/search/open documents, and persisted contents/identity. Determine
actual OS/filesystem/product rules first; never hard-code a universal illegal
character set, maximum length, or whether length counts bytes or characters.
Include keyboard/IME composition, focus and pending feedback when applicable.

Separate these scenarios: absent before entry; deleted after opening the dialog;
deleted after editing but before confirming; change during a pending operation;
and change after commit but before UI refresh. Define observable checkpoints and
external events independently. Each selected **event x checkpoint** is a separate
coverage obligation. Prove that the change actually occurred at that checkpoint
before continuing. Use deterministic barriers or supported test hooks for a
narrow race; a guessed sleep or fast click is not proof of race coverage. If the
checkpoint cannot be reached or observed, keep its case blocked. A check/use
race may be a TOCTOU risk; do not diagnose a vulnerability from timing alone.

Freeze `tests/e2e/scenarios.json` (or the project's established equivalent) with
source_revision and hashes of every selected source/contract/config/fixture.
The ordinary test-asset book contains sources, requirements, operations,
applicability decisions, checkpoints/events, scenarios, discovery_gaps and
exclusions with scope/reason/owner. It is not runtime-owned workflow state.
Each scenario contains stable ID, operation, requirements, dimensions, technique,
priority, preconditions, ordered actor/action/observation steps, exact perturbation
step bindings, visual and independent-effect oracles, execution route, safety,
and cleanup. Each oracle names an assertion and how to observe it. Keep clear
expected and actual observations in different records.

```text
python .specify/scripts/shared/e2e_scenarios.py derive tests/e2e/scenarios.json --root . --require-v2
python .specify/scripts/shared/e2e_scenarios.py check tests/e2e/scenarios.json --root . --require-v2
```

`derive` expands timing obligations and exposes gaps; it does not invent correct
scenarios. `check` verifies declared accounting. `scenario_design_ready` is only
planning readiness, never tests passed. Review the generated gaps, author missing
scenarios, and rerun. Preserve high-risk compound situations explicitly; budgets
may prioritize execution but must never remove the unexecuted denominator.

### Concrete condition coverage, not dimension labels

Author new books as `schema_version: 2`. Add `conditions` with stable ID,
operation, dimension, kind, title, bound source_refs and requirements. For
`partition`, `state`, `rule`, `sequence` or `example`, enumerate distinct
`variants: [{id, input, expected}]`. A `boundary` instead declares
`boundary: {limit, unit, expectations: {below, at, above}}`; the helper derives
L-1, L and L+1 as distinct obligations in that verified discrete unit. It does
not generate suitable strings or choose the expected business rule. Unknown
limits, units, variants or outcomes remain discovery gaps, not guessed values.

Every scenario has `condition_bindings: [{condition, variant, step_ids,
oracle_ids}]`. Bind the actual stimulus steps in order and specific oracle IDs;
at least one bound oracle assertion must exactly equal the variant's expected
outcome. Sibling variants need distinct steps and oracles; a generic happy-path
step cannot satisfy all boundary points. Every applicable dimension needs a
condition family, except timing already accounted by event x checkpoint pairs.
A scenario's dimension label without a condition or timing binding remains a gap.

Use `--require-v2` at every derive/check/audit gate. The helper retains v1 reads
for explicit legacy inspection only; never silently downgrade, relabel a v1 book,
or carry old trace observations into new conditions. Author missing conditions,
rebind the whole book and run fresh evidence. Report `condition_coverage` and
`timing_coverage` separately: only cleanly passed scenarios credit obligations;
failed/skipped/blocked/not_run/flaky variants remain visible. These checks bind
declared semantics, not proof of correct discovery, perception or t-way coverage.

**Outputs:** The frozen schema-v2 scenario book, derive/check outputs, complete
condition/timing denominators, expected oracles and gap/exclusion ledger.
**Acceptance:** The validator challenges discovery, source-backed limits and
units, applicability, scenario/requirement mappings and oracle adequacy, then
reruns `derive/check --require-v2`. Machine readiness alone cannot accept the
book. Keep the full parent inventory if independently validated ready scopes
need separate books; blocked remainder IDs must stay visible. Planning-only
work proceeds to stage 6 design audit and stage 7 reporting with execution
explicitly unrequested.

## 3. Prepare and Verify Execution Readiness

**Inputs:** The accepted stage 1 target matrix and stage 2 book. Select
`visual`, `runner`, `hybrid` or `human` per scenario from actual capabilities.
Prepare authorized isolated accounts, services, fixture setup/reset/cleanup,
observable oracles and event barriers. Prove launch/readiness through the real
entrypoint with a bounded smoke action and independent effect readback; record
this as readiness evidence, not full scenario coverage. Freeze fixture
definitions/seeds/scripts, not temporary objects deliberately mutated or deleted
during execution; their changing state belongs in run evidence.

**Outputs:** A readiness record bound to the accepted book, actual build/target,
route and exact run instructions, test/fixture hashes, per-case runner bindings
where used, successful setup/readback/reset probes, and remaining blocker IDs.
**Acceptance:** A separate validator reproduces the launch and decisive
observation/reset probes, checks account/fixture isolation and all required
channels, and reconciles every scenario to a ready route or explicit blocker.
Do not execute a dependent case whose required channel, fixture or target is
unready. Setup failure is not a product pass or a reason to drop the case.

### Optional Combination and Native Automation Preparation

After discovering dimensions and ordered scenarios, use the existing
`e2e_coverage.py plan` for applicable constrained factor combinations. Ordinary
pairwise strength is not exhaustive; known high-risk higher-order combinations
remain mandatory. Use higher strength or exhaustive bounded matrices where
needed. Invalid actions the product must reject are required negative tests,
not infeasible exclusions. Exclude only proven impossible configurations.
Budget failure requires explicit partition/budget/scope decisions retaining
cross-feature journeys, never silent sampling or strength reduction.

```text
python .specify/scripts/shared/e2e_coverage.py plan tests/e2e/coverage-manifest.json --root . --max-cases 1000
```

Preserve every generated E2E-* ID/variant and requirement mapping when expanding
scenario cards or runnable tests. Independently reconcile the full generated
case set to the scenario book; the scenario checker does not calculate t-way
coverage. New combinations, conditions or changed frozen inputs return to
stage 2 for a new accepted book before readiness. Compare actual runner
collection with the complete plan; reject missing/unknown/duplicate IDs.

Reuse `e2e_runner.py` for supported serial pytest or local Playwright Test;
other harnesses need validated adapters. Do not rebuild a supported adapter
or install a runner without authorization. No distributed pytest or shard
merging is supported; partial shards cannot close a full manifest. Optional
automation is a route choice, not an entry gate for client testing.

## 4. Execute Through the Actual Product and Capture Evidence

**Inputs:** The accepted stage 2 book and stage 3 readiness/bindings for this
exact target and scope. Recheck prerequisites and hashes before each task; a
missing required observation blocks that case.

Choose `visual`, `runner`, `hybrid`, or `human` per scenario, based on actual
capabilities and required observations. Default client interaction work to visual
model + UI tools when available; auxiliary tools may prepare fixtures and verify
side effects. Do not spend the task building a new automation framework when
real client interaction and evidence capture already suffice.

For a visual/hybrid scenario, observe the initial screen and selected object;
perform a bounded action; capture the resulting state; compare it with the
specific expected checkpoint; continue only from the actually observed state.
Reacquire controls after layout changes instead of replaying stale coordinates.
Record screenshots and action observations at relevant checkpoints, including
external-change proof, final feedback, focus/recovery and cleanup. Preserve
registered design/source-continuity IDs. A screenshot is visual evidence, not
proof of file identity, durable storage, server state, or correct background work:
verify those through independent filesystem/API/CLI/database/log readback.
Unavailable effect oracles remain blocked or pending, even if the UI looks right.

Retain every attempt; fail-then-pass is flaky. Failed, skipped, blocked, disabled,
quarantined and not_run scenarios are not passes. Bounded test-harness repair is
agent-owned; product bugs keep their failed evidence. New discoveries append
scenarios and invalidate the old book binding; never manufacture old observations
for new cases. Source/config/test changes require fresh evidence. Keep immutable
run IDs, actual target/build identity, capture times, hashes, action observations,
oracle observations and cleanup in a new run-specific trace.

```text
python .specify/scripts/shared/e2e_scenarios.py audit tests/e2e/scenarios.json --root . --trace test-results/e2e/run-001/trace.json --require-v2
```

Bind book_sha256 to the exact scenario book. This is a visual/mixed trace
consistency audit, not an assertion that the model
really acted or saw pixels. It requires every declared step/oracle of a passing
case, matching evidence channels, verified cleanup and current source binding.
No test_ref, pytest result or Playwright project is required for visual cases.
Do not fabricate native-runner reports from visual observations.

### Native execution when selected

Run the verified route and retain native reports, actual argv and exit status,
timestamps, `test_sources` hashes, `manifest_sha256` and `source_revision`.
The native wrapper checks before/after source/test bytes and retains all
phases, retries, teardown and global failures. Never let a shell pipeline hide
runner failure.

```text
python .specify/scripts/shared/e2e_runner.py tests/e2e/coverage-manifest.json --bindings tests/e2e/bindings.json --root . --runner pytest --target local-test-build --output-dir test-results/e2e/run-001 -- tests/e2e -q
python .specify/scripts/shared/e2e_coverage.py audit tests/e2e/coverage-manifest.json --root . --results test-results/e2e/run-001/results.json --max-cases 1000
```

A scenario trace cannot override a failed native audit or certify t-way coverage.
**Outputs:** Immutable per-run raw captures, action/effect observations, all
attempts, cleanup, trace and each selected native report/audit, with every
scenario's actual status. **Acceptance:** A separate validator checks full ID
accounting, original evidence, observation channels, target/build identity and
hashes, and replays decisive assertions. Accept faithful failed-run evidence
for repair; never turn that acceptance into a passing test outcome.

## 5. Repair Owned Test Problems and Re-run Affected Work

**Inputs:** Accepted run evidence plus every rejected acceptance row, failed,
flaky, blocked or not_run scenario and its cause. Classify a product defect,
harness/fixture error, unavailable capability and unknown oracle separately.
Use a falsifiable explanation and original reproduction; do not retry
speculative patches or change expectations until the suite turns green.

Repair only owned tests, fixtures, adapters and harness configuration within
authorization. Product-source or business-rule defects retain their reproduction
and return to the owning workflow/person; do not implicitly invoke Quick/Debug
or change the product. Continue independent feasible tests while those cases
remain failed/blocked. State a bounded recovery budget and the next evidence
needed when repeated attempts do not improve the explanation.

After repair or an authorized owner's new product build, re-enter the earliest
affected stage: inventory/oracle changes at 1/2, book/test/config/fixture or
route changes at 2/3, execution at 4. Reaccept changed inputs and obtain fresh
run evidence; preserve every original failed attempt. Fail-then-pass retries
on unchanged inputs remain flaky. A new, corrected version may earn a fresh
result but must not rewrite the failed version's history.

**Outputs:** A defect/repair ledger with owner, causal evidence, affected IDs,
changed versions, fresh regression runs and concrete unresolved blockers.
**Acceptance:** A different validator reproduces the original failing behavior
against the corrected version, verifies the expected repair and affected
cross-feature regressions, and confirms unchanged denominator and assertions.
When no repair is needed, record the checked no-repair disposition. Rejected
repairs return to this loop; a product/capability blocker cannot be self-waived.

## 6. Independently Reconcile Scope, Coverage and Evidence

**Inputs:** The original request and accepted stage 1-5 artifacts, complete todo,
all original attempts, exclusions/gaps and **every** selected visual/native
audit. Diagnostic review may consume blocked/rejected records to report gaps;
it must not convert those records into accepted prerequisites.

Use an independent validator to reconcile requested targets/operations ->
requirements -> conditions/timing obligations -> scenarios -> actual attempts ->
clean passes. Check set differences, omitted and duplicate IDs, source-backed
not-applicable decisions, boundaries, negative cases, event order, compound risks
and the substance of each assertion. Inspect original captures and independent
effects; replay critical journeys/decisive checks on each target supporting a
pass claim. A tested web route cannot certify an untested native/mobile target.

**Outputs:** An independent audit with per-acceptance-row verdicts, evidence and
replay refs, full counts/IDs, missing coverage, exclusions and required rework.
**Acceptance:** The leader checks every row and selected lane audit. Machine
checks cannot prove omitted discovery, authentic observations or correct
oracles. Reject unresolved gaps for any full-scope pass. Newly discovered
omissions return to the earliest affected stage and invalidate its consumers;
repeat the review after repair. No independent reviewer means independence
remains blocked, even if a documented self-check is useful.

## 7. Report and Close the Verified Scope

**Inputs:** Stage 6 audit, exact accepted artifact versions, final todo and all
open blockers. **Outputs:** A reproducible report linking inventory, book,
readiness, runs, repairs and audit, with separate design completeness, execution
coverage, observed outcomes, combination coverage and visual/interaction
acceptance. Give per-target counts and all failed/skipped/blocked/flaky/not_run
IDs, discovery gaps, exclusions, evidence refs and fresh hashes.

**Acceptance:** Independently check the report against the full ledger and
original request before leader closeout. Every requested item must be accepted
against its actual criteria or explicitly unresolved with owner/evidence/resume;
any unresolved mandatory item prevents a full-scope success claim. Item-level
passes also require integrated cross-feature verification. Evidence of only
3 of 10 requested items is progress, never completion of 10.

An explicit planning-only request reports design validation and unexecuted
scenarios without an execution claim. Otherwise continue feasible execution
until complete or concretely blocked. A blocked report is a partial result,
not a completed E2E run. Preserve missing visual comparison as
pending-human-review. Never claim absolute completeness, product acceptance or
release safety. Formal delivery remains `tasks -> implement -> review -> accept`;
E2E supplies additional evidence and cannot bypass those owners.

After independent acceptance of the stage 7 report, call the runtime's
`e2e close` with the current revision, leader ID and observed
`--outcome pass|failed|blocked`. It rechecks the whole required task/evidence
chain; 3/10 accepted items cannot close a 10-item run as passed. Planning mode
never yields product execution success. An accepted failure report may be
reported, while unaccepted obligations remain blocked. Stages 6/7 may use the
explicit `task-start --diagnostic` route to document blocked/rejected work;
that route cannot create a passing observation or unlock successful consumers.

### Test-only asset mutation closeout

When this invocation changes retained test assets, harness configuration or
behavior-bearing test documentation, apply the shared closeout below using only
those explicitly owned changed paths. Disposable run data and read-only
planning/inspection do not justify a fabricated mutation receipt. The canonical
identity is `sp-e2e`; an older runtime rejecting it remains a compatibility
blocker, never a reason to impersonate Implement or Review.

{{spec-kit-include: ../command-partials/common/inline-project-cognition-update.md}}

{{spec-kit-include: ../command-partials/common/learning-layer.md}}

At a blocked exit preserve stage, category, owner, exact cause, sanitized evidence,
attempted recovery, affected IDs, next action, observable unblock criteria and
exact resume point. Keep agent-capable repair agent-owned; never request secrets
or ask the user to reconstruct runtime state. Resume by checking source/book
hashes and obligations; do not reuse stale evidence or silently retarget scope.
Close Work only after its actual supported verification, never a fabricated pass.
