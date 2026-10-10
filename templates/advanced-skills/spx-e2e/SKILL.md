---
name: spx-e2e
description: Advanced user-invoked scenario-first E2E testing for desktop, mobile, web, CLI, and services; systematically derive abnormal, boundary, state and timing cases, then execute through visual-model tools or suitable runners with explicit coverage gaps.
---

# Scenario-first E2E

Run only when explicitly invoked. Read `references/project-cognition.md` and
`references/project-learning.md`; use live evidence, not cognition, as truth.
Apply `references/execution-bootstrap.md` through the other-modifying-workflows
Work Board route. `specify-runtime e2e` owns verified task handoffs; do not add
an execution Activity enum. Use supported help/discovery; do not impersonate a different workflow when a token
is unsupported. Read `references/blocker-resolution.md` at blocked boundaries.

Own scoped test assets, fixtures, adapters, harness configuration and ordinary
results. Product behavior, migrations, approvals, Test Design publications and
feature lifecycle state retain their owners. Test Design is optional, read-only
input through supported verification; preserve its IDs/gaps without inventing a
projection consumer. Product defects retain reproductions for their owner; do
not weaken assertions or invoke another workflow implicitly.

## Operating plan

Coordinate the seven stages with the following rules. This is orchestration over
existing runtime contracts, not a new schema, mode, scheduler or acceptance owner.

### Intent and execution boundary

Resolve product/feature, targets, outcome, authorization and resource/time limits
from the current request and live inputs; retain the original request and later
changes separately. Do not re-ask resolved questions. Keep unknown product
semantics and external authorization explicit while advancing independent work.

Default E2E is `execution`. Explicit design-only, case preparation or user-owned
later testing selects `planning` for a new run: author the package and handoff,
without application launches, smoke actions, test runs, CI polling or scheduled
test work. Separate read-only source/tool discovery and permitted design checks
from execution. Proposed instructions are not successful probes; deferred design
checks cannot establish validated readiness. Stages 3-5 remain unexecuted, with
all requested targets/scenarios retained. The runtime assigns planning Stage
3-5 tasks `not_requested`; that is distinct from scenario-level `not_run`.

If execution is deferred mid-run, stop new dispatch and checkpoint active native
workers safely, retaining attempts and cleanup. Do not change frozen mode or
remove tasks; use diagnostic reporting and supported truthful closeout. Later
execution of a planning package requires explicit authorization and an execution
run linked to the prior package/request, with current Stage 1-3 bindings. Do not
import planning acceptance as execution receipts or reset unfinished runs.

### Scope graph and artifact ownership

Keep a complete parent inventory and a compact scheduling index in the existing
ledger: target/operation IDs, stage tasks, books/manifests, route, input/output
owners, exclusive resources and unfinished obligations. Those columns are not
extra JSON keys. `api pack` owns `mode/scope/tasks` and task
`id/stage/scope_ids/depends_on/acceptance/inputs/outputs/resources`.

- Freeze independent target/operation scopes and outputs before execution, with
  all seven stage placeholders, unavailable targets, cross-feature journeys and
  discovery gaps. Expand only through `scope-add` without dropping old scope.
- Declare actual producer dependencies for inventory -> design -> readiness ->
  execution -> repair disposition -> reconciliation -> report, plus every other
  consumed output. Stage 6 consumes relevant Stage 1-5 artifacts; Stage 7 binds
  its audit and claim inputs. Include implicit runtime edges: every overlapping
  producer at the previous requested stage, and all earlier requested stages
  for Stage 6/7. Planning Stage 6 follows Stage 2, omitting unrequested 3-5.
  Explicit edges cannot weaken these requirements; inspect the effective graph.
  Do not serialize unrelated same-stage scopes. Use `passed` for design/
  readiness for execution, and `accepted` for usable factual failure reports.
  Never relax the former to unblock work.
- A task must cover every assigned scope/acceptance pair. Group only scopes with
  genuinely common criteria; otherwise split before freezing. Independently
  accepted scopes may pipeline without an all-platform barrier. Shared inputs,
  services and resources still block their consumers. Preserve a global join
  over the parent inventory and cross-feature obligations.
- One owner writes each canonical revision. Parallel discovery/design workers
  write owned fragments; an integration task consumes accepted fragments,
  reconciles IDs/conflicts and owns the canonical inventory/book. No concurrent
  appends to one book or leader ledger. Keep independently bound scope artifacts
  separate from the mutable parent index; real input drift still invalidates.

### Native workers, revisions and joins

