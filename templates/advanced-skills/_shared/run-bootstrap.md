# Run bootstrap

Run Control owns process-tree launch and resume boundaries for workflow work.
For a new Run whose identity, scope, adapter, and child argv are ready, use
`specify-runtime run launch` as the single call that records the Run and starts
its supervised child. Older runtimes that do not expose `run.launch` fall back
to `specify-runtime run create` followed by `specify-runtime run supervise`.
Use `specify-runtime run show` to confirm an existing active Run identity before
reusing it, then resume that existing Run through `specify-runtime run supervise`.
Launch repository work only through these Run Control entrypoints; they are
control-plane intent only
so the runtime forces child cwd, binds the managed workspace, and seals an
immutable Result. With `--workspace-policy auto`, the runtime may route exactly
one non-overlapping modifying Run to the primary workspace only when its checkout
is pristine; every overlap and every idle-but-dirty launch is isolated. Overlaps
inherit the primary Run's pre-launch Snapshot. Never change cwd or select
another Run's workspace yourself.

Fast, Debug, Implement, and Quick use one global concurrency view. At entry or
resume, before choosing new work versus an existing task, call
`specify-runtime execution overview --format json`; pass the exact current Work
id when one exists. Its `execution-overview-v1` activity rows correlate open
task state, nonterminal Run identity, live or recovery-held Work identity,
planned scope, and confirmed scope. Read `activities` and `signals` instead of
inferring global activity from an empty Work Board or from one workflow's task
list. A `block` signal stops ownership-dependent execution; a `warn` signal
requires bounded recovery or an explicit sequencing decision; an `info` signal
keeps other open work visible without creating a user gate. Refresh at event
boundaries—after a parallel join, before selecting the next task or batch,
before claim, before work scope-add on legacy managed Work,
interrupted-work recovery, or material scope expansion. Use
`--since-revision <last-coordination-revision>` for a compact event-boundary
change feed. Do not poll on a timer. This overview supplies coordination
context; only an execution guard or the managed claim receipt below grants
mutation authority.

For every unhosted Fast, Debug, Implement, or Quick task, create one durable
Activity/Work identity with `specify-runtime execution announce` after choosing
the exact task and before writing source files. Announce the complete candidate file
scope plus applicable semantic resources such as feature, API, UI surface,
schema, configuration, service, port, or external-effect ownership. Record the
`selected` boundary with `specify-runtime execution checkpoint`, refresh
`specify-runtime execution overview`, and pass that response's exact
`coordination_revision` and `snapshot_sha256` to
`specify-runtime execution guard` as `--expected-overview-revision` and
`--expected-overview-sha256`. Guard atomically promotes the complete confirmed
write scope and semantic resource set; any stale snapshot, duplicate task,
file overlap, or semantic resource conflict blocks without a partial claim.
Refresh and guard the whole amended set before expanding scope.

The Activity lifecycle is `announced -> selected -> claimed -> executing ->
validating -> completed`; guard owns the atomic claimed/executing boundary.
Use `specify-runtime execution checkpoint` at meaningful event boundaries and
again with phase `validating` before final verification. After workflow task
state is terminal and fresh passing evidence exists, call
`specify-runtime execution complete`; it derives actual changed paths from the
announced Git baseline, rejects every path outside confirmed scope, stores the
validation/completion digest, and releases file plus semantic ownership in one
transaction. A registered Activity must not use legacy `work claim`, `work
scope-add`, `work checkpoint`, or `work finish` to bypass these gates.

For a host-managed modifying Run backed by a compiled worker task packet, pass
the compile receipt's canonical values unchanged as
`--work-packet-file <receipt.path> --work-packet-sha256 <receipt.sha256>` on
`run launch` or `run supervise`; never pass the path alone. The runtime verifies
the SHA-256 over the file's exact bytes before parsing, then derives task
identity, objective, and confirmed `scope.write_scope` intents, so do not
reconstruct `--work-intents-json` in a prompt or adapter. For non-packet work,
pass exact task identity and planned scope with `--work-agent-id`,
`--work-task-ref`, `--work-summary`, and
`--work-intents-json`. The supervisor
automatically runs `specify-runtime board reconcile` to reconcile stale leases,
registers the Work item before child launch, renews its lease, and owns terminal
closeout. A managed child receives `SPECIFY_WORK_ID` and `SPECIFY_WORK_FENCE`;
do not call `specify-runtime work begin`, `specify-runtime work finish`, or
`specify-runtime work abandon` from that child. If scope grows, first read the
current revision with `specify-runtime work show`, then use
`specify-runtime work scope-add` before touching the new path. Exit nonzero after
`specify-runtime work block` when human or external action is required; the
supervisor retains the blocked scope.

Fast, Debug, Implement, and Quick share one claim-before-write gate. An
unhosted task uses the execution guard above. A managed Run with zero confirmed
write scope is rejected before the Run is claimed or the child starts. Before
source writes, the managed child must either call
`specify-runtime work claim --task-ref <exact-task-ref> --write-scope-json
<complete-json-array> --format json`, or receive the equivalent `work_claim`
receipt from its runtime-owned `implement task-start` / `quick item-start`
boundary. Work id and fence default to `SPECIFY_WORK_ID` and
`SPECIFY_WORK_FENCE`. The claim is all-or-none: missing identity, a foreign
`task_ref`, stale fence, inactive Work, empty scope, or any overlap blocks
without retaining a partial claim. A successful `data.work_claim` receipt is
the authority to begin source mutation; an earlier board scan alone is not.
Only a task/item boundary that explicitly declares no source write may return
`claim_state: not_required`, and that lane must not later report changed files.

