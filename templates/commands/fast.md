---
description: Use when the requested change is truly trivial, local, low risk, and can be completed without entering the full specify-plan workflow.
workflow_contract:
  when_to_use: The work is genuinely local and low-risk enough to stay on the fast path.
  primary_objective: Complete the smallest safe low-risk change directly and run the smallest meaningful verification without opening the full planning workflow.
  primary_outputs: A tightly scoped direct change plus a concise report of what changed, what was verified, and any remaining risk.
  default_handoff: Upgrade immediately to /sp-quick if scope, coupling, or uncertainty expands.
---

{{spec-kit-include: ../command-partials/fast/shell.md}}

{{spec-kit-include: ../command-partials/common/senior-consequence-analysis-gate.md}}

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

## Detailed References

Read [Reference index](references/INDEX.md) before applying shared semantic contracts.

- [semantic work contract](references/semantic-work-contract.md)

## Execution Mode

{{spec-kit-include: ../command-partials/common/dispatch-mode-gradient.md}}

**This command tier: trivial. Dispatch mode: leader-direct.**

The leader performs the change directly. No subagent dispatch. No task contract needed.


## Scope Gate

Use `sp-fast` only when ALL of:
- ≤3 files touched
- No shared registration surface (router table, export barrel, template registry)
- No protocol/contract boundary crossed
- No dependency changes
- Task is clear in one sentence
- Root cause known (if bug fix)

If any check fails → upgrade to `/sp-quick`.
If scope >10 files or crosses module boundary → upgrade to `/sp-specify`.

## UI Fast Gate

- A user-visible UI change is fast-eligible only when it is a narrow adjustment
  to an approved existing pattern, introduces no new visual/product decision,
  affects a bounded state, and can be run and visually checked at the real
  entry point.
- `DESIGN.md` with `design_system.status: bootstrap`, a new surface, supplied
  fidelity target, responsive multi-state work, or a shared component/token
  change leaves fast: route a new direction to `/sp-design`, bounded tracked UI
  to `/sp-quick`, and feature-level acceptance to `/sp-specify`.
- Eligible UI fast work still requires a representative screenshot or platform
  output plus visual inspection against the governing design/live pattern.
  Code, unit, or style tests alone do not close visible UI behavior.

## Fast Path Consequence Routing

The fast path may continue only when the Senior Consequence Analysis Gate does not trigger, or when it stands down with a recorded stand-down reason. If the gate triggers, upgrade out of `sp-fast` instead of adding planning artifacts to satisfy this gate on the fast path.

- Upgrade to `/sp-quick` immediately if the gate triggers with a bounded consequence model.
- Triggered gate with product, lifecycle, running-state, destructive-operation, shared-state, downstream-consumer, compatibility, security, or multiple-behavior semantics → route to `/sp-specify`.
- Stood-down or non-triggered gate → continue in `sp-fast` only after recording the stand-down reason in the fast-path closeout.

## Upgrade Triggers

Upgrade to `/sp-quick` immediately if:
- The Senior Consequence Analysis Gate triggers and the consequence model is bounded enough for lightweight tracking.
- The work expands to more than 3 files.
- The change touches a shared surface such as a router table, registration file, export barrel, template registry, or other coordination point.
- The project cognition runtime or change slice shows the touched area is a change-propagation hotspot, has explicit verification entry points beyond a trivial local check, or carries known unknowns that make safe direct execution unavailable.
- The task stops being obvious and needs research or clarification to proceed safely.
- The task needs multiple subagent lanes, resumable tracking, or a written quick-task summary artifact.
- The work started as a bug fix, but root-cause analysis is still unresolved, competing causes are still plausible, or the next safe step is diagnostic investigation rather than a truly local repair. In that case, route to `/sp-debug`.

Upgrade to `/sp-specify` immediately if:
- The Senior Consequence Analysis Gate triggers for lifecycle, running-state, shared-state, destructive-operation, downstream consumer impact, broad compatibility handling, security, or multiple plausible behavior choices that need product semantics.
- The request introduces a new workflow, role boundary, or user-visible behavior that needs explicit acceptance criteria.
- The change carries compatibility, migration, rollout, or neighboring-workflow risk.
- The task is no longer a bounded local fix and now changes architecture, APIs, long-lived templates, or planning assumptions.

## Passive Project Learning Layer

Fast path does not load the full passive learning layer.

**This command tier: trivial.** Skip all learning hooks. Do not read constitution, project-rules, or project-learnings. Do not run learning start, signal, review, or capture. Learning Reflex is acknowledged but not executed on the fast path; leave `.specify/memory/learnings/INDEX.md` and any linked detail document untouched unless the task is upgraded out of the fast path.

## Process

1. **Scope gate**
   - Confirm the task fits the fast-path constraints above.
   - If not, stop and redirect to the right workflow instead of forcing the task through `sp-fast`.

