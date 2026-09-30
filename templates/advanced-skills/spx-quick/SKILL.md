---
name: spx-quick
description: Tracked direct-delivery workflow for advanced coding models. Use when non-trivial work of any size needs resumable planning, implementation, and verification without first creating a formal feature specification. Select a guarded leader-direct executor for low-risk well-understood items when the runtime advertises it; otherwise delegate. Both normal paths require structured result submission before acceptance.
---

# SPX Quick

## Hard preflight stop

A material-backed Discussion handoff requires full Quick intake and
`references/task-contract.md`; classify it as insufficient for context-direct.
That shortcut cannot bypass complete source reading, requirement mapping, or
source readiness. Unchanged confirmed source meaning needs no extra approval.

The invoking request is not a branch selection, even when it says to make the
change. Before committing to any action, classify context sufficiency. If it is
sufficient, render the evidence summary and exact two-option menu, then stop
and wait for a new user reply. Do not infer consent from the recommendation.
If it is insufficient, state that the full workflow will perform its normal
intake and continue into that intake.
Do not say "I'll change", "I'll fix", or "I'll reproduce" before the selected
branch's gates allow that action.

Before opening any reference or calling any tool, assess only evidence already
present in the active conversation. Context-direct is eligible only when the
request and mutation authority are explicit; the exact owner/current patch
anchors, direct consumers, risk boundary, and verification entry point are all
visible; no material decision is open; and the edit is one bounded coherent
change. Unknown, stale, conflicting, large, cross-cutting, multi-item,
multi-owner, acceptance-heavy, or resumable work is insufficient.

The pre-intake routing result is strict:

- **Insufficient: never show a branch menu.** Enter the full Quick branch and
  perform its normal intake. Do not announce discovery, reproduction, or edits
  before the full branch's own confirmation and execution gates.
- **Sufficient:** show the exact scope, evidence, and fallback trigger, then ask
  exactly **Direct change (Recommended)** or **Continue full sp-quick**.
  Do not paraphrase these labels or add a third option.