Divide useful work by independent evidence/write scope: intent versus live
entrypoints, distinct operation families, isolated targets/fixtures, and review
of exact submissions. Keep actual native task/session references; roles, shell
processes and identity strings are not agents. Select concurrency from available
slots and ready non-conflicting work, reserving capacity for independent review.
One slot allows sequential author and different validator, not self-approval.
Reuse workers only without violating authorship independence. Validators must
not have authored/repaired the task or any dependency ancestor under review;
check recorded author history, not only the current worker ID. Stage 6 authors
and final reviewers must also be independent of audited work. Missing delegation
permits honest drafting, not invented acceptance.

Dispatch the runtime packet/binding with original task, all assigned IDs/criteria,
accepted input digests, owned outputs/resources, necessary context, observation
and safety requirements and return channel. Reuse unchanged scoped context;
expand unresolved refs instead of broadcasting the full repository/history.
This never skips mandatory freshness checks. Return pinned artifact/evidence
refs and concise decisions, not repeated raw files in chat.

Coordinate revision-changing calls on the leader path. Parallel work does not
permit shared stale `--expected-revision`: obtain the current revision per call
and inspect conflicts rather than retry blindly. Review completed handoffs as
they arrive; unrelated slow lanes need not delay an independent acceptance.

On idle/timeout/disconnection, inspect actual native and runtime status, retain
diagnostics, and establish worker/process resource ownership before reassigning.
Use supported stop/join controls; uncertain ownership blocks the namespace.
Never duplicate a writer, hand-edit state or invent cancellation/lease commands.
At joins reconcile assigned/returned IDs, exact accepted inputs, targets, selected
audits and cleanup; route discrepancies to the original producer.

### Coverage-preserving efficiency

Before readiness connect target/operation -> requirement -> condition/boundary
unit/event-checkpoint -> scenario -> oracle -> cleanup. Challenge roles/tenants,
locale/encoding, data scale, transitions, external failure, durability and
cross-feature effects where source makes them applicable. Unknown rules stay
gaps. Deduplicate only same-target cases with equivalent preconditions, stimuli,
event order, effects and cleanup while retaining all distinct bindings. Titles
or shared helpers are insufficient; never collapse distinct boundaries, timing,
roles, projects or platforms. Multiple routes cannot double-credit one scenario.

During authorized execution, prefer proven readiness first, then critical
permissions/data-loss/persistence and regressions, remaining partitions/boundaries
and mandatory combinations, and resource-sensitive interruption/concurrency and
cross-feature joins as dependencies allow. This schedules rather than truncates
the required set; do not postpone high-risk timing solely by category. One shared
readiness failure blocks its affected cases instead of triggering a failure storm.

Reuse immutable current builds/definitions/instructions, not mutable case state.
Name accounts, databases, queues, directories, devices and UI sessions as actual
resources. Different directories do not isolate a shared desktop or account.
Observe/reset independent cases; retain continuity inside ordered journeys.
Prefer an available route that satisfies the oracle over building a new harness.
Avoid redundant visual/native work unless distinct evidence is required; once
selected, both audits remain required. Supported native workers do not imply
xdist or shard merging. Partition books before execution, retain parent/cross-
scope accounting, and never transplant passes or concatenate partial reports.

Budgets govern scheduling, not acceptance. Distinguish measured setup/execution/
review/repair/blocked costs from estimates. At a limit checkpoint safely and
retain every unfinished ID plus continuation. Do not poll unchanged failures,
rerun passes or idle to fill a duration; scheduled follow-ups are not continuous
multi-agent execution.

### Causal recovery and user handoff

Return missing operations/targets/rules to Stage 1; wrong conditions, units,
oracles or changed combinations/books to Stage 2; launch/account/fixture/channel/
reset gaps to Stage 3; missing or inconsistent raw observations to their Stage 4
producer or earlier changed-input owner. Preserve invalid evidence and capture a
fresh run; never rehash changed bytes to certify previously parsed observations.
Stage 5 routes justified product defects to the product owner and test-only
repairs through the original Stage 2/3 owner. Reopen before changing pinned bytes,
reaccept prerequisites, rerun Stage 4, then regenerate the repair disposition.
Cleanup/ownership uncertainty stops namespace reuse; never wipe unowned resources.
Stage 6/7 repairs reporting discrepancies or reopens a disproven upstream owner.

Deduplicate causal investigation only with evidence, retaining all affected IDs
and attempts. A bounded retry needs a hypothesis, changed recovery condition and
expected new observation. Stable policy/capability failure requires new recovery
evidence, not repeated launches, widened permissions or disabled controls.
Nonpassing per-case combination attachments are unvalidated diagnostic metadata:
validate files needed by diagnosis before consuming them as evidence. No-repair
requires an observed current run; no execution cannot justify that disposition.

