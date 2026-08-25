---
name: spx-quick
description: Tracked direct-delivery workflow for advanced coding models. Use when non-trivial work of any size needs resumable planning, implementation, and verification without first creating a formal feature specification. After item-start, MUST spawn_subagent before any write_scope file edit; item-accept requires worker result submit (or quick allow-inline).
---

# SPX Quick

## Hard preflight stop

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
Read `references/run-bootstrap.md`.
Read `references/autonomous-blocker-recovery.md` before treating any execution
or validation failure as terminal.
Read `references/human-confirmation.md`, then `references/task-contract.md`.
Read `references/worker-contract.md` only
when delegating. Read `references/consequence-gate.md` when work can affect
lifecycle operations, running objects, concurrent work, destructive behavior,
shared state, downstream consumers, compatibility, security-sensitive behavior,
or multiple plausible product behaviors.
Read `references/ui-quality-gate.md` for any user-visible UI change.

The full `$spx-quick` branch always starts a new run. Record that new run with
`specify-runtime run create`, then execute only through `specify-runtime run
supervise`; do not resume another workflow's run. The explicit user-selected
context-direct branch is the sole exception and creates no run or Quick
workspace.

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

After checkpoint confirmation, every in-progress `Qn` uses this hard order.
Leader owns scope, `STATUS.md`, join, accept—not `write_scope` edits.

1. `quick packet-compile --item Qn`
2. `quick item-start --item Qn` (`requires_worker: true`)
3. **Spawn subagent** for the Qn write scope (required; no Edit/Write first)
4. Wait / join
5. `result submit --command quick --workspace .planning/quick/<id>-<slug> --lane-id Qn --result-json '...'`
6. `quick item-accept --item Qn --evidence '...'` (runtime requires worker result)
7. Only then start the next Q

**Forbidden** between item-start and item-accept: Leader mutation of that item's
`write_scope`. **Illegal excuses:** docs-only, few files, serial order, save
time. **Legal leader-inline only via**
`quick allow-inline --item Qn --reason "spawn_failed: ..."` after real spawn/tool
failure, then accept.

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

Initialize or preserve the unconfirmed intake state, then stage a
`quick-confirmation-v1` contract with
`{{specify-subcmd:specify-runtime quick checkpoint-stage <id> --input-json '<decision+delivery>' --format json}}`
and render the runtime Decision Checkpoint plus Delivery Map from
`references/human-confirmation.md`. For applicable UI work, include
`decision.ui_confirmation` and append its UI proposal. When Quick will adopt a
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
and consume it only when it is handoff-ready, its digests are current, the
resolver's exact `discussion_slug` maps to `source_discussion_slug`,
`source_contract` is bound, resolver-returned `review_digest`,
`state_sha256`, and `recommended_consumer` match, `topic_ownership.owner_slug`
equals the selected slug, it has zero
blocking decisions, and `consumer_eligibility.sp-quick.status: ready`, except
for the legacy size/breadth-only override below. With no semantic
delta, stage inheritance with the handoff `review_digest` and continue without
re-confirmation; show the binding summary plus Delivery Map/Pulse. With a
semantic delta, stage only the changed decision rows and confirm the new digest.
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
confirmed scope with mandatory native-subagent execution. When durable
planning no longer fits compact state, create an absent task-local `PLAN.md`
with `specify-runtime artifact scaffold --kind quick-plan`, query it on resume,
and patch only named sections; never submit or reconstruct the whole plan.
Scale that plan, dependency-aware lanes, and multiple ready batches to the
workload.

After checkpoint confirmation, the first substantive step is the **Hard Q Loop**
above—not Leader implementation. Default shapes:

- non-overlapping ready items → `parallel-subagents`;
- one lane, dependent Q items, or **shared/overlapping write scopes** →
  `one-subagent` serial;
- native dispatch unavailable → `quick allow-inline --reason "spawn_failed: ..."`
  only after real attempts (never docs-only).

A narrow single-file or docs-only change does **not** waive subagent-first.
Runtime refuses `item-accept` without a matching `result submit` (or prior
`allow-inline`). Close refuses items missing `execution_mode` worker/inline
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
`specify-runtime artifact patch`. Run
`specify-runtime design resolve --scope <exact-surface> --format json` and query
`.specify/design/index.json` through `specify-runtime artifact show` only for
detail. Resolution is discovery only. Each Quick `STATUS.md` has one singular
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

Patch `STATUS.md` at meaningful transitions through leased `specify-runtime artifact patch` calls. Create an absent `SUMMARY.md` with `artifact scaffold --kind quick-summary`, query it on resume, and patch only its named terminal sections through fresh leases; never submit or reconstruct the whole summary.

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