After the user's choice, read `references/context-sufficiency-choice.md` only
for a selected context-direct branch. Execute only that branch, defer
`references/project-cognition.md` until exact-path mutation closeout, and do not
consume Project Learning. For the full branch, continue below without asking
again. The remaining skill text owns the full Quick branch.

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/native-subagents.md` when task lanes are delegated.
Read `references/project-cognition.md`, using cognition intent `implement`.
Read `references/execution-bootstrap.md`.
Read `references/autonomous-blocker-recovery.md` before treating any execution
or validation failure as terminal.
Read `references/human-confirmation.md`, then `references/task-contract.md`.
Read `references/worker-contract.md` only
when delegating. Read `references/consequence-gate.md` when work can affect
lifecycle operations, running objects, concurrent work, destructive behavior,
shared state, downstream consumers, compatibility, security-sensitive behavior,
or multiple plausible product behaviors.
Read `references/ui-quality-gate.md` for any user-visible UI change.

The full Quick branch creates or resumes its task workspace in the current
worktree. The explicit user-selected context-direct branch creates no Quick
workspace; both routes announce scope, checkpoint selection, refresh the
overview, and require `specify-runtime execution guard` before source writes.
Checkpoint validation and call `specify-runtime execution complete` only after
fresh passing validation and terminal workflow state.

The runtime-managed `STATUS.md` Test Design input uses
`test_design_gate.decision: not_selected|selected|required` plus a
`projection_binding`. For `selected` or `required`, verify the producer-built
projection before use with
`{{specify-subcmd:specify-runtime test-design projection-verify --projection-ref <project-relative-ref> --expected-sha256 <sha256> --format json}}`,
adding `--feature-dir <feature-dir>` only for feature scope. Consume that
canonical typed pointer-only projection read-only. Never create, patch,
replace, weaken, or copy the Test Design publication, projection, cases, data,
coverage, gaps, or audit. A selected/required gate with no root or a missing,
stale, tampered, or foreign projection routes to the independent
`$spx-test-design` producer and stops. It does not require Plan completion.
First stage the user-owned decision through `quick checkpoint-stage`. Resume
Quick only after Test Design publishes and builds the Quick projection against
the stable project-relative `.planning/quick/<id>/confirmation.json`, never the
mutable `STATUS.md` that will receive `projection_binding`. `not_selected` is
the legal optional path and carries no invented binding.

## Hard Q Loop (do not skip in the full Quick branch)

After checkpoint confirmation, choose the executor, not a weaker acceptance
standard. Query `{{specify-subcmd:specify-runtime api show quick.item-start --format json}}`
once per pinned runtime identity (or reuse its entry in an already loaded API
pack). Require `execution_contract.schema: quick-item-dispatch-v1`,
`flag: --leader-direct`, `selected_mode: leader-direct`, and
`result_submit_required: true` before using direct execution. Missing, unknown,
or conflicting metadata means the existing delegated path; never probe support
by starting an item or inventing a spawn failure. If resuming a recorded
leader-direct item, missing runtime support blocks until its compatible pinned
runtime is restored; never downgrade or redispatch that active item.

Prefer leader-direct only for one bounded, low-risk, already-understood item:
exact ownership and consumers are known, meaningful checks are available,
no unresolved decision remains, and independent implementation is not required.
Use a worker for substantial investigation, high-risk or cross-cutting changes,
required implementation isolation, or unclear consequences. Use parallel workers
only when dependencies, product scopes and shared resources permit it. File count
alone is not a risk assessment. Keep independently required review, Test Design,
UI/source-continuity, RED and final integration gates in either route.

1. Use the registered quick/status artifact CLI to record the chosen executor
   and evidence-backed reason in the existing agent-owned `STATUS.md` execution
   plan. For a direct
   item, descriptive dispatch fields may use `execution_model: adaptive`,
   `dispatch_shape: leader-inline`, `execution_surface: leader-inline`;
   runtime-owned per-item `execution_mode: leader-direct` is authoritative.
   This is ordinary selection, not `blocked_dispatch` or `allow-inline`.
2. Start exactly one ready Q: `quick item-start <id> --item Qn --leader-direct`
   for the negotiated direct route, or omit the flag to require a worker.
   Read the returned packet and matching `work_claim`; the existing execution
   guard is mandatory. `requires_worker: false` alone is not permission.
   Start already compiles and returns the packet, so do not immediately repeat
   `packet-compile` unless a pre-dispatch preview or explicit refresh is needed.
3. Direct: require both response and packet `execution_mode: leader-direct`
   and `requires_worker: false`, then Leader performs only that guarded item.
   Delegated: spawn a worker before its first product write and join its result;
   Leader never edits an active worker scope.
4. Both routes use `result submit --command quick --workspace .planning/quick/<id>-<slug> --lane-id Qn --result-json <inline-json|@path|->`.
   For direct execution include non-empty `validation_results`, all commands
   actually passed, and empty blockers; a prose success claim is insufficient.
5. `quick item-accept <id> --item Qn --evidence '...'`. Only accepted prerequisites
   permit dependent Q items to start. Independent delegated items may run in the
   same safe batch; accepting one item is not permission to skip its siblings.

Resume preserves the selected executor without repeating the direct flag. Never
relabel an in-progress worker, hand-edit execution audit fields, or use
`allow-inline` to waive direct-mode results. If a direct item outgrows its safe
boundary, pause it and reconcile the task/authority; do not silently spawn a
second writer or change executors under an active claim. Genuine dispatch/tool
failure on the delegated route still uses
`quick allow-inline --item Qn --reason "spawn_failed: ..."`; docs-only, few files,
serial order and time-saving are not fallback reasons.

Keep small result payloads inline, send large model-authored JSON through stdin,
and reserve `@path` for an existing runtime-owned or registered project
artifact. Never create a temporary result file merely for transport.

Accept non-trivial direct-delivery work whose outcome can be confirmed at the
Quick Checkpoint. Task size, capability count, architecture, migration,
compatibility, rollout, shared-state impact, and acceptance depth do not limit
Quick eligibility. Diagnose unknown failure mechanisms through an internal
Debug-grade recovery lane; do not route to `$spx-specify` because the
implementation grows. That formal
specification workflow is a separate user-selected path.
For recovery routing, preserve the Quick workspace, current Q lifecycle,
confirmation binding, and failed evidence through their runtime owners. Run a
bounded Debug-grade diagnostic lane inside Quick; do not invoke `$spx-debug` or
another user-invoked workflow automatically. Resume the blocked Q item or
verification point in the same invocation after the repair is verified.
Quick can handle larger tasks through deeper task-local planning, multiple
batches, explicit joins, and acceptance coverage, including multi-capability
work.
Record every consequence obligation in `STATUS.md` or referenced task-local
`PLAN.md` with affected objects, recovery, verification, and stop conditions.
Broad consequences increase planning, batching, and evidence depth inside
Quick; do not shrink the request or hand it to `$spx-specify`.

Query `.specify/memory/constitution.md` through `specify-runtime artifact show` as governance. Consume project rules and
task-relevant Learning only through the project-learning CLI intake.

Create new state deterministically with
`{{specify-subcmd:specify-runtime artifact scaffold --kind quick-status --path ".planning/quick/<id>-<slug>/STATUS.md" --vars "<compact-json>"}}`
and fill only the returned semantic anchors. Resume an existing
`.planning/quick/<id>-<slug>/STATUS.md` instead of replacing it. Use the project launcher-backed
`{{specify-subcmd:specify-runtime quick list}}`, `{{specify-subcmd:specify-runtime quick status <id>}}`, and
`{{specify-subcmd:specify-runtime quick resume <id>}}` helpers for deterministic discovery.
Keep state compact and ask the user only for decisions the repository cannot
supply.

For full-branch coordination, use
`{{specify-subcmd:specify-runtime execution overview --format json}}` as the
primary global view. Its `execution-overview-v1` snapshot joins Fast, Debug,
Implement, and Quick task, Work/Activity, and scope state. The older
`{{specify-subcmd:specify-runtime quick preflight [<quick-id>] --format json}}`
remains a compatibility view for Quick-specific fields and signals, not the
global concurrency authority. An empty Work Board does not mean no other task
is in progress. In that compatibility view, `write_overlap` is a hard blocker;
an `unfinished_quick_untracked`, `unfinished_quick_scope_overlap`,
`other_unfinished_quick`, or `board_only_work` signal is advisory. Compare
title, current focus, next action, and planned scope, then
resume/merge/sequence related work or proceed with unrelated work without
inventing a user gate.
`same_quick_active_owner` is a hard blocker. A shared `quick:<id>` task ref is
not proof of process identity; bind the exact live Work identity or wait for or
recover the recorded owner.

Refresh the unified overview at entry or resume, before the first `quick item-start`, after
each join before the next Q item or batch, and before execution guard,
interrupted-work recovery, or material scope expansion. Do not poll between
events. Use Work Board task refs `quick:<id>` for the Quick and
`quick:<id>#Qn` for separately registered Q workers through the exact
`execution announce --task-ref` binding.

