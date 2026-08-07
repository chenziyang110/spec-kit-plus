---
name: spx-quick
description: Tracked direct-delivery workflow for advanced coding models. Use when non-trivial work of any size needs resumable planning, implementation, and verification without first creating a formal feature specification. After item-start, MUST spawn_subagent before any write_scope file edit; item-accept requires worker result submit (or quick allow-inline).
---

# SPX Quick

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/native-subagents.md` when task lanes are delegated.
Read `references/project-cognition.md`, using cognition intent `implement`.
Read `references/run-bootstrap.md`.
Read `references/human-confirmation.md`, then `references/task-contract.md`.
Read `references/worker-contract.md` only
when delegating. Read `references/consequence-gate.md` when work can affect
lifecycle operations, running objects, concurrent work, destructive behavior,
shared state, downstream consumers, compatibility, security-sensitive behavior,
or multiple plausible product behaviors.
Read `references/ui-quality-gate.md` for any user-visible UI change.

`$spx-quick` always starts a new run. Record that new run with `specify-runtime run create`, then execute only through `specify-runtime run supervise`; do not resume another workflow's run.

## Hard Q Loop (do not skip)

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
Quick eligibility. Route unknown failure mechanisms to `$spx-debug`; do not
route to `$spx-specify` because the implementation grows. That formal
specification workflow is a separate user-selected path.
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
`decision.ui_confirmation` and append its UI proposal. For staged non-inherited
checkpoints, ask once for both decisions and bind with
`{{specify-subcmd:specify-runtime quick checkpoint-confirm <id> --digest <confirmation_digest> --format json}}`.
For staged non-inherited checkpoints, wait for user confirmation before
substantive execution. During execution, prefer
`{{specify-subcmd:specify-runtime quick checkpoint-show <id> --view pulse --format json}}`
over vague waiting text. Keep Delivery Map, waves, subagents, and file splits
agent-owned; they never enter `confirmation_digest`.

When intake names `.specify/discussions/<slug>/handoff-to-specify.json`, query it through `specify-runtime artifact show` and consume
it only when it is handoff-ready, its digests are current, it has zero blocking
decisions, and `consumer_eligibility.sp-quick.status: ready`, except for the
legacy size/breadth-only override below. With no semantic
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
After binding a confirmed discussion contract and its `review_digest` into the
Quick `STATUS.md`, run
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
`specify-runtime artifact patch`. When an approved design system is the basis,
patch its approved visual ref, preview/manifest/handoff SHA-256 values,
immutable handoff ref, and selected `DS-*`/`DH-*` rows into that same artifact
and every UI worker contract. An active Quick task must not silently adopt a later design approval; adoption requires a confirmed UI checkpoint amendment
with the replacement binding. Preserve original visual references and run the
UI gate's real-entrypoint capture/inspect/refine loop. Escalate a new visual
direction to `$spx-design`. Keep multi-surface or acceptance-heavy UI in Quick
and expand its task-local plan, batches, viewport/state matrix, and evidence;
do not shrink the UI outcome.

Patch `STATUS.md` at meaningful transitions through leased `specify-runtime artifact patch` calls. Create an absent `SUMMARY.md` with `artifact scaffold --kind quick-summary`, query it on resume, and patch only its named terminal sections through fresh leases; never submit or reconstruct the whole summary.

**Terminal order is mandatory (do not reverse):**

1. Finish verification (tests/tsc/surface checks) and patch evidence into the quick-status and quick-summary artifacts through leased `specify-runtime artifact patch` calls.
2. When any confirmed `write_scope` or `changed_code_paths` touches project source/runtime/templates/config/tests (not only `.planning/`), run planner-first cognition closeout **before** close:
   `{{specify-subcmd:specify-runtime cognition closeout-plan --workflow sp-quick --intent implement --format json}}`
   → fill agent-owned fields → execute `update_argv` → for `result_state=ready|no_op` run validate-build then complete-refresh; for incomplete update run mark-dirty with reason.
3. Record the durable receipt (hard gate for `quick close … resolved`):
   `{{specify-subcmd:specify-runtime quick cognition-closeout <id> --result-state ready|no_op|mark-dirty|partial --reason "<text>" --format json}}`.
   Greenfield / `baseline_kind=greenfield_empty` is **not** a skip: use `no_op` or `mark-dirty` with an explicit reason.
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
stage; report any explicit user-selected workflow change as a handoff and do not
invoke another workflow in this run.
