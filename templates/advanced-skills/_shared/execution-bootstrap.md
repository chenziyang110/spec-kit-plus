# Execution bootstrap

Work Board + execution is the normal path for workflow work. Work/Activity is
the sole durable ownership authority: an Activity extends one Work item, not a
second owner or an extra process layer. Execute in the current worktree and
resolve paths there. Do not create isolation branches, move work to another
worktree, or automatically merge or publish. Feature scaffolding alone follows
the explicit branch policy returned by its bootstrap receipt below. Use the
agent's native tooling for bounded subagents or manual long-lived workers.

Fast, Debug, Implement, and Quick use one global concurrency view; other
workflows may inspect that same read-only context. At entry or resume, before choosing new work versus an existing
task, call `specify-runtime execution overview --format json`; pass the exact
current Work id when one exists. Its `execution-overview-v1` activity rows
correlate open task state, live or recovery-held Work identity, planned scope,
and confirmed scope. Read `activities` and `signals` instead of inferring global
activity from an empty Work Board or one workflow's task list. A `block` signal
stops ownership-dependent execution; a `warn` signal requires bounded recovery
or an explicit sequencing decision; an `info` signal keeps other open work
visible without creating a user gate. Refresh at event boundaries: after a
parallel join, before selecting the next task or batch, before guard,
interrupted-work recovery, or material scope expansion. Use
`--since-revision <last-coordination-revision>` for a compact change feed; do not
poll on a timer. This overview supplies coordination context, not task selection
authority or permission to mutate source.

For Fast, Debug, Implement, and Quick only, after choosing the exact task and
before writing source files, create one
durable Activity/Work identity with `specify-runtime execution announce`. For
manual work, supply the exact workflow, agent, adapter, subject, task identity,
objective, complete planned file scope (including workflow-state artifacts
that will change), and applicable semantic resources such
as feature, API, UI surface, schema, configuration, service, port, or external
effect. Discover the current tokenized flags through `api show execution.announce`
when needed; supported workflow values are `fast|debug|implement|quick`.
Do not invent another execution workflow value or a duplicate Work registration.

For a compiled WorkerTaskPacket, pass the compile receipt's canonical values
unchanged to `specify-runtime execution announce --workflow implement
--agent-id <agent-id> --adapter-id <adapter-id>
--work-packet-file <receipt.path> --work-packet-sha256 <receipt.sha256>
--format json`. The runtime verifies the canonical packet path, exact current
compiler output digest over the file's exact bytes before parsing, and immutable
baseline binding, then derives feature/subject id, item/task id, `task_ref`,
objective/summary, and the full `planned_write_scope`. Never pass the path alone
or reconstruct or override those packet-derived fields with manual metadata.
Keep product `write_scope` and `ui_contract` unchanged. The compiler adds
separate `bookkeeping_write_scope` with exactly these feature-local paths:
`task-index.json`, `tasks.md`, `implement-tracker.md`,
`implementation-review/execution-state.json`,
`implementation-review/tasks/<task-id>.json`, and
`worker-results/<task-id>.json`. The hashed packet pins both sets. Announce
derives their union; guard must use the full returned `planned_write_scope`,
not a reconstruction of product paths alone. Bookkeeping remains CLI-owned,
never hand-edited. Shared feature metadata overlaps require serialized
ownership instead of dropping paths or bypassing the board. No wildcard or
broad `.specify` exemption is allowed.
Packet integrity establishes planned scope; it does not grant a write claim.
Packet-backed scope is pinned: guard cannot widen it. If the packet or its scope
changes, recompile and reannounce the new canonical packet through the runtime
owner before dispatch; never amend or hand-edit a pinned packet.

Record the `selected` boundary with `specify-runtime execution checkpoint`,
refresh `specify-runtime execution overview`, and pass that response's exact
`coordination_revision` and `snapshot_sha256` to
`specify-runtime execution guard` as `--expected-overview-revision` and
`--expected-overview-sha256`. Here `snapshot_sha256` is the concurrency-view
digest, not an ambient file capture. Guard atomically confirms the complete
write scope and semantic resource set before source writes or worker dispatch.
The claim is all-or-none: a stale overview, duplicate task, stale fence,
inactive identity, empty write scope, file overlap, or semantic resource
conflict blocks without a partial claim. For manual work, refresh and guard the
whole amended set before expanding scope; packet-backed work must instead
recompile and reannounce its changed packet. An earlier board scan or packet receipt alone
does not authorize mutation.

The Activity lifecycle is `announced -> selected -> claimed -> executing ->
validating -> completed`; guard owns the atomic claimed/executing boundary.
Use `specify-runtime execution checkpoint` at meaningful event boundaries and
again with phase `validating` before final verification. Only after workflow
task state is terminal and fresh passing validation exists, call
`specify-runtime execution complete`. It derives actual changed paths from the
announced Git baseline and audits the product and canonical workflow Git delta.
Declare exact canonical artifact paths as needed before they change; CLI-owned
state is not an audit exemption. Only narrowly identified private runtime cache
bytes, such as `.specify/runtime/receipts` and runtime-owned transaction
metadata, may be excluded by the runtime. Feature, Design, memory, and
`.planning` canonical artifacts stay audited; Work recovery inspections are
unchanged. This does not permit agent-authored files or temporary authoring
payloads. Every audited path outside confirmed scope blocks completion, which
otherwise records the
validation/completion digest, and releases file plus semantic ownership
atomically. Completion does not grant product acceptance or external-mutation
permission. A registered Activity must not bypass guard, checkpoint, or
completion through `work claim`, `work scope-add`, `work checkpoint`, or
`work finish`. A task/item boundary's `work_claim` receipt must agree with the
guarded Work identity and scope before `in_progress`; it cannot replace guard.
Only an explicitly source-read-only boundary may report
`claim_state: not_required`, and it must not later report changed source files.
Pass the exact Work id and fence to delegated task boundaries; inherited
`SPECIFY_WORK_ID` / `SPECIFY_WORK_FENCE` must match that identity.