Feature bootstrap has a read-only planning boundary. Before any feature write or
branch action, run the exact installed `create-new-feature` script from the repo
root with the original feature description plus `--dry-run --json` (PowerShell:
`-DryRun -Json`). Retain its exact `BRANCH_NAME` as `feature_id` and exact
`FEATURE_DIR` as `feature_dir`; the dry run must not write, create a branch, or
switch branches. Require the dry-run receipt's exact `BOOTSTRAP_CONTRACT` field
to equal `spec-kit-feature-bootstrap-v1`. If it is absent or different, stop
before any Run/Work registration, branch action, or feature write; request the
operator's human-only integration repair action through the trusted project
Specify launcher (`{{specify-subcmd:integration repair}}`), then repeat the dry
run. Every later real script invocation must replay that dry-run
`BRANCH_NAME` unchanged with `--resolved-feature-id <dry-run BRANCH_NAME>`
(PowerShell: `-ResolvedFeatureId <dry-run BRANCH_NAME>`); never recompute its
timestamp or automatic feature number.

For managed feature work, record the dry-run `feature_id` as
`subject_type=feature`, using
`--subject-type feature --subject-id <dry-run BRANCH_NAME>`. Run the real
create-feature script only as the child of `specify-runtime run
supervise`; the supervisor automatically binds the exact feature directory as a
confirmed write intent. A managed child always remains on its allocated
private/current ref, regardless of the returned `feature_branch_policy`; it
must not create or switch to a business feature branch. The exported
`SPECIFY_FEATURE_BRANCH_POLICY` is advisory context and never overrides that
managed-workspace invariant.

For an unhosted feature bootstrap, first run `specify-runtime board reconcile`
and `specify-runtime board show`. Then call exactly one
`specify-runtime board feature-bootstrap --feature-id <dry-run BRANCH_NAME> --feature-dir <dry-run FEATURE_DIR> --summary <summary> --agent-id <agent-id> --adapter-id <adapter-id> --format json`.
That command atomically registers the Work, records the exact
feature directory as a confirmed write intent, and returns `data.work` plus
`data.feature_branch_policy`. Do not query `specify-runtime board branch-policy`
before registration, and do not call `specify-runtime work begin` separately.
Only after that receipt may the caller run the real create-feature script. When
the returned policy is `keep-current`, pass `--keep-current-branch` (PowerShell:
`-KeepCurrentBranch`) and do not create or switch branches. Only when the policy
is `default` because the board was idle does the existing business-branch
behavior remain unchanged.

For any other unhosted modifying workflow, use the execution
announce/checkpoint/overview/guard/complete lifecycle above; its Activity is a
one-to-one authoritative extension of Work, not a second owner. Use
`specify-runtime work block` only to expose an active blocker; Activity phase
and semantic resources follow that Work transition automatically. The board is
a SQLite CLI projection; do not edit it by hand. Legacy non-Activity board
clients retain `specify-runtime work begin`, `specify-runtime work checkpoint`,
`specify-runtime work finish`, and `specify-runtime work abandon`; these are not
completion shortcuts for registered Activities. At process or
computer restart, reconcile and show before deciding what to do. Active
same-task Work may still belong to another agent: do not take it over or resume
it, and you must not interrupt another live agent. Only when the new session has
confirmed that the old owner/session has ended (for example, after a computer
restart), and only after inspecting the board plus its recorded workspace, use
`specify-runtime work interrupt <work-id> --expected-revision <n> --fence <n> --reason <reason> --format json`.
The runtime checks the original workspace, advances the fence, changes the Work
to `interrupted`, and preserves a dirty recovery hold for affected scope. Then
use `specify-runtime work resume` with the returned identity to continue the
preserved task. If prior-owner termination cannot be established, wait rather
than taking over; reconciliation also converts an expired lease to
`interrupted`. After inspecting its recorded workspace and changes, resume it
explicitly or use `specify-runtime work abandon` to release it. If the board
reports a conflict, avoid the overlap by yielding, splitting responsibility, or
narrowing scope. Do not delete unknown edits or unfamiliar changes just because
they appeared during your run.

Inspect Result history with `specify-runtime result list` and
`specify-runtime result show`; record only explicit relationships with
`specify-runtime result depend`, and use `specify-runtime result reopen` rather
than mutating a sealed Result. Delivery is a separate frozen chain:
`specify-runtime candidate build` -> `specify-runtime candidate review` ->
explicit human `specify-runtime accept receipt` ->
`specify-runtime cas publish`. `specify-runtime sync safe` is a separate guarded
primary worktree update. The exact sealed primary Result is accounted state, but
any additional index or worktree change blocks delivery and remains untouched. A Review repair
creates a new Run/Result and therefore a new Candidate; no stage calls direct
integration or mutates an existing Candidate.
