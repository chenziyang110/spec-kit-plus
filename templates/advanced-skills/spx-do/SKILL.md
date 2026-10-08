---
name: spx-do
description: Advanced workflow for explicitly requested project operations with progressive verified-method retrieval, native tools, a resumable DoSession, and evidence-backed method improvements.
---

# Do

This invocation authorizes only this requested operation. Execute the user's build,
package, test, check, generation, or bounded maintenance goal through native
tools. Go `do` owns session/receipt state and `playbook` owns reusable methods.
Read `references/operation-contract.md` before starting, resuming, or finalizing
an operation; it is the full ownership and evidence contract.

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
   filter by observed operation/target/context. Follow matching `show_argv` and
   only required `expand_argv`. Inspect current prerequisites and referenced
   scripts before applying a pinned revision. Stored commands do not grant
   permission. No match is a normal live-discovery path.
4. Inspect `{{specify-subcmd:specify-runtime api show do.start --format json}}`
   and its schema, then freeze the exact definition, method binding, context,
   source files, output/write scopes, and real leader `agent_id` in `do start`.
   Use `adapter_id="__AGENT__"`; same-adapter ambiguity still needs an explicit ID.
   Resume only an explicit session ID through `do show` / `do resume`.
   `do show --active` never licenses selecting the latest ambiguous candidate.
5. Before native execution record `started`; afterwards record the actual
   completed observation with `do record`, expected revision, idempotency ID,
   tool-call provenance, argv/cwd, outcome, timestamps, and result references.
   Execute the frozen checks against current outputs. A receipt does not attest
   an unobserved command; preserve failures and reconcile interrupted effects.
6. Repair scoped agent-owned failures; when the frozen method must change,
   follow typed resume replanning in the operation contract and verify every
   required step/check again in the new definition epoch. Complete the
   source-mutation gate below, then run `do validate <id>` before finalizing execution
   through `do finish`; a successful command or
   `ready_to_finish` alone is not terminal. Finish execution with knowledge
   `pending`, then use
   `playbook update` with the exact validated definition, completed session, and
   current `base_digest`. Untested changes remain proposals; no-change reuse
   must not create duplicate revisions. After update, reread `do show` for the
   latest session revision and pass the returned `knowledge_receipt` to
   `do finish` as `knowledge` with status `saved`. Never auto-promote into project rules.
7. Retained source/script/configuration changes require canonical `sp-do`
   planner-first cognition closeout and the runtime-bound receipt. Outputs and
   method metadata alone use an explicit no-source-mutation disposition; never
   invent a cognition no-op. Record `saved` only after durable method update;
   use `not_applicable` when no reusable method or usage should be retained.
   Require fresh validation and `data.terminal=true`
   before claiming completion. Pending knowledge resumes without rerunning a
   successful external operation.

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
