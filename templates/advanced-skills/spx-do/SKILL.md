---
name: spx-do
description: Advanced workflow for explicitly requested project operations with progressive verified-method retrieval, native tools, a resumable DoSession, and evidence-backed method improvements.
---

# Do

This invocation authorizes only this requested operation. Execute the user's
project goal through available process, file, browser, desktop or connector
tools. Go `do` owns session/receipt state and `playbook` owns reusable methods.
Read the applicable sections of `references/operation-contract.md` before
starting, resuming, or finalizing; it owns the detailed evidence contract.

Before method retrieval or session mutation, require the complete installed contract:

`{{specify-subcmd:specify-runtime api ensure --capabilities do.start,do.record,do.validate,do.finish,do.resume,do.show,playbook.find,playbook.show,playbook.update,playbook.validate,do.prepare,do.next,do.complete,playbook.metrics,do.scoped-recovery.v1 --format json}}`

Missing capabilities block DO until the pinned runtime is repaired/upgraded.
Preserve existing sessions and methods; never fall back to Python or authored state.

1. Establish the real entrypoint, requested result, acceptance checks, current
   environment, output scope, and authorized source write scope. Preserve other
   work and existing external-side-effect approvals. Do not create a formal
   feature, Activity, second Work, or retired Run; `do start` binds `do:<id>`.
2. Consume relevant Learning under canonical `do`; read
   `references/project-learning.md` for its runtime policy. Use cognition as
   advisory navigation when needed; read `references/project-cognition.md` for
   its routing contract, and let live source prove current applicability.
   A missing map does not force reconstruction before an ordinary operation.
3. Run `{{specify-subcmd:specify-runtime playbook find --query "$ARGUMENTS" --format json}}`;
   filter by observed operation/target/context and actual parameters. Follow matching `show_argv` and
   only required `expand_argv`. Inspect current prerequisites and referenced
   scripts before applying a pinned revision. Stored commands do not grant
   permission. No match is a normal live-discovery path. Use observed ranking
   only for comparable-history decisions and expand recovery for matching failures.
4. Inspect `{{specify-subcmd:specify-runtime api show do.prepare --format json}}`
   and its schema. Prepare the exact template, parameter values, method binding,
   context, source files, scopes and real leader `agent_id` read-only; send its
   returned `start_input` unchanged to `do start`, which rechecks live conditions.
   Use `adapter_id="__AGENT__"`; same-adapter ambiguity still needs an explicit ID.
   Resume only an explicit session ID through `do show` / `do resume`.
   `do show --active` never licenses selecting the latest ambiguous candidate.
5. Ask `do next <id>` for ready full actions and recording skeletons. Record
   the selected `started_input` before executing; fill `completion_event` and
   every `completion_required` fact from the actual tool call. Submit through
   `do record` with the latest revision and unique request ID. Refresh next
   after each checkpoint; ready entries share a revision. Process observations
   use argv/cwd; other tools use typed native actions/results. Required output
   and independent effect checks still execute; receipts do not attest unseen calls.
6. Repair agent-owned failures within scope. Use the contract's failed or
   unstarted replan branch; carry evidence only when explicit `retain_verified`
   receives runtime-approved receipts. Reconcile interrupted effects and
   complete the source-mutation gate below. Read `do next`'s completion result
   or `do validate`; readiness alone is not terminal.
7. Normally supply `change_summary` with next's `complete_input` to `do complete`
   for validated execution, template/usage publication and final saved knowledge.
   Use the explicit pending/Learning/manual-publication branch when needed;
   use `not_applicable` when no reusable method or usage should be retained.
   Proposals cannot replace verified methods, and unchanged reuse cannot create
   duplicate revisions. Require fresh validation and `data.terminal=true`.
   Pending knowledge resumes without rerunning successful execution. Never
   auto-promote methods or lessons into project rules.

## Source Mutation Closeout

When retained source, scripts, tests, or configuration changed, read
`references/project-cognition.md` and run this registry-owned planner with the
exact session identity and owned source paths:

Use the project root as the native process working directory; the planner does
not accept a `--project-root` flag.

`{{specify-subcmd:specify-runtime cognition closeout-plan --workflow sp-do --scope-dir .specify/do/sessions/<id> --scope-mode explicit --changed-path <owned-source-path> --format json}}`

Repeat `--changed-path` for each owned endpoint, including both sides of a
rename. The session directory is the closeout scope, not a formal feature;
preserve its existing Work binding. Only source deltas enter `changed_paths`,
not declared outputs or method/session metadata. Add `--delta-session` only
when the current operation already has that actual runtime-owned identity.
Fill the planner's agent-owned evidence/disposition fields from current checks,
then execute its structured `apply_argv`; shared apply owns update, validation,
eligible finalization, and the bound receipt. Follow the shared intent inspection,
repair, and exact replay contract on interruption. Clean completion requires
the receipt-bound finalizer to succeed when globally eligible; preserve a
truthful `scope_ready` receipt with unrelated global debt otherwise. Never stamp
a second receipt, construct direct updates, or treat an entry map status as
source closeout. `do validate` must accept the exact session-bound result before
execution can be finished.

For an actual blocked exit read `references/blocker-resolution.md`. State the
session, failed gate, evidence, attempted recovery, next action, unblock condition,
and exact resume point. Do not invoke another workflow automatically. Report
the actual operation, verified output, reused/updated/proposed method and gaps;
methods remain project-local unless explicitly exported or version-managed.
