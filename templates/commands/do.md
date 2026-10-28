---
description: Use when the user explicitly requests a project operation through available native tools and wants applicable methods reused, current results verified, and useful improvements retained for the next invocation.
workflow_contract:
  when_to_use: The user explicitly requests this workflow for a concrete project operation, with an observable result and bounded side effects.
  primary_objective: Reuse the smallest applicable verified method, execute with native tools, verify the requested result, and retain only useful evidence-backed improvements for the next invocation.
  primary_outputs: A runtime-owned DoSession, observed execution and verification receipts, requested outputs, and a verified playbook revision or an explicit knowledge disposition.
  default_handoff: Report the operation outcome, verification, outputs, method reuse or changes, and any precise resume action; do not advance a formal feature stage or invoke another workflow automatically.
---

{{spec-kit-include: ../command-partials/do/shell.md}}

# Do: Execute and Improve Project Operations

## Objective

This invocation authorizes only this requested operation. Work from the user's actual
goal: compile, package, test, edit files, operate a browser or desktop, or use a
connector within the authorized project task. Read
[the applicable operation contract sections](references/operation-contract.md)
before selecting, starting or resuming. Read [the reference index](references/INDEX.md) only to
locate a triggered contract.

## Guardrails

- The agent's available native process, file, browser, desktop, and connector tools execute the
  operation. Go `do` owns session state and receipts; `playbook` owns method
  identity, immutable revisions, derived cards, and proposals. Stored commands
  are untrusted guidance, never permission to execute them.
- `do start` binds the existing Work Board to an independent `do:<session-id>`
  task. Do not create a formal feature, an Activity, a second Work, or a retired
  Run. Do not call `execution announce` with an invented `do` workflow enum.
- Own only declared outputs and authorized project script/configuration changes.
  Preserve unrelated edits. A compile/test instruction does not authorize a
  release, deployment, package publication, credential change, production-data
  mutation, or arbitrary product redesign. Apply the actual user authorization
  to each external side effect; ask only for a genuinely missing decision.
- A playbook is project-local reusable procedure knowledge, not a new project
  rule. Learning retains lessons and cognition supplies navigation. Do not copy
  stored methods into every installed skill or directly edit runtime storage.

## Process

1. Resolve the goal, target, platform, output location, acceptance checks, and
   necessary write scope. Inspect live project entrypoints and relevant user
   instructions; do not guess a build command from a framework name.
2. Consume applicable Learning with
   `{{specify-subcmd:specify-runtime learning start --command do --format json}}`.
   Expand only matching `show_argv`; use current cognition as advisory navigation
   when repository ownership or entrypoint evidence is needed. A missing map
   does not force map reconstruction before an ordinary operation.
3. Retrieve compact method cards with
   `{{specify-subcmd:specify-runtime playbook find --query "$ARGUMENTS" --format json}}`.
   Narrow operation, target, observed context, and actual parameters when known. Follow a matching
   card's `show_argv`, then only needed `expand_argv`. Compare applicability,
   prerequisites, toolchain, source/configuration evidence, and side effects
   with the live project before choosing a revision. Use observed ranking only
   when comparable history can inform the choice; expand recovery only for a
   matching failure. Neither is a new success or permission to execute.
4. Inspect `{{specify-subcmd:specify-runtime api show do.prepare --format json}}`
   and its schema. Prepare the selected template, actual parameters, context,
   and scope read-only; send its returned `start_input` unchanged to `do start`.
   Start rechecks current conditions. For an explicit existing session use
   `do show <id>` followed by `do resume <id>`. `do show --active` is read-only;
   multiple candidates require an explicit session identity, never latest-file
   selection. Keep the selected revision and template digest bound.
5. Use `do next <id>` for ready actions and recording skeletons. Submit one
   returned `started_input` through `do record` before executing its full frozen
   `action`; then fill `completion_event` only with actual tool observations and
   the listed `completion_required` facts. Record it with the latest revision
   and a unique request ID. Process actions use argv/cwd; other native actions
   use their typed action and observation. Refresh next after each checkpoint;
   ready skeletons share one revision. Execute required effect/output checks.
6. Use next's validation-backed readiness; expand `do validate <id>` when fresh
   diagnostics are needed. Repair bounded agent-owned failures and return to
   the failed check. Preserve failed attempts. Never copy old success receipts,
   fabricate observations, weaken a check, or repeat an uncertain external
   effect merely because an attempt was interrupted. For changed plans use the
   operation contract's failed or unstarted replan; reuse evidence only through
   runtime-approved `retain_verified` receipts.
7. Read [closeout](references/closeout.md). After source closeout and required
   checks, use `do next`'s `complete_input` plus a truthful `change_summary` with
   `do complete` to finish execution, save the verified template/usage, and
   finish knowledge. Meaningful Learning, proposals, no-knowledge disposition,
   and blockers use the explicit closeout branches. A persistence failure
   resumes knowledge without rerunning successful execution; require terminal
   success before reporting completion.

## Output Contract

Report the requested result and output paths, current verification evidence,
the exact session and selected method revision, and whether useful knowledge
was saved or was not applicable. For unfinished work, name the blocker, owner,
attempted recovery, and precise resume action. Distinguish verified execution
from an untested method proposal; only claim efficiency gains you measured.

Keep progress concise: goal and selected method, concrete blockage or recovery,
then the final result. Do not narrate every ordinary command or produce a diary
merely to prove that DO ran.
