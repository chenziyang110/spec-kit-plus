---
description: Use when the user explicitly requests a build, package, test, or repeatable project operation and wants applicable project methods reused, current results verified, and useful improvements retained for the next invocation.
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
goal: for example compile the current target, produce a local package, run a
specified test suite, or regenerate a bounded artifact. Read
[the operation contract](references/operation-contract.md) before starting or
resuming the operation. Read [the reference index](references/INDEX.md) only to
locate a triggered contract.

## Guardrails

- The agent's native terminal, process, and observation tools execute the
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
   Narrow operation, target, and observed context when known. Follow a matching
   card's `show_argv`, then only needed `expand_argv`. Compare applicability,
   prerequisites, toolchain, source/configuration evidence, and side effects
   with the live project before choosing a revision.
4. Freeze the exact method definition and scope through `do start`, using
   `{{specify-subcmd:specify-runtime api show do.start --format json}}` and its
   schema contract for structured input. For an explicit existing session use
   `do show <id>` followed by `do resume <id>`. `do show --active` is read-only;
   multiple candidates require an explicit session identity, never latest-file
   selection. Reuse the original method binding unless the runtime accepts a
   newly verified definition.
5. Record each attempt's `started` event before the native operation and its
   `completed` observation afterwards through `do record`. Preserve tool-call
   provenance, exact argv/cwd, outcome, duration, and required result references.
   Execute the frozen checks against current outputs. A process exit alone is
   insufficient when the operation promises a package, report, or other artifact.
6. Run `do validate <id>`; repair bounded agent-owned failures and return to the
   failed check. Preserve failed attempts. Never copy old success receipts,
   fabricate observations, weaken a check, or repeat an uncertain external
   effect merely because an attempt was interrupted.
7. Use `do finish` and the runtime-returned next action to close execution and
   method disposition. Improve a playbook through `playbook update` only from
   a matching completed session and exact validated definition. A new proposal
   without evidence remains a proposal; do not replace a verified current
   method with an untested optimization. If no reusable change is warranted,
   record that explicitly. Read [closeout](references/closeout.md) before final
   completion, source-mutation closeout, or a blocked stop.

## Output Contract

Report the requested result and output paths, current verification evidence,
the exact session and selected method revision, and whether useful knowledge
was saved or was not applicable. For unfinished work, name the blocker, owner,
attempted recovery, and precise resume action. Distinguish verified execution
from an untested method proposal; only claim efficiency gains you measured.

Keep progress concise: goal and selected method, concrete blockage or recovery,
then the final result. Do not narrate every ordinary command or produce a diary
merely to prove that DO ran.