Treat `quick item-start` as claim-before-start. It requires the active Work id
and fence from `SPECIFY_WORK_ID` / `SPECIFY_WORK_FENCE`, or explicit
`--current-work-id` / `--current-work-fence`. The inherited identity must match
the execution guard. Before
changing the Q item to `in_progress`, runtime claims its complete normalized
`write_scope` all-or-none and returns `work_claim`; do not dispatch without that
receipt and the matching execution guard. Missing identity, foreign `task_ref`, stale fence, inactive Work, or a
scope conflict leaves Quick state unchanged. By default the Quick-level Work
identity owns the active batch. Workers inherit that Quick-level Work authority
without registering overlapping child scopes. Use `quick:<id>#Qn`
only for an independently guarded Q owner when the Quick-level owner does
not already hold those paths.

Initialize or preserve the unconfirmed intake state, then stage a
`quick-confirmation-v1` contract with
`{{specify-subcmd:specify-runtime quick checkpoint-stage <id> --input-json '<decision+delivery>' --format json}}`
and render the runtime Decision Checkpoint from the returned `views.decision`
in that response instead of immediately re-querying it through
`checkpoint-show`. Use the confirmation response's returned `views.delivery`
for the initial Delivery Map, and reserve
`{{specify-subcmd:specify-runtime quick checkpoint-show <id> --view pulse --format json}}`
for later pulse refreshes. Render the checkpoint from
`references/human-confirmation.md`. Use its human-first heading/bullet view;
for reference/live/source-grounded UI, first perform only the bounded read-only
`source_continuity` intake needed to enumerate surfaces, bind touchpoints to
`business_outcome`/side effects/final state, bind assets and dispositions, and
declare complete coverage surface/interaction/component ID sets that exactly
equal their binding targets before closing `unresolved_gaps`. This preflight authorizes no code edit or construction
plan and never treats a screenshot/HTML artifact as behavioral proof. Then
show Delivery Map only after confirmation, on request, or for inherited state.
For applicable UI work, include `decision.ui_confirmation` and fold its readable
`界面方向` proposal into the same checkpoint. When Quick will adopt a
registered `UD-*` change, stage the exact five-field
`decision.ui_confirmation.design_binding` before confirmation; its `scope` and
four registered binding fields enter `confirmation_digest`. For staged
non-inherited checkpoints, ask once for both decisions and bind with
`{{specify-subcmd:specify-runtime quick checkpoint-confirm <id> --digest <confirmation_digest> --format json}}`.
For staged non-inherited checkpoints, wait for user confirmation before
substantive execution. During execution, prefer
`{{specify-subcmd:specify-runtime quick checkpoint-show <id> --view pulse --format json}}`
over vague waiting text. Keep Delivery Map, waves, subagents, and file splits
agent-owned; they never enter `confirmation_digest`.