For user-owned testing or an authorized pause, reuse the ordinary test-asset
area/ledger to deliver exact request and authorization, source/target identity,
inventory/book/manifest/bindings digests, every condition/timing/scenario mapping,
and all gaps. Include per-target prerequisites, role and secret variable names
(no values), setup/launch/reset/cleanup, ordered steps and justified expected
UI/durable effects, selected route/selectors, evidence recording locations and
fields, original-report retention, failure routing and later audit instructions.
Mark proposed commands/unresolved parameters and unperformed capability probes;
never supply fabricated sample passes.

Include runtime run/task/revision refs when present, accepted versus unaccepted
artifacts, active-resource disposition, next owner/stage and observable resume
prerequisites. Resume from fresh status, not stale mutation argv. Outstanding
execution remains `not_run` with the user-deferral reason, not exclusion/pass.
Report authored, independently reviewed, executed and user-owned work separately.
Package delivery does not imply runtime acceptance, human/visual approval, full
E2E success or permission to bypass Review/Accept.

## Execution and dependency contract

The leader freezes the complete requested denominator through the Go
`specify-runtime e2e` owner. Its state and immutable snapshots live under
`.planning/e2e/<run-id>/`; never write them directly. An ordinary
`tests/e2e/workflow-ledger.md`, or an existing equivalent, may index these
records but cannot grant acceptance. Every stable todo row has
`task_id`, `stage`, `scope_ids`, `depends_on`, worker and validator identities,
input/output refs with exact versions and SHA-256 hashes, `acceptance_rows`,
expected versus actual results, evidence refs, status, blocker and `next_action`.
Keep immutable submission and review snapshots; the ledger is their mutable
index. Accepted dependencies bind actual artifact digests and those snapshots,
not the continuously updated ledger as an immutable input. Updating another
row must not invalidate an unchanged accepted artifact.
Distinguish task-delivery status from the tested product's outcome. Record which
dependencies require a complete factual report and which require success.

Use bounded subagents to author substantive stage work and separate read-only
validator subagents to check it. Schedule them serially when slots are scarce;
concurrency is not a prerequisite for independence. Validators must not author
or repair the outputs they review. Give each worker the original task, full
scope/acceptance rows, exact accepted prerequisite refs, write ownership,
required outputs and evidence, and the failure/resume contract. Parallelize
only work whose dependencies are satisfied and whose writes/fixtures do not
conflict; the leader owns joins and integration.

The lifecycle is `pending -> running -> submitted -> verified -> accepted`.
A worker's completion claim reaches only submitted. A validator reads the
original task, the full denominator and every acceptance row, inspects actual
outputs and raw evidence, and reproduces checks when needed. It records an
expected/actual/evidence verdict per row. The leader accepts only that exact
verified output version, then releases dependents. Reject incomplete work back
to its author for repair and another independent review; retain rejection and
attempt history. File existence, task count, an aggregate PASS or a worker's
summary is not acceptance.

Only accepted exact upstream refs/hashes satisfy dependency inputs; the consumer
rechecks them before use. Partial work never satisfies a readiness prerequisite.
An accepted, complete failure report can feed repair, audit or reporting; it
cannot satisfy a prerequisite that requires the product to pass. Keep blocked
scope IDs in the full denominator while advancing independent ready scopes.
If subagent or independent-validator capability is unavailable, safely draft
work and continue other independent tasks, but mark the required acceptance
blocked. A same-agent second pass cannot impersonate independent acceptance.

Changed inputs, newly discovered obligations or disproven evidence reopen the
earliest affected stage and invalidate dependent acceptances. Revalidate their
inputs and rerun affected work; retain unaffected evidence only while its exact
bindings remain valid. A changed `book_sha256` requires a fresh trace for the
whole book, including every previously passed scenario; never transplant old
passes. Only books partitioned and independently frozen before execution may
have independently retained evidence, with shared/cross-feature obligations
still accounted for. The Go owner enforces complete declared rows, transitions,
accepted dependencies, byte freshness and scoped closeout. Scenario/trace
schemas and Python helpers remain ordinary test-asset accounting contracts.

### Runtime protocol

Negotiate the actual installed capabilities before dispatch:

`{{specify-subcmd:specify-runtime api ensure --capabilities e2e.init,e2e.status,e2e.scope-add,e2e.task-start,e2e.task-submit,e2e.review-start,e2e.review-submit,e2e.task-accept,e2e.reopen,e2e.close --format json}}`