2. **Pass the project cognition gate**
   - {{spec-kit-include: ../command-partials/common/context-loading-gradient.md}}
   - **Project cognition gate:** query the active project's runtime before broad
     repository reads.

     Run or emulate:

     ```text
     {{specify-subcmd:project-cognition compass --intent implement --query="$ARGUMENTS" --format json}}
     ```

     After the default compass packet, run the advanced `lexicon -> semantic_intake -> query` path only when `compass_state`, coverage diagnostics, localization, or live evidence requires explicit concept decisions. In that escalation, use `project-cognition lexicon --mode catalog` as the alias catalog, write agent-authored `semantic_intake` and `concept_decisions`, then run `project-cognition query --query-plan "<query_plan_json>"`; include `query_plan`, `semantic_intake`, `concept_decisions`, `covered_facets`, `missing_facets`, `match_sources`, `lexicon_generation_id`, `repository_search_terms`, project-language search terms, and facet coverage; do not search only the raw user words before source search. Include component names, state names, file names, command names, UI labels, and route names from candidates, aliases, matched terms, returned paths, `normalized_query`, and `expanded_queries`; use these project-language search terms before broad repository search. Agent-owned semantic normalization remains mandatory: `agent_normalization` and raw lexicon ranking are bootstrap signals only; if `agent_normalization` is omitted, treat it as `required=false`; use `write_semantic_intake_from_alias_catalog` when needed. Raw lexicon ranking is only a bootstrap; CJK or mixed CJK/ASCII input still requires agent-owned normalization even when positive raw lexical matches exist. The agent still owns translation. Readiness values are `query_ready`, `review`, `needs_rebuild`, `blocked`, and `unsupported_runtime`.

     Use the returned readiness:

     - `query_ready`: read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons.
     - `review`: perform only the returned `minimal_live_reads` before continuing and inspect `coverage_diagnostics`.
     - `blocked`: report the blocking runtime issue and continue with live evidence only where this workflow allows degraded navigation.
     - Use map-scan -> map-build only for first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation path_index rows, missing or invalid alias_index, explicit_rebuild_requested, or baseline_identity_invalid.
     - Pre-work map maintenance may record ordinary uncertain closure, partial/low-confidence facts, known unknowns, and `minimal_live_reads`. Use map-update for ordinary existing-baseline gaps. After a successful existing-baseline maintenance refresh, use `{{specify-subcmd:project-cognition complete-refresh --format json}}` only for incremental freshness finalization; do not run `complete-refresh` as a rebuild finalizer.
     - **CARRY FORWARD**: Use project-cognition signals to decide whether
       fast-path execution is still safe. Carry the selected capability, minimal reads,
       and verification route into the fast-task state or report.
   - Only after the cognition gate passes may you read the source files to change.

3. **Execute the fast lane**
   - Perform the fast-path change directly.
   - Keep the allowed write scope local and explicit.
   - Before reading any non-obvious path, confirm the resolved path stays inside the repository and is not a credential, secret, private key, or other sensitive file. If path safety is uncertain, stop and ask for a safer explicit path instead of probing broadly.
   - If the task is behavior-changing rather than docs-only, write a failing targeted test or failing repro check before editing production code.
   - The direct execution notes must include that RED gate before production edits.
   - Do not use manual sanity checks as a substitute for red when behavior changes.
   - If no reliable automated test surface exists for the affected behavior, stop and redirect to `/sp-quick` or `/sp-specify` instead of hand-waving the verification gap.
   - For bug fixes and regressions, record the current root-cause explanation before implementation starts. If the root cause is not yet known, or if multiple plausible causes are still in play, stop and route to `/sp-debug` instead of applying a quick symptom patch.
   - Keep the change as small and local as possible.
   - If the Senior Consequence Analysis Gate stands down, record the stand-down reason before continuing in `sp-fast`.
   - Do not add planning artifacts to satisfy this gate on the fast path. If required consequence outputs are needed, upgrade instead of manufacturing durable artifacts in `sp-fast`.

4. **Verify**
   - If playbook command tiers exist, focused is the fast-lane acceptance check.
   - Otherwise run the smallest meaningful local verification for the change.
   - Prefer targeted existing tests or a direct sanity check over broad workflows.

5. **Report**
   - Summarize what changed, what was verified, and any remaining risk.
   - [AGENT] Keep the fast-path closeout truthful: report the exact verification you ran and any residual risk instead of implying broader validation.
   - Include `changed_code_paths` with modified, added, deleted, and renamed paths.
   - Include `changed_behavior_surfaces` for commands, APIs, templates, generated assets, state files, tests, docs, validators, packets, or runtime assumptions affected by the change.
   - Include `verification_evidence` with the exact checks run and the result.
   - {{spec-kit-include: ../command-partials/common/inline-project-cognition-update.md}}
   - The completion claim must be backed by live code, tests, scripts, configuration, or authoritative docs; project cognition can support route selection but cannot be the sole evidence for completion. Continue only when verification is truthfully green and no explicit blocker prevents completion.

## Output Contract

- Keep the outcome to one tightly scoped change set plus the minimum truthful verification evidence.
- Report what changed, which code paths were modified/added/deleted/renamed, which behavior surfaces moved, how it was verified, what residual risk remains, and the `project_cognition_refresh` outcome when the cognition runtime was affected.

## Guardrails

- No spec.md creation.
- No plan.md creation.
- No tasks.md creation.
- Use leader-direct execution only; if subagent lanes are needed, route to `/sp-quick`.
- Do not add planning artifacts just to satisfy process formality.
- If the task grows while working, stop and redirect to `/sp-quick`.