When intake names `.specify/discussions/<slug>/handoff-to-specify.json`, or a
discussion slug may be implied, first run
`{{specify-subcmd:specify-runtime discussion resolve --intent sp-quick --json}}`,
appending `--slug <slug>` when an exact slug was supplied.
If multiple candidates are returned, ask for the exact slug; never guess, never
select latest, and never infer an unstated slug from a name, title, topic, or
keyword similarity. Query the resolved contract through `specify-runtime artifact show`
and consume it only when it is handoff v5 and handoff-ready, its review and
`discussion_snapshot_digest` values are current, the
resolver's exact `discussion_slug` maps to `source_discussion_slug`,
`source_contract` is bound, resolver-returned `review_digest`,
`state_sha256`, and `recommended_consumer` match, `topic_ownership.owner_slug`
equals the selected slug, it has zero
blocking decisions, and `consumer_eligibility.sp-quick.status: ready`, except
for the legacy size/breadth-only override below. Require non-empty actors,
scenarios, scope, success criteria, and optimal solution approach, plus every
source material inspected, gap-free, and linked through
`source_evidence.material_id`. With no semantic
delta, stage inheritance with the handoff `review_digest` and continue without
re-confirmation; show the binding summary plus Delivery Map/Pulse. With a
semantic delta, retain the complete resulting decision, stage
`source.kind=delta`, name its exact changed paths in
`source.changed_decision_fields`, render only those fields plus
necessary row context, and confirm the new digest. The display field list does
not enter the digest.
A legacy size-, capability-, architecture-, migration-, acceptance-, or
consequence-breadth-only Quick block is obsolete routing advice: keep the source
immutable, stage a Quick checkpoint bound to its digest, and continue under the
inheritance or delta rules above. Return to discussion for an unconfirmed,
contradictory, or decision-blocked contract.
Honor `$spx-specify` only when the user explicitly selected the formal spec-first
path, not as an automatic upgrade.
After binding a confirmed discussion contract into Quick `STATUS.md`, verify
the five lineage fields `source_discussion_slug`, `source_contract`,
`review_digest`, `state_sha256`, and `recommended_consumer` before running
`{{specify-subcmd:specify-runtime discussion mark-consumed <slug> --feature-dir <quick-workspace>}}`.
The `--feature-dir` spelling is retained for compatibility and accepts the Quick
workspace; do not mark consumption before the binding evidence exists.