Feature bootstrap has one read-only planning boundary. Before any feature write
or branch action, run the exact installed `create-new-feature` script from the
repo root with the original description plus `--dry-run --json` (PowerShell:
`-DryRun -Json`). Retain its exact `BRANCH_NAME` as `feature_id` and
`FEATURE_DIR` as `feature_dir`. Require `BOOTSTRAP_CONTRACT` to equal
`spec-kit-feature-bootstrap-v1`; a missing or different contract stops before
Work registration, branch action, or feature writes. Request the operator's
human-only integration repair action through the exact trusted project Specify
launcher command named by the diagnostic, then repeat the dry run.

Next run `specify-runtime board reconcile` and `specify-runtime board show`,
then exactly one
`specify-runtime board feature-bootstrap --feature-id <dry-run BRANCH_NAME> --feature-dir <dry-run FEATURE_DIR> --summary <summary> --agent-id <agent-id> --adapter-id <adapter-id> --format json`.
It atomically registers Work, records the exact feature directory as a
confirmed write intent, and returns `data.work` plus
`data.feature_branch_policy`. Do not query `specify-runtime board branch-policy`
before registration, and do not call `specify-runtime work begin` separately.
Only after that receipt run the real create-feature script, replaying the exact
dry-run `BRANCH_NAME` unchanged with
`--resolved-feature-id <dry-run BRANCH_NAME>` (PowerShell:
`-ResolvedFeatureId <dry-run BRANCH_NAME>`). Do not recompute the timestamp or
automatic feature number. For `keep-current`, pass `--keep-current-branch`
(PowerShell: `-KeepCurrentBranch`) and do not create or switch branches. Only
when the returned policy is `default` because the board was idle does existing
branch behavior remain unchanged. Verify the real `FEATURE_DIR` equals the
dry-run value; an existing feature directory requires explicit resume. The
bootstrap reserves scaffolding scope only; later writes still need the owning
workflow's scoped write boundary, including execution guard for the four
execution workflows. Do not announce a duplicate owner for that reservation.

Other modifying workflows use precise Work Board ownership with
`specify-runtime board reconcile`, `specify-runtime board show`, and
`specify-runtime work begin` before their allowed writes. Claim the complete
write scope with `specify-runtime work claim`; checkpoint the lease through
`specify-runtime work checkpoint` and expand scope with
`specify-runtime work scope-add` before touching new paths. Keep their existing
artifact leases, state owners, verification, and human approval gates. Only
finish Work after fresh validation and the owning workflow's terminal state.
Do not pass Plan, Specify, Review, Accept, map, or other artifact workflows to
`execution announce`; no new Activity workflow enum is introduced.

The board is a SQLite CLI projection; do not edit it by hand. Use
`specify-runtime work block` to expose an active blocker; Activity phase and
semantic resources follow that Work transition. Legacy non-Activity board
clients retain `specify-runtime work begin`, `specify-runtime work checkpoint`,
`specify-runtime work finish`, and `specify-runtime work abandon`; these are
not completion shortcuts for Activities. Reconcile stale leases and show the
board at process or computer restart. Active same-task Work may still belong
to another agent: do not take it over or resume it, and you must not interrupt
another live agent. Only after confirming that the old owner/session has ended
and inspecting its recorded workspace and changes, use
`specify-runtime work interrupt <work-id> --expected-revision <n> --fence <n> --reason <reason> --format json`.
The runtime advances the fence, marks Work `interrupted`, and preserves a dirty
recovery hold. Then use `specify-runtime work resume` with the returned identity,
followed by a fresh overview and the applicable guarded write boundary. An expired lease also
enters conservative interrupted recovery. If termination cannot be established,
wait; if scope conflicts, yield, split responsibility, or narrow scope. Abandon
only explicitly after inspecting preserved changes. Do not delete unknown
edits or unfamiliar changes.

Keep generic `WorkerTaskResult`, result path/submit handoffs, UI
`structure_snapshot`, fresh validation, integrated Review, and the actual human
Accept decision intact. Review repairs stay in the current worktree under a
scoped Work owner and require fresh Review evidence; Acceptance remains
read-only with respect to product source. Branch changes outside the bootstrap,
merges, commits, pushes, publication, and other external mutations retain their
normal explicit authorization gates.

Historical Run records are inert preserved history only: Run no longer selects
tasks, owns scope, or resumes automatically. Historical worktrees remain
preserved, including recorded workspaces needed by Work recovery. Live or
recovery-held Work remains active safety ownership until reconciliation or
explicit resolution; Run retirement never clears those holds. Safe additive
metadata schema evolution is allowed without rewriting history. Retirement must
not delete or rewrite historical records or automatically clean up worktrees,
branches, or edits.