`{{specify-subcmd:specify-runtime api pack --capabilities e2e.init,e2e.scope-add,e2e.task-submit,e2e.review-submit --include-schema --format json}}`

- Preserve a reference to the original request. `e2e init --run-id <run>
  --leader-id <native-session-id> --input-json <object|@path|-> --format json`
  freezes the semantic plan: every target/operation, seven-stage task
  placeholders, full acceptance criteria, inputs, owned outputs, dependencies
  and exclusive resources. Future outputs need not exist. Include mandatory
  selected visual/native/combination audit and integrated-journey rows. Stage
  6/7 must reconcile the original request, including discovery uncertainty.
  Use mode `planning` only for an explicit planning-only request. Never reset
  a run or import old ledger checkmarks to evade outstanding obligations.
- Resume with `e2e status`. Use current `--expected-revision` and actual native
  identities for mutations. `task-start` returns the pinned WorkerTaskPacket,
  attempt and submission template; dispatch it through native subagent tools.
  Pass the existing shared parser its `worker_task_packet` view, keeping
  `worker_task_packet_binding` and the enclosing E2E scope/attempt/dependency
  contract. The result's `packet_id` is the outer packet digest. Both worker
  and review start use this shared packet shape.
  Keep complete intent/context fields. Shared validation uses default
  execution checks for workers and explicit `read_only_review=True` for
  reviewers, with no writes or produced artifacts granted to the reviewer.
  Dependencies distinguish `require: accepted` reports from `require: passed`
  prerequisites. Each submitted scope/acceptance pair needs expected/actual,
  reproduction, preconditions and raw evidence through `task-submit` with
  the existing normalized WorkerTaskResult embedded in `--result-json`.
  Failed validation rows and nonzero runner exit codes cannot accompany pass.
- `review-start` binds a separate validator to the exact submission and full
  original task. `review-submit` accounts for every row and records inspected
  versus replayed checks; only the leader's `task-accept` unlocks consumers.
  If a reviewer repairs outputs, obtain a new author submission and another
  validator. Use returned templates/argv; do not fabricate lifecycle fields.
- `scope-add` expands the denominator without removing old requirements.
  `reopen` records a reason/evidence and invalidates descendants after changed
  inputs or counterevidence. On rejection, repair, resubmit and independently
  revalidate. Inspect current revision after conflicts rather than replaying
  stale commands. Do not write via generic artifact/result mutation channels.
- Serialize declared shared resources and outputs; use Work Board across runs.
  Declare a dependency path for every producer output consumed as an input,
  including across targets. Active reads/writes may not conflict. Keep raw
  bytes via the runtime's `archive_ref` in `blobs/<raw-sha256>.bin`; reusing a
  source path for a repair must preserve the old failed evidence and review.
  Missing capabilities remain a compatibility blocker until an updated runtime
  can verify the run. Safe drafting can continue without accepted receipts.

Terminal `blocked`/`reported`/`complete`/`planning-complete` runs refuse ordinary
task, review and acceptance mutations. Resume from current `e2e status` through
the leader's explicit `e2e reopen`, binding the current revision, recovery reason
and evidence. Blocked/reported `next_argv` selects the earliest unresolved or
nonpassing task and leaves placeholders for the actual recovery reason/evidence;
passing terminal runs have no ordinary next action. Retain prior closeout,
attempt and review history; use the new revision to revalidate the affected task
and descendants. Source-drift invalidation and `scope-add` expansion keep their
existing reopening behavior.

Distinct recorded identities do not authenticate native agent processes;
actually launch separate workers and validators. Hashes prove byte bindings,
not truthful observations, adequate oracles or complete discovery. The leader
and independent reviewer still own those semantic judgments.

Run all seven stages for an execution request. Do not stop at discovery or a
scenario book because the work is long. Continue agent-capable recovery and all
safe independent work until every requested item has an accepted deliverable or
a genuine external blocker with an exact resume action. An explicit planning-only
request may take an accepted Stage 2 package to a scoped Stage 6/7 design report;
Stages 3-5 remain unexecuted, never passed. Stages 6/7 may inspect clearly marked
blocked/rejected material diagnostically to report partial progress, without
promoting any earlier stage to accepted or any product outcome to passed.

## 1. Establish scope, real inventory and platform capabilities

**Inputs:** The explicit request/project/feature, approved requirements/design,
verified read-only Test Design inputs when present, and live project evidence.