Inspect the current diff and cognition-selected paths, then execute the full
confirmed scope with the negotiated executor policy above. When durable
planning no longer fits compact state, create an absent task-local `PLAN.md`
with `specify-runtime artifact scaffold --kind quick-plan`, query it on resume,
and patch only named sections; never submit or reconstruct the whole plan.
Scale that plan, dependency-aware lanes, and multiple ready batches to the
workload.

After checkpoint confirmation, follow the **Hard Q Loop** above. A narrow
single-file or docs-only task may use negotiated leader-direct when its actual
risk and context satisfy that policy, not by fabricating a worker failure.
Unknown or unsupported runtime behavior retains delegated execution. Serial
conflicts require sequencing, not relabelling an active owner. Close requires
a runtime-audited `worker`, `leader-direct`, or genuine `leader-inline` fallback
proof. A behavior change must run and record RED before production edits. If no
reliable automated surface exists, build the smallest viable harness as its own
Quick lane; if blocked, record the blocker rather than a `$spx-specify` handoff.
For a propagating change, record a minimal sweep before editing and prove full
affected-surface or callsite coverage across consumers, generated/mirrored
copies, registrations, and verification entry points; sampling or an unverified
surface leaves the task blocked.

For UI work, run **UI Audit** then the **Quick Design Loop**
(design-before-code): audit issues → analyze current UI / system model →
identify issue → propose before/after against DNA/dials/anti-slop → implement →
visual review. Do not jump straight to code or CSS. Patch design sources,
affected states/viewports, visual acceptance, direction source/signature,
reference intents, real content/image sources, and the structure/visual/runtime
evidence triad into the quick-status artifact via leased
`specify-runtime artifact patch`.

For reconstruction, migration, adaptation, or completion governed by an
existing screenshot/recording, HTML/design export, live source UI, source
code/resources/tests, runnable product, requirements, or business rules, build
a structured `source_continuity` contract before dispatch and stage its
applicable subset as `decision.ui_confirmation.source_continuity` so confirmation binds the
promise. Include `schema: spec-kit-ui-source-continuity-v1`, `applicability`,
`mode`, `reason`, complete `coverage.surface_ids` / `interaction_ids` /
`component_ids` sets with exact binding-target equality, and stable
`authority_refs`. Preserve the digest-bound contract or exact ref in `STATUS.md`, the
task-local `PLAN.md` when needed, and every affected worker packet. Treat the
sources as complementary bounded authorities: discover deep surfaces, alternate
entries, and applicable empty/populated/loading/error/permission/offline/
pending/cancel/repeat/restored states rather than extrapolating from the first
screen. Map each surface with exactly one `preserve`, `adapt`, `replace`,
`merge`, `split`, or `retire` disposition. Record every actionable control in
`action_bindings` with exact `interaction_id`, `source_refs`, `user_promise`,
`business_outcome`, `side_effects`, `final_state`, and `verification`; linked
interaction/scenario rows own event order, feedback, and recovery. Code
presence is not proof.
Carry `asset_bindings` for icons, imagery, fonts, and other identity resources,
using exact `component_id`, `semantic_role`, `source_refs`, `target_strategy`,
`target_ref`, `provenance`, and `fallback`. Enforce
`placeholder_policy: forbid-character-substitution`; Unicode, emoji, ASCII, or
arbitrary glyphs cannot substitute for missing icons or images. Keep unknown
surfaces/actions/outcomes/states/assets and source conflicts in
`unresolved_gaps` strings naming owner, next discovery action, and blocking effect; never
hide an unexplored gap as retirement.

