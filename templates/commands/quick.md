---
description: Use when a non-trivial task needs tracked direct delivery, scalable task-local planning, validation, or resumable execution without first creating a formal feature specification. After item-start, MUST spawn a subagent before any write_scope file edit; item-accept requires worker result submit (or quick allow-inline).
workflow_contract:
  when_to_use: The requested outcome is clear enough to implement directly and needs more tracking than `sp-fast`; task size, capability count, architecture, migration, compatibility, rollout, and acceptance depth do not disqualify this workflow.
  primary_objective: Keep direct-delivery work resumable while scaling task-local planning, research, decomposition, consequence analysis, and validation to the actual workload.
  primary_outputs: '`.planning/quick/<id>-<slug>/STATUS.md`, quick-task summary artifacts, and the scoped implementation changes for the task.'
  default_handoff: 'Resume the quick task until resolved or concretely blocked. Never require an upgrade to /sp.specify because the task grows; use that formal specification path only when the user explicitly chooses it.'
---

{{spec-kit-include: ../command-partials/quick/shell.md}}

{{spec-kit-include: ../command-partials/common/senior-consequence-analysis-gate.md}}
{{spec-kit-include: ../command-partials/common/run-bootstrap.md}}
{{spec-kit-include: ../command-partials/common/autonomous-blocker-recovery.md}}

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

[AGENT] Apply the Pre-Intake Context Sufficiency Gate first. The full Quick
branch always starts a new run: record it with `specify-runtime run create`,
then execute only through `specify-runtime run supervise`; do not resume another
workflow's run. The explicit user-selected context-direct branch is the sole
exception and creates no run or Quick workspace.

## Read-Only Test Design Projection Gate

The runtime-managed `STATUS.md` Test Design input records
`test_design_gate.decision: not_selected|selected|required` and its
`projection_binding`. `not_selected` is the normal optional path. For
`selected` or `required`, verify the producer-built projection before reading
it:

`{{specify-subcmd:specify-runtime test-design projection-verify --projection-ref <project-relative-ref> --expected-sha256 <sha256> --format json}}`

Add `--feature-dir <feature-dir>` only when the selected projection is feature
scoped; project scope omits it. The projection is a canonical, typed,
pointer-only input. Quick consumes it read-only and must not create, patch,
replace, weaken, or copy the Test Design publication, projection, cases, data,
coverage, gaps, or audit. A selected/required gate with no Test Design root or
a missing, stale, tampered, or foreign projection routes to the independent
`{{invoke:test-design}}` producer and stops. Test Design does not require Plan
completion. First stage the user-owned decision through `quick
checkpoint-stage`; Test Design builds the Quick projection against the stable
project-relative `.planning/quick/<id>/confirmation.json`, never the mutable
`STATUS.md` that will receive `projection_binding`. Resume Quick and bind the
returned refs/digests through the runtime-owned STATUS contract.

## Hard Q Loop (do not skip in the full Quick branch)

After checkpoint confirmation, **every** in-progress `Qn` uses this hard order. Leader owns scope, STATUS, join, accept—not write_scope edits.

1. `specify-runtime quick packet-compile <id> --item Qn`
2. `specify-runtime quick item-start <id> --item Qn` (sets `requires_worker: true`)
3. **Spawn subagent** for the Qn write scope (required; do **not** Edit/Write those paths first)
4. Wait / join the subagent
5. `specify-runtime result submit --command quick --workspace .planning/quick/<id>-<slug> --lane-id Qn --result-json '...'`
6. `specify-runtime quick item-accept <id> --item Qn --evidence '...'` (runtime requires matching worker result)
7. Only then start the next Q

**Forbidden after item-start / before item-accept:** Leader Edit/Write/shell mutation of that item's `write_scope`.

**Illegal leader-inline excuses:** docs-only, few files, serial Q order, save time.

**Legal leader-inline only when:** (a) spawn failed or tool surface missing after real attempts, (b) `specify-runtime quick allow-inline <id> --item Qn --reason "spawn_failed: ..."`, (c) then accept. Soft reasons are refused.

## Workflow dispatch strategy