Inspect the working tree and resolve scope without inferring a feature from a
branch. Full-product E2E is not changed-files-only; narrower scope retains its
cross-feature regressions. Independently reconcile requirements with actual
menus, screens, APIs, commands, objects, permissions, jobs, integrations and
state. Existing tests never define the universe. Assign stable scope/operation
IDs, identify missing/unread surfaces and contradictions as discovery gaps,
and retain evidence-backed exclusions separately from unavailable execution.

Record the actual build/source revision and official entrypoint for each
requested target, with a capability matrix:

| Target | Required environment and capability evidence |
| --- | --- |
| Web | Actual app/build, browser/version, OS and viewport; inspect/capture, interact, independent state readback and reset. |
| Desktop: Windows, Linux, macOS | Actual native build, OS/version and display/session; native inspection/capture and input, filesystem/service readback and reset. |
| iOS/iPadOS | Actual app/build, OS/version, device or simulator and permissions; inspect/interact, durable-effect readback and fixture/reset control. |
| Android | Actual app/build, OS/version, device or emulator and permissions; inspect/interact, durable-effect readback and fixture/reset control. |
| CLI, services and other software | Actual binary/service/build and runtime environment, official command/API/device entrypoint, observable effects, readback and reset appropriate to the system. |

Probe image inspection, capture, interaction, accessibility, fixture control,
readback, runners and native subagents separately; never infer them from the
integration name. Record supported targets that are unavailable as blocked.
A web smoke run cannot stand in for native execution. A visible screen without
interaction is not execution; an action without inspection is not visual review.

**Outputs:** Versioned scope/operation inventory, requirement/source mappings,
platform/capability matrix, discovery gaps/exclusions and the complete todo
ledger with dependencies and acceptance rows.

**Acceptance:** Independent review reconciles the requested and discovered
inventory, platform targets and evidence. No missing feature or unavailable
platform disappears from the denominator. Only exact accepted scoped inventory
and capability facts feed Stage 2; incomplete discovery remains explicit.

## 2. Derive and validate the scenario book

**Inputs:** Accepted Stage 1 scope IDs, inventory, source/requirement bindings,
platform facts and known gaps.

Read `references/scenario-design.md` before authoring the book. For every stable
operation identify its user goal, object identity, real entrypoint, assumptions,
lifecycle and side effects. Challenge assumptions initially, during execution,
on retry and in risky combinations. Combine error guessing, equivalence
partitioning, boundary value analysis, decision tables, state-transition and
event-sequence testing. An unknown expected outcome is an oracle gap; pairwise
factors neither discover missing conditions nor establish event order.

```text
python .specify/scripts/shared/e2e_scenarios.py catalog
python .specify/scripts/shared/e2e_scenarios.py schema --schema-version 2
python .specify/scripts/shared/e2e_scenarios.py derive tests/e2e/scenarios.json --root . --require-v2
python .specify/scripts/shared/e2e_scenarios.py check tests/e2e/scenarios.json --root . --require-v2
```

Use `schema_version: 2`. Decide every catalog dimension per operation with
source-backed not-applicable reasons; add product-specific dimensions. Each
applicable dimension needs source/requirement-bound `conditions` unless explicit
event x checkpoint accounting already owns it. Enumerate
`variants: [{id, input, expected}]` for partition/state/rule/sequence/example
families. Boundaries declare `{limit, unit, expectations: {below, at, above}}`
under `boundary`; derive L-1/L/L+1 in the verified discrete unit. For rename,
resolve actual platform/product legality and name/path limits first; never
invent a universal limit, illegal character set or expected error UI.

Every card carries preconditions, ordered actor/action/observation steps,
perturbation step bindings, oracles with assertion/channel/check, execution
route, priority, safety and cleanup. Bind `condition_bindings: [{condition,
variant, step_ids, oracle_ids}]` to exact ordered stimuli and outcome assertions;
sibling variants need distinct steps/oracles. A happy path relabelled with many
dimensions does not cover their obligations. Preserve design/source-continuity
IDs and read `references/ui-quality-gate.md` when applicable.

Declare observable checkpoints and external events independently. The helper
derives each declared event x checkpoint obligation: deletion before opening
and deletion before confirmation differ; external rename and replacement at
the old path differ. Require proof of the mutation at its precise checkpoint,
using a deterministic barrier/test hook for narrow races. A guessed sleep is not
timing evidence. Unobservable timing remains blocked. Preserve identity/content
and independent readback.

Freeze `source_revision` and hashes of selected requirements, source, config and
fixture definitions/seeds/setup-reset scripts. Do not put temporary mutable
fixture instances that a scenario will rename/delete into constant `sources`;
record their setup and changing state as run evidence. Keep the book an ordinary
test asset, not runtime workflow state, a Test Design publication or acceptance.