Quick remains the direct-delivery owner. Source depth, migration breadth, and
multi-surface acceptance expand task-local planning, Q items, and evidence;
they do not force `$spx-specify`. Escalate only a genuinely new or unresolved
visual direction to `$spx-design`, then resume the same Quick workspace after
approval. Close only after matched safe scenarios run through source and target
real entrypoints when available and separately prove visual fidelity plus each
promised `business_outcome` and `final_state`. If the source cannot run, use the
strongest remaining authority and explicitly withhold the parity claim.

Before `item-accept` for each applicable Q item, call `specify-runtime evidence
source-continuity-manifest --quick-id <quick-id> --item-id Qn --format json`
to materialize the runtime-owned confirmed denominator, inspect the live tool
inventory, then call `source-continuity-adapter-bridge` with the exact Quick
selectors and manifest. It maps signals through
`source-continuity-adapter-catalog` and owns
inventory, Probe, and Plan. `source-continuity-adapter-probe` and
`source-continuity-adapter-plan` are progressively lower-level fallbacks.
Compile `source-continuity-adapter-execution` from the plan ref/SHA and execute
only its bounded packets, evidence requirements, permissions, and stop
conditions. Register each capture
with provenance `adapter:<adapter_id>`, bind its row and observation to the
returned plan, then submit observations through `specify-runtime evidence
source-continuity-validate --quick-id <quick-id> --item-id Qn --manifest
<manifest-ref> --adapter-plan <adapter-plan-ref> --adapter-execution
<adapter-execution-ref> --input-json '<observed-result-json>'`. Return the exact coverage,
`source_continuity_adapter_plan_ref`/SHA-256 and
`source_continuity_adapter_execution_ref`/SHA-256 and
`source_continuity_lab_report_ref`/SHA-256 in `ui_verification`; Quick
acceptance revalidates them against the current digest-protected confirmation decision.

Derive exact stable path-like surface IDs from confirmed source or registered
metadata, split surfaces, and never send the whole brief or prose as `--scope`. Run
`specify-runtime design resolve --scope <exact-surface> --format json` and query
`.specify/design/index.json` through `specify-runtime artifact show` only for
detail when the index exists or registered metadata identifies it. Missing
registry/coverage is legitimate discovery absence; do not blindly read a missing
index or replace required approved Design with a prose risk note. Required
Design still follows approval, registration, and confirmed adoption gates.
Resolution is discovery only. Each Quick `STATUS.md` has one singular
`ui_design_binding`, so split composite coverage into independently bound Quick
workspaces; do not distribute conflicting parent/successor bindings across
workers in one workspace. Select the registered change whose scope matches the Quick task, and
pin its `design_change_id`, exact `design_change_ref`,
`design_change_sha256`, and sibling `design_contract_ref` into Quick state and
every UI worker contract. Never resolve “latest” and never substitute any
unregistered design document. Also pin the
change's approved visual ref, preview/manifest/handoff SHA-256 values,
immutable handoff ref, and selected `DS-*`/`DH-*` rows. An active Quick task
must not silently adopt a later design approval. Before replacement, run
`specify-runtime design diff <CURRENT-UD-ID> <CANDIDATE-UD-ID> --format json`
and then
`specify-runtime design impact quick:<quick-id> --change <CANDIDATE-UD-ID> --scope <exact-surface> --mode quick --expected-change <CURRENT-UD-ID|none> --format json`.
Present the impact classes, affected `DS-*`/`DH-*` IDs,
`preserved_bindings`, `invalidated_bindings`, and `reconcile_from`. Adoption
requires a confirmed UI checkpoint amendment with
the complete replacement binding staged as
`decision.ui_confirmation.design_binding`: exact `scope` plus the four
registered binding fields. `quick checkpoint-confirm` must leave
`confirmation.json` in `confirmed` or `inherited` state; runtime owns the STATUS
readiness projection. Only then patch the independent top-level
`## UI Design Binding` / `ui_design_binding` adoption copy. Do not manually
duplicate the confirmed decision copy into the runtime-managed STATUS
projection; it remains in `confirmation.json`. Both copies must match exactly;
hash the exact status bytes, then run
`specify-runtime design adopt quick:<quick-id> --change <UD-ID> --scope <exact-surface> --mode quick --binding-ref <quick-dir>/STATUS.md --binding-sha256 <sha256> --expected-change <CURRENT-UD-ID|none> --format json`.
Do not dispatch or resume UI work until that compare-and-swap receipt succeeds.
Then retire unstarted affected packets, stop in-progress affected packets at a
safe boundary, preserve completed work, create a corrective work item for
completed-work drift, and recapture only affected Review evidence; unaffected
scope and evidence remain valid.
Preserve original visual references and run the
UI gate's real-entrypoint capture/inspect/refine loop. Escalate a new visual
direction to `$spx-design`. Keep multi-surface or acceptance-heavy UI in Quick
and expand its task-local plan, batches, viewport/state matrix, and evidence;
do not shrink the UI outcome.