| Workflow | Subagent policy |
| --- | --- |
| `sp-quick` / `sp-implement` | subagents-first + hard gates (this loop) |
| `sp-debug` | small investigation may leader-inline; multi-lane uses subagents |
| `sp-ask` / `sp-discussion` | leader-inline default (read-heavy) |
| `sp-fast` | leader-inline allowed by design (not quick) |

## Main Flow

The steps below own only the full Quick branch. A user-selected context-direct
branch follows the pre-intake gate, performs the bounded edit and verification,
runs exact-path mutation closeout, and does not enter this flow.

1. Accept non-trivial direct-delivery work of any size whose outcome can be confirmed at the Quick Checkpoint. Scale the quick workspace instead of routing to `{{invoke:specify}}` because work is large, cross-cutting, multi-capability, migration-heavy, or acceptance-heavy; investigate unknown failure mechanisms through Quick's internal evidence-driven recovery lane.
2. Create `.planning/quick/<id>-<slug>/STATUS.md` only with `artifact scaffold --kind quick-status`; resume via `artifact show`, and mutate frontmatter/sections only through leased `artifact patch` calls.
3. Consume eligible discussion handoff or quick-task context without silently changing the confirmed scope. Resolve discussion intake with `specify-runtime discussion resolve --intent sp-quick [--slug <slug>] --format json`; if multiple candidates are returned, stop for an explicit slug and never guess or select latest. Map the resolver's exact `discussion_slug` into `STATUS.md` as `source_discussion_slug`, require `source_contract`, resolver-returned `review_digest`, resolver-returned `state_sha256`, and resolver-returned `recommended_consumer` to match the consumed contract pointer, persist those five fields in `STATUS.md` only through a leased `specify-runtime artifact patch`, and verify the binding before `specify-runtime discussion mark-consumed`. Record consequence coverage, planning depth, any user-owned checkpoint amendment, and the exact `not_selected|selected|required` Test Design gate. Verify a selected/required projection before it shapes any Q item.
4. Use `choose_subagent_dispatch(command_name="quick", snapshot, workload_shape)` and packetized contracts for every substantive Q item. Default `one-subagent` when Q items share write scope or depend serially; `parallel-subagents` only for isolated write sets. Parallel write-conflict is not leader-inline permission.
5. Execute the **Hard Q Loop** for each Q item; patch `STATUS.md` through the artifact CLI at phase transitions; validate changed surfaces.
6. **Before** `quick close … resolved` on source-changing work: run `cognition closeout-plan` with the quick workspace plus explicit owned paths, fill agent fields, and execute its shared `apply_argv`. It owns update, validation, eligible finalization, and the quick-workspace receipt; do not stamp a second receipt. Clean closeout keys on `result_state`; not `status=ok`, `update_id`, `last_update_id`, or freshness alone. Do not present `status=ok` alone as proof of cognition freshness or mutation closeout. Only failed apply uses mark-dirty plus `quick cognition-closeout … --result-state mark-dirty`. Greenfield/empty graph still needs `no_op` or explicit dirty fallback—never skip. Create the quick-summary artifact with `artifact scaffold --kind quick-summary` and patch it (including `project_cognition_refresh`) through leased `specify-runtime artifact patch` calls, confirm `quick status` shows `cognition_closeout.allowed_close=true`, and only then `specify-runtime quick close <id> resolved`. Close also requires every Q to have `execution_mode` worker or audited leader-inline.

For blocker recovery, preserve the Quick workspace, the current Q lifecycle,
confirmation binding, and failed evidence through their runtime owners. Use a
bounded Debug-grade diagnostic lane inside Quick when the failure mechanism is
unknown, or create another Quick recovery item when the cause belongs in
supporting code; do not invoke another user-invoked workflow automatically.
After the repair is independently verified, resume the
blocked Q item or verification point in the same invocation.

## Detailed References

Read [Reference index](references/INDEX.md) before applying detailed contracts.

- [intake and checkpoint](references/intake-and-checkpoint.md)
- [workspace state](references/workspace-state.md)
- [handoff consumption](references/handoff-consumption.md)
- [packetized work](references/packetized-work.md)
- [validation and closeout](references/validation-and-closeout.md)