**Outputs:** Frozen v2 scenario book/digest, complete condition/timing obligations,
derive/check results, source bindings and scoped oracle/discovery gaps.

**Acceptance:** Validator reconciles every requested operation/requirement and
applicable dimension with concrete conditions, steps and oracles, checks exact
v2 outputs and rejects invalid/stale books. Readiness gaps block their affected
scope; an accepted gap report does not make that scope execution-ready. Keep
independent ready scope and the whole denominator visible. Use `--require-v2`
on derive/check/audit; v1 is explicit legacy inspection, not a downgrade escape.
`scenario_design_ready` proves declared design accounting only, not tests passed
or complete discovery. Never finish an execution request here.

## 3. Prove execution readiness and prepare optional automation

For a build/package/native-test operation, optionally retrieve methods. First
negotiate `{{specify-subcmd:specify-runtime api ensure --capabilities playbook.find,playbook.show --format json}}`;
if unavailable, continue E2E's own verification without method reuse. Otherwise use
`{{specify-subcmd:specify-runtime playbook find --query <operation-goal> --format json}}`.
Expand only matching pinned `show_argv` and needed `expand_argv`; verify live
scripts, prerequisites, scope, and outputs. Reuse is read-only advice inside the
current E2E Work, retaining every scenario/condition ID, the complete verification
denominator, execution ledger, and visual/acceptance gates. Do not implicitly
invoke DO, create another Work/DoSession, or replace fresh evidence with method history.

**Inputs:** Exact accepted Stage 1 target/capability facts and Stage 2 book,
conditions, oracles and scope-specific readiness dependencies.

Select visual-model, runner, hybrid or human execution per card. Desktop/mobile
clients may use live model inspection and UI tools without an automation
harness. Confirm the actual build/OS/device/browser and official entrypoint,
readiness/health, authorized isolated accounts/data, deterministic fixtures,
per-worker namespaces, observable barriers, independent oracles and verified
reset/cleanup. Prove inspect/interact/readback/reset capability before relying
on it. Freeze fixture definitions and runner/test bindings before execution;
mutable test data belongs to the run, not constant source hashes.

External mutations target disposable fixtures only. Production actions, real
payments/messages, credentials, dependency installation/upgrades, licensing and
external writes retain authorization gates. Missing tools, required oracles or
readiness dependencies block affected scope; they do not authorize mocks,
smaller denominators or a different platform masquerading as the target.

When combinations are needed, discover dimensions/ordered journeys first:

```text
python .specify/scripts/shared/e2e_coverage.py plan tests/e2e/coverage-manifest.json --root . --max-cases 1000
```

Ordinary pairwise is not exhaustive; mandatory known-risk higher-order cases
survive selection. Use higher strength or exhaustive enumeration for critical
bounded matrices. Invalid user actions needing rejection are negative tests,
not infeasible constraints. Budget failure cannot silently lower strength or
sample; any partition must retain cross-feature obligations. Map the full
case/variant set into cards or tests and independently reconcile IDs; the
scenario checker does not calculate t-way coverage.
If combination planning adds cases/conditions or changes the book, return to
Stage 2, refreeze and independently accept the revised book before Stage 3
readiness or execution. Never append obligations to an accepted execution packet.

For serial pytest/local Playwright Test reuse `e2e_runner.py`, prepare exact
bindings and verify full native runner collection against the planned set
before execution. Bind `manifest_sha256`, `source_revision`, `test_sources`,
selectors/projects and asserted requirements. Collection is readiness evidence,
not executed coverage. Other harnesses require validated adapters; installing
one still needs authorization. Distributed pytest and shard merging are not
supported; partial shards cannot close a full manifest.

**Outputs:** Versioned execution packets per candidate ready scope, environment/
build and capability evidence, fixture/reset/oracle proofs, route decisions, and optional
combination plan, test bindings and collection reconciliation.

**Acceptance:** Independent validator can identify how every planned assertion,
external event and cleanup will be observed on the actual target. Exact inputs
and IDs match; required authorization/readiness exists before actions start.
Missing prerequisites block their dependent cards while other ready scopes
continue. A passing smoke or collector cannot mark scenarios passed.

## 4. Execute and retain original evidence

**Inputs:** Accepted exact book/version and Stage 3 execution packets for ready
scope, fixture definitions, target/build bindings and selected route contracts.