Record meaningful transition updates in `STATUS.md` only through its artifact owner. For multiple same-checkpoint targets in one artifact, aggregate the delta in memory and prefer one prepared lease plus `specify-runtime artifact patch-batch`; older runtimes fall back to leased `specify-runtime artifact patch` calls. Create an absent `SUMMARY.md` with `artifact scaffold --kind quick-summary`, query it on resume, and batch only its named terminal sections; never submit or reconstruct the whole summary.

**Terminal order is mandatory (do not reverse):**

1. Finish verification (tests/tsc/surface checks) and patch evidence into the quick-status and quick-summary artifacts through leased `specify-runtime artifact patch` calls.
2. When any confirmed `write_scope` or `changed_code_paths` touches project source/runtime/templates/config/tests (not only `.planning/`), run planner-first cognition closeout **before** close:
   `{{specify-subcmd:specify-runtime cognition closeout-plan --workflow sp-quick --scope-dir .planning/quick/<id>-<slug> --scope-mode explicit --intent implement --format json}}`
   plus one explicit `--changed-path` per owned path → fill agent-owned fields → execute `apply_argv`. Shared apply owns update, validation, eligible finalization, and the durable receipt; do not stamp a second receipt. For an update failure only, run mark-dirty and then `quick cognition-closeout` with `--result-state mark-dirty` and reason.
3. Greenfield / `baseline_kind=greenfield_empty` is **not** a skip: shared apply must still produce `no_op`, or dirty fallback must record an explicit reason.
4. Confirm `{{specify-subcmd:specify-runtime quick status <id>}}` shows `cognition_closeout.allowed_close=true` when source-changing.
5. Only then: `{{specify-subcmd:specify-runtime quick close <id> resolved}}` (argv is positional status, not a bare close).
6. Archive later only with `{{specify-subcmd:specify-runtime quick archive <id>}}`.

Apply the receipt-bound finalizer gate in `references/project-cognition.md`
before any clean source-changing close claim. Do not tell the user the workflow
is complete, and do not run `quick close … resolved`, until step 3 succeeds when
cognition is required. `item-accept` and green tests alone are not terminal
truth; only `quick close … resolved` after cognition closeout is terminal truth.
Report changed paths, evidence, residual risk, and
`project_cognition_refresh`. This invocation authorizes only this workflow
stage. Report an explicit user-selected workflow replacement as a terminal
handoff; do not invoke another workflow in this run. Autonomous recovery
routing under
`references/autonomous-blocker-recovery.md` is not a replacement: keep the
recovery inside Quick and return to the recorded failed gate.
