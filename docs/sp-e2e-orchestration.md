# E2E operating plan and user-owned execution

This guide describes the orchestration policy embedded in both
[Classic E2E](../templates/commands/e2e.md) and
[Advanced E2E](../templates/advanced-skills/spx-e2e/SKILL.md). Read the
[seven-stage contract](sp-e2e.md) for the owning runtime and evidence semantics.
The policy improves how an agent organizes work; it does not implement a new
scheduler, extend the JSON schemas or make an execution claim.

## Choose the requested outcome first

A normal E2E invocation proceeds through discovery, design, readiness, execution,
repair, reconciliation and reporting. Explicit requests to design cases or leave
execution to the user select the existing `planning` mode for a new run. They
produce a source-bound scenario package and actionable handoff, not application
launches, readiness smoke runs, CI polling or automatic test jobs.

Read-only inventory, an instruction to launch an application, an executed
readiness probe and a passing scenario are four different things. Label proposed
commands and unperformed checks explicitly. If design validation is also deferred,
the package is authored but not validated. Runtime Stage 3-5 tasks in planning
mode are `not_requested`; an execution handoff lists unexecuted scenarios as
`not_run`. Do not invent a new deferred task status or mark unavailable targets
not applicable.

Deferral during an existing execution run stops new dispatch and safely settles
active workers; it does not rewrite the frozen mode or erase earlier attempts.
Diagnostic Stage 6/7 reporting can preserve incomplete work. Runtime closeout
still needs its required independent acceptance; delivering a handoff without
that acceptance must not be described as a completed runtime run. Later execution
of a planning package requires explicit authorization and a linked execution run,
with current inventory, book, target and readiness bindings checked anew.

Editing the E2E workflow source itself is repository maintenance, not an implicit
invocation of the generated E2E workflow. Deferring maintenance tests does not
remove the generated product's execution, evidence or Review/Accept contracts.
The author may deliver implementation changes for user testing without claiming
that the modified workflow has executed successfully.

## Shape the work graph around real dependencies

Keep the whole requested target/operation universe, including unread surfaces,
in one parent inventory. Use independently versioned scoped artifacts and a
mutable scheduling index; do not make a constantly changing index the immutable
input to every downstream task.

Each lane identifies target/operation and requirement IDs, seven-stage task IDs,
book/manifest references, route, owned outputs, actual shared resources and
unfinished obligations. These are descriptive ledger columns, not additional
fields in runtime JSON. The runtime plan continues to use `mode`, `scope`,
`tasks` and the task schema advertised by `api pack`.

The effective graph is not only the authored `depends_on` list. The Go owner
adds every overlapping previous-stage producer as a dependency. Stage 6/7 also
join earlier requested stages in their scope; planning Stage 6 follows Stage 2
and skips unrequested Stages 3-5. Explicit edges cannot weaken these implicit
requirements. Cross-target output consumption needs its own dependency path.

Use a passing prerequisite for execution readiness, and an accepted factual
report for repair or diagnosis. Accepting a complete failure report does not
make its product outcome pass. A task's acceptance criteria apply to every
assigned scope: split heterogeneous targets instead of submitting inapplicable
criteria with invented verdicts.

Two disjoint, independently accepted scopes may progress at different stages.
For example, missing mobile hardware need not block a CLI lane, but their shared
identity service or mutable test account may. Do not create a global barrier at
every stage solely for convenience. A final global reconciliation still includes
all targets, shared inputs and cross-feature journeys.

One task owns each canonical output revision. Parallel analysts can author
separate fragments, while an integration task consumes accepted fragments,
resolves conflicting IDs and owns the canonical inventory or book. This avoids
several workers appending to the same file. A same-stage integration edge remains
an explicit producer dependency and must not introduce a cycle.

## Dispatch and accept independently

Split work by evidence and write ownership rather than a fixed list of model
roles: intended requirements versus actual entrypoints; independent operation
families; isolated target/fixture execution; and read-only review of submissions.
Keep real native task/session references. A role name, process count or heartbeat
does not establish a subagent or a completed handoff.

Choose parallelism from actual slots and ready non-conflicting work. Reserve
review capacity; one slot can execute an author and then a different validator.
The validator must not have authored or repaired the output or a dependency
ancestor under review. Stage 6 authors and final reviewers must be independent
of audited work. A missing validator permits honest drafting, not self-approval.

Packets carry the original task, complete assigned IDs and criteria, accepted
input digests, owned output/resources, necessary context, expected observations,
safety boundary and result channel. Reuse unchanged scoped context instead of
broadcasting the whole repository or chat history. Do not omit freshness checks.
Review complete submissions as they arrive instead of waiting for unrelated
slow lanes.

