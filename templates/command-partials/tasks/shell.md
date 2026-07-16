{{spec-kit-include: ../common/user-input.md}}

## Objective

Compile a ready plan contract into the smallest dependency-safe execution graph that preserves scope, boundaries, obligations, verification, and recovery.

## Context

- Primary authority: `plan-contract.json`; `tasks.md` is the project-facing view and `task-index.json` is canonical for standard/heavy and all UI-bearing work.
- Read conditional plan/spec views only through a required ref or stale condition.
- Task generation is artifact-only and does not authorize source/test edits.

## Process

- If `FEATURE_DIR` is not explicit, run `{{specify-subcmd:lane resolve --command tasks --ensure-worktree}}`; honor a materialized worktree and stop on `uncertain`.
- Validate plan revision, target boundary, complete confirmed scope, interfaces, acceptance, `MP-*`, `CA-###`, capability, fidelity, and stop/reopen refs.
- Reject a target that silently falls back to the current repository when another implementation target was confirmed.
- Select `light`, `standard`, or `heavy`; delegate only isolated decomposition lanes whose benefit exceeds handoff cost.
- Build outcome-oriented tasks, dependency edges, safe parallel batches, and explicit join points. Every join point records validation target, command/check, pass condition, and recovery.
- Run deterministic graph review; repair task-layer defects locally and route upstream truth defects to their owner.

## Tiered Contract

- `leader-direct`: id, objective, dependencies, expected path/discovery scope, acceptance, verification.
- `delegated`: add bounded reads/writes, forbidden drift, authoritative refs, done condition, and recovery.
- `parallel/high-risk`: add exact write isolation, task-relevant obligation/fidelity refs, consumer evidence, join point, and stop/reopen conditions.

Exact delegated packet shape lives in `templates/task-packet-template.json`. `sp-implement` renders and validates only the current packet against live code; do not copy the schema into `tasks.md` or pre-generate all packets.

## Output Contract

- Light non-UI: compact `tasks.md` unless a graph adds real resume value.
- Any UI-bearing work: minimal canonical `task-index.json` plus task-local UI contracts in rendered `tasks.md`.
- Standard/heavy: canonical `task-index.json` plus rendered `tasks.md`.
- Delegated decomposition only: one lane manifest plus lane results.
- Consume every accepted task-generation lane result into a task, edge, batch, join point, guardrail, or explicit blocker/deferral; chat-only lane output is not handoff truth.
- Ready transition: canonical task ref, semantic delta, required refs, blockers/recovery, and exactly one next action.

## Guardrails

- Do not duplicate full upstream contracts, pre-generate every worker packet, or turn task generation into implementation.
- Do not mark a task ready when dependencies, acceptance, required refs, verification, write isolation, or recovery are unresolved.
- Route spec or plan truth defects upstream; repair only task-graph defects locally.