Observe the initial screen/target, perform bounded actions, inspect actual
feedback and reacquire controls after state/layout changes; do not replay stale
coordinates. Prove external events at planned checkpoints.
A screenshot is not proof of durable files/server state: side effects need independent
filesystem/API/CLI/database/log readback. Missing oracles remain blocked even
when the screen appears correct. Verify cleanup and preserve its observations.

Separate expected from actual observations. Record every attempt, actual
executor/target/build, times, original captures/logs and step/oracle evidence in
a new immutable run. Failure followed by retry-pass on the unchanged version is
flaky; failed/skipped/blocked/
disabled/quarantined/not_run cases never become clean passes. Do not turn visual
observations into invented runner output. Native execution retains original
reports, actual attempts/exit codes, collection and binding evidence, including
global/teardown failures and retries. Never hide failures in a shell pipeline.
The native wrapper checks source/test hashes before and after execution.

```text
python .specify/scripts/shared/e2e_scenarios.py audit tests/e2e/scenarios.json --root . --trace test-results/e2e/run-001/trace.json --require-v2
python .specify/scripts/shared/e2e_coverage.py audit tests/e2e/coverage-manifest.json --root . --results test-results/e2e/run-001/results.json --max-cases 1000
```

Run the second audit only for a selected combination/native lane. Scenario audit
checks `book_sha256`, `source_revision`, fresh source/evidence hashes, complete
step/oracle observations and channels, cleanup and every scenario ID. It needs
no pytest `test_ref` or Playwright project for visual cases. It is local
consistency, not attestation that the model acted, inspected pixels or asserted
the correct outcome. A visual trace cannot override a failed native audit or
certify t-way coverage; retain every selected lane's audit independently.

**Outputs:** Immutable trace/native reports, raw evidence, full attempt/status
records, scenario and applicable native/combination audits, and scoped defects,
readiness blockers or oracle gaps.

**Acceptance:** Validator checks real evidence against every executed card and
accepted inputs, including cleanup and absent results as `not_run`. A complete,
truthful failure report may be accepted for Stage 5 repair and later diagnosis;
it does not mean that the product passed. Dependents requiring success stay
blocked.

## 5. Repair the test harness or hand off product defects, then rerun

**Inputs:** Accepted Stage 4 result/failure reports and exact reproductions,
source/fixture/test versions, blocked rows and original expected outcomes.

Diagnose harness/setup failure, product defect, missing capability and oracle
uncertainty separately. Keep bounded test-harness repair agent-owned within the
existing authorized write scope; preserve failed product evidence and return
product fixes to their owner with reproduction, expected/actual behavior,
source/build/evidence refs and the exact rerun target. Do not edit product
behavior, migrations or feature state, weaken assertions to obtain green, or
implicitly invoke Debug/Implement. Missing product intent remains an oracle gap.

Before patching, state a falsifiable causal explanation from the failure evidence
and the observation that would disprove it; reject speculative patches. Repeated
failure requires stronger causal evidence and revised, bounded recovery with an
explicit next check and stopping condition, not another blind retry. Escalate
only at the genuine external boundaries described above.

Before changing pinned test assets, record the diagnosis and intended repair.
The leader calls `e2e reopen` for the earliest owning producer before any bound
bytes change. Dispatch the correction through that producer's new `task-start`
packet and returned write scope; Stage 5 cannot gain competing ownership of an
upstream output or edit it through its current packet. Independently reaccept
the corrected producer and affected readiness, obtain fresh Stage 4 execution,
then regenerate the Stage 5 repair disposition.
Source/test/config/fixture-definition changes require fresh bound evidence;
a changed book requires an entirely fresh trace for that book. Preserve failed
attempts and retries rather than overwriting them. Continue repairs and safe
independent scenarios; genuine external boundaries keep affected rows blocked.
An actual correction can establish a fresh pass on its new source/build with
matching evidence; retain the earlier failure and its version in history.

**Outputs:** Reviewed test-only fixes and fresh run/audit refs, or a complete
product-defect/blocker handoff with owner, recovery attempts, next action and
observable unblock criteria; each failed or missing row has a disposition.
When no repair is needed, emit a checked no-repair disposition bound to the
accepted current run and audit references.

**Acceptance:** Independent validator reproduces the repaired failure and checks
regressions/fresh bindings, or verifies the concrete handoff and remaining
blocker, or confirms the no-repair disposition against the full accepted run.
The leader reaccepts changed prerequisites before dependents resume.
A handoff is an accepted report, never a passed product test or repaired defect.

## 6. Independently reconcile inventory, coverage and evidence