Parallel work does not permit concurrent mutations using a stale runtime
revision. Coordinate revision-changing calls and obtain the current revision
for each mutation. On conflict, inspect state before deciding the next action.
On timeout or disconnection, establish whether the native worker/process still
owns resources before reassignment. Use actual supported stop/join controls;
uncertain ownership blocks the namespace. No invented cancel command, lease
override or manual state repair is permitted.

## Reduce overhead without losing coverage

Maintain the trace from target/operation to requirements, conditions and exact
boundary units, event/checkpoint obligations, scenarios, oracles and cleanup.
Challenge roles/tenants, locale/encoding, data size, state transitions, external
failures, durability and cross-feature effects against actual product evidence.
Unknown rules stay gaps. A similar title or shared helper does not justify
merging cases with different boundaries, timing, roles, projects or platforms.
Equivalent cases may share execution only when every distinct obligation and
required observation remains represented; do not double-count multiple routes.

During authorized execution, prioritize proven readiness, critical permission/
data-loss/persistence journeys and regressions, remaining partitions and required
combinations, and resource-sensitive interruption/concurrency and integrated
journeys as dependencies allow. This changes order, never the required set.
A failed common readiness probe should produce one causal diagnosis with all
impacted IDs, not a storm of identical failing launches.

Reuse current immutable builds and fixture definitions, not dirty runtime state.
Directories alone do not isolate a shared desktop session, account, queue or
database. Reset independent cases and observe their initial state; keep deliberate
multi-step journey continuity intact. Select the available route that can prove
the oracle rather than automatically building a new harness. When visual and
native lanes both supply necessary evidence, retain both audits. Native workers
are not distributed-pytest support; pre-frozen independent books are not shard
merging or permission to copy passing results into a new book.

Budgets schedule work, not success. Distinguish measurements from estimates,
retain all unfinished IDs at the limit and checkpoint active work safely. Do not
idle, poll unchanged failures or repeat passing cases to fill a duration.
Scheduled follow-ups are not continuous multi-agent execution.

## Recover at the earliest responsible stage

| Problem | Return point | Preserve |
| --- | --- | --- |
| Missing operation/target or unclear product rule | Stage 1, then affected design | Source conflict, gap and original request |
| Wrong condition, boundary unit, oracle or book | Stage 2 | Previous book, rejected rows and changed bindings |
| Launch/account/fixture/channel/reset unavailable | Stage 3 | Capability evidence and all affected scenario IDs |
| Invalid or mismatched raw execution evidence | Stage 4 or earlier changed-input owner | Original reports, captures, bindings and failed attempt |
| Justified product defect | Product owner via Stage 5 | Minimal reproduction, build, expected/actual effect |
| Test-only harness/configuration defect | Original Stage 2/3 owner via Stage 5 | Causal explanation and fresh producer attempt |
| Cleanup fails or ownership is unknown | Resource owner, affected Stage 3/4 | Unsettled resources; do not reuse or wipe them |
| Missing target/lane or incorrect report claim | Stage 6/7 or disproven upstream owner | Full set differences, not rewritten evidence |

Reopen a pinned producer before editing its bytes, independently reaccept the
correction and readiness, obtain fresh execution, then regenerate the repair
disposition. No execution cannot justify a no-repair disposition. Every retry
needs a hypothesis, new recovery condition, expected observation and finite
limit. Stable policy failure requires new recovery evidence, not disabled
controls or wider permissions.

Nonpassing per-case attachments in the combination audit retain their existing
unvalidated diagnostic status. Validate the actual files needed by diagnosis;
neither their presence nor a task summary proves authentic product behavior.
Preserve attempt history and the existing flaky/failed/non-run semantics.

## Deliver an executable handoff, not a passing summary

A user-owned testing package reuses ordinary test assets and the existing ledger.
It contains exact request/authorization and source/target identity; inventory,
book, manifest and bindings references/digests; every condition/timing/scenario
mapping; all gaps and exclusions with their reasons; and accepted versus
unaccepted artifact versions.

Per target, include account roles and secret variable names without values,
prerequisites, proposed setup/launch/reset/cleanup, ordered case steps and
source-backed expected UI and durable effects, route/selectors, evidence
locations/fields, original-report retention and later audit instructions. Clearly
mark unrun probes, unresolved command parameters and missing oracles. Do not
create sample passes, synthetic reviews or a second workflow-state system.

Include runtime run/task/revision references if present, active-resource
disposition, next stage/owner and observable prerequisites. Resume with fresh
status rather than cached mutation argv. Report authored, independently reviewed,
actually executed and user-owned work separately. Package delivery is not runtime
acceptance, integrated visual approval, full E2E success or release authorization.

For repository-maintenance handoffs, report implementation delivery and deferred
user validation separately. These are human-facing delivery descriptions, not
new runtime outcomes or exemptions from the generated product contract.