**Inputs:** Exact accepted artifacts across Stages 1-5 and the complete ledger;
clearly labelled blocked/rejected records are diagnostic input only.

Use a read-only validator independent of the reviewed work's authors. Re-read
the original request, source inventory and acceptance rows, not just worker
summaries. Reconcile every requested platform/operation/requirement through
conditions and event/checkpoint obligations to scenario IDs, optional planned
combinations and collected tests, actual attempts, raw evidence and cleanup.
Challenge applicability, boundary rules, compound risks and assertion adequacy;
replay necessary checks through available authorized tools. Record each row's
expected/actual result, evidence, accepted version and verdict.

Report condition_coverage and timing_coverage separately, crediting only clean
passes. Preserve all failed/skipped/blocked/not_run/flaky cases and every
selected native audit; no overlap, retry or visual trace erases their failure.
Reconcile todo counts and IDs with the frozen denominator, including exclusions
and capability gaps. Reject unsupported evidence and return defects to the
earliest responsible stage. No checker proves full discovery, semantic oracle
correctness or perceptual truth. If independence is unavailable, audit acceptance
is blocked; a documented same-agent second pass is not a substitute.

**Outputs:** Independent row-level reconciliation, discrepancy/repair list,
coverage totals with exact denominators, evidence bindings and scoped verdicts.

**Acceptance:** The leader can trace every requested item and every verdict to
its original obligation and inspected evidence. An audit may accept a complete
partial/failure report, but cannot mark incomplete prerequisites accepted or
promote product outcomes. Any required successful dependency remains blocked
until repaired and independently verified.

## 7. Close out with a truthful result and exact continuation

**Inputs:** Accepted Stage 6 reconciliation, exact result/audit refs, full ledger
and defect dispositions. Diagnostic blocked material permits only a clearly
qualified partial report, not a successful completion claim.

Report design coverage, execution coverage, observed outcomes, combination
coverage and visual acceptance separately, with all denominators, gaps,
exclusions, source/book/manifest hashes, target/build identities and evidence
refs. Give each requested item its accepted deliverable or concrete external
blocker. Missing visual comparison remains `pending-human-review`; no absolute
completeness, release safety or human acceptance claim. Formal delivery remains
`tasks -> implement -> review -> accept`.

After independently accepting the report, use `e2e close` with the current
revision, leader and observed `--outcome pass|failed|blocked`. Its full task and
evidence recheck prevents partial work from becoming a passing closeout.
Planning completion has no product-pass claim; accepted failure reports remain
reports and unresolved mandatory work stays blocked. For diagnostic stage 6/7
reporting, `task-start --diagnostic` may inspect blocked/rejected upstream
records but cannot produce a passing observation or unlock success dependencies.

When retained test assets, harness configuration or behavior-bearing test docs
change, use `references/project-cognition.md` with canonical workflow `sp-e2e`
and the exact owned changed paths:

`{{specify-subcmd:specify-runtime cognition closeout-plan --workflow sp-e2e --scope-dir <test-scope> --scope-mode explicit --changed-path <owned-test-path> --format json}}`

Repeat `--changed-path` for every owned endpoint. Fill only the returned
semantic/disposition and passing verification fields, then execute structured
`apply_argv`. Shared apply owns update, validation, eligible finalization and
the bound mutation receipt. Require its receipt-bound finalizer to succeed
before claiming clean completion. Consume supported recovery; do not invent
verification results, a receipt or an E2E stage/Activity. If required validation
is not passing, retain the failed/partial status rather than forcing closeout.
Disposable run data and read-only planning do not justify a mutation receipt.
Runtime rejection is a compatibility blocker, not permission to impersonate a
different workflow. Use `references/project-learning.md` for relevant,
evidence-backed lessons; preserve explicit rule-promotion approval.

**Outputs:** Verified scoped final/partial report, updated ledger, exact resume
instructions and any required runtime-owned mutation receipt.

**Acceptance:** Independent review and leader acceptance cover the report's
claims as well as its evidence; all requested rows reconcile. Successful E2E
requires all in-scope required readiness, executions, oracles, cleanup and
reviews to pass on the bound targets, with every selected audit satisfied.
Delivering an accepted failure report is not successful E2E. Close Work only
with supported fresh verification, never a fabricated pass.

At every blocked exit retain stage, category, owner, exact cause, sanitized
evidence, attempted recovery, affected IDs, next action, observable unblock
criteria and exact resume point. Do not request secrets or transfer
agent-capable repair to the user. Resume by checking hashes/obligations, never
stale chat memory, and continue independent safe work while blockers remain.
