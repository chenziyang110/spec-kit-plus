---
description: Use when the requested change is truly trivial, local, low risk, and can be completed without entering the full specify-plan workflow.
workflow_contract:
  when_to_use: The work is genuinely local and low-risk enough to stay on the fast path.
  primary_objective: Consume relevant Learning and Project Cognition, complete the smallest safe low-risk change leader-direct, then run targeted verification and a lightweight review without opening the full planning workflow.
  primary_outputs: A tightly scoped direct change plus a concise report of what changed, what was verified and reviewed, and any remaining risk.
  default_handoff: Hand off an initially ineligible request to /sp-quick before edits; once Fast execution is active, repair agent-owned blockers inside Fast and resume its failed gate.
---

{{spec-kit-include: ../command-partials/fast/shell.md}}

{{spec-kit-include: ../command-partials/common/senior-consequence-analysis-gate.md}}
{{spec-kit-include: ../command-partials/common/run-bootstrap.md}}
{{spec-kit-include: ../command-partials/common/autonomous-blocker-recovery.md}}

## Project Learning Intake

Fast uses consume-only Learning. Run Learning intake before Project Cognition:

```text
{{specify-subcmd:specify-runtime learning start --command fast --format json}}
```

Use `learning list` only to filter or page compact summaries, and execute one
matching card's `show_argv` only when its triggers match the task. Do not parse
Learning storage. Do not capture or promote Learning from `sp-fast`; preserve a
reusable signal in the closeout report so a workflow with an allowed durable
Learning write surface can handle it later.

{{spec-kit-include: ../command-partials/common/learning-layer.md}}

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

[AGENT] `sp-fast` always starts a new run. Record that new run with `specify-runtime run create`, then execute only through `specify-runtime run supervise`; do not resume another workflow's run.

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

If an entry check fails before execution starts, hand the ineligible request to
`/sp-quick`; do not force ordinary product work through Fast. These entry limits
do not cap causally required recovery after an active Fast gate fails.

## Recovery Continuity

When an active Fast change hits a blocker, enter autonomous recovery mode inside
Fast, preserve the evidence already gathered, and continue in the same
invocation. Diagnose unknown causes with Debug-grade evidence discipline and
expand the registered write scope only as far as the causal repair requires;
do not invoke Quick or Debug automatically. Return to the failed verification
after recovery. A newly discovered product decision uses an explicit workflow
handoff, while only a genuine human/external boundary may end `blocked`.

## UI Fast Gate

- A user-visible UI change is fast-eligible only when it is a narrow adjustment
  to an approved existing pattern, introduces no new visual/product decision,
  affects a bounded state, and can be run and visually checked at the real
  entry point.
- No applicable registered design change, a new surface, supplied fidelity
  target, responsive multi-state work, or a shared component/token change
  leaves fast: route a new direction to `/sp-design` and tracked UI of any
  implementation size or acceptance depth to `/sp-quick`.
- Eligible UI fast work still requires a representative visual capture and
  runtime diagnostics plus visual inspection against the governing design/live
  pattern; add a structure snapshot whenever semantics, hierarchy, focus, or
  interaction changes.
- `representative screenshot or platform` output remains a compatibility name
  for the required visual capture; it does not replace runtime or structure
  evidence when those are triggered.
  Code, unit, or style tests alone do not close visible UI behavior.

## Fast Path Consequence Routing

The fast path may continue only when the Senior Consequence Analysis Gate does not trigger, or when it stands down with a recorded stand-down reason. If the gate triggers, upgrade out of `sp-fast` instead of adding planning artifacts to satisfy this gate on the fast path.

- Upgrade to `/sp-quick` immediately whenever the gate triggers. Quick records product, lifecycle, running-state, destructive-operation, shared-state, downstream-consumer, compatibility, security, and multiple-behavior semantics through its checkpoint and task-local planning.
- Stood-down or non-triggered gate → continue in `sp-fast` only after recording the stand-down reason in the fast-path closeout.

## Upgrade Triggers

Upgrade to `/sp-quick` immediately if:
- The Senior Consequence Analysis Gate triggers at any breadth.
- The work expands to more than 3 files.
- The change touches a shared surface such as a router table, registration file, export barrel, template registry, or other coordination point.
- The project cognition runtime or change slice shows the touched area is a change-propagation hotspot, has explicit verification entry points beyond a trivial local check, or carries known unknowns that make safe direct execution unavailable.
- The task stops being obvious and needs research or clarification to proceed safely.
- The task needs multiple subagent lanes, resumable tracking, or a written quick-task summary artifact.
- The request introduces a new workflow, role boundary, or user-visible behavior that needs explicit acceptance criteria.
- The change carries compatibility, migration, rollout, or neighboring-workflow risk.
- The task changes architecture, APIs, long-lived templates, or planning assumptions.
- Before Fast execution starts, a bug request with an unresolved root cause is
  normally better suited to `/sp-debug`. If the uncertainty is discovered by an
  active Fast failure, keep ownership and enter autonomous recovery mode.

Do not bypass `/sp-quick` and require `/sp-specify` because work is large or consequential. `/sp-specify` is a separate formal specification path selected explicitly by the user.

## Process

1. **Scope gate**
   - Confirm the task fits the fast-path constraints above.
   - If the requested product work is ineligible before execution, hand it to
     `/sp-quick`. If only an active blocker expands the causal repair, use
     Recovery Continuity instead of ending Fast.

2. **Consume Project Learning**
   - Run the consume-only Learning intake above before Project Cognition or broad repository reads.
   - Expand only task-relevant cards through their returned `show_argv` and verify them against live repository evidence.
   - Do not capture, review, or promote Learning from this lightweight workflow.

3. **Pass the project cognition gate**
   - **Project cognition gate:** query the active project's runtime before broad
     repository reads.

     Run or emulate:

     ```text
     {{specify-subcmd:specify-runtime cognition compass --intent implement --query="$ARGUMENTS" --format json}}
     ```

     After the default compass packet, run the advanced `lexicon -> semantic_intake -> query` path only when `compass_state`, coverage diagnostics, localization, or live evidence requires explicit concept decisions. In that escalation, use `specify-runtime cognition lexicon --mode catalog` as the alias catalog, write agent-authored `semantic_intake` and `concept_decisions`, then run `specify-runtime cognition query --query-plan "<query_plan_json>"`; include `query_plan`, `semantic_intake`, `concept_decisions`, `covered_facets`, `missing_facets`, `match_sources`, `lexicon_generation_id`, `repository_search_terms`, project-language search terms, and facet coverage; do not search only the raw user words before source search. Include component names, state names, file names, command names, UI labels, and route names from candidates, aliases, matched terms, returned paths, `normalized_query`, and `expanded_queries`; use these project-language search terms before broad repository search. Agent-owned semantic normalization remains mandatory: `agent_normalization` and raw lexicon ranking are bootstrap signals only; if `agent_normalization` is omitted, treat it as `required=false`; use `write_semantic_intake_from_alias_catalog` when needed. Raw lexicon ranking is only a bootstrap; CJK or mixed CJK/ASCII input still requires agent-owned normalization even when positive raw lexical matches exist. The agent still owns translation. Readiness values are `query_ready`, `review`, `needs_rebuild`, `blocked`, and `unsupported_runtime`.

     Use the returned readiness:

     - `query_ready`: read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons.
     - `review`: perform only the returned `minimal_live_reads` before continuing and inspect `coverage_diagnostics`.
     - `needs_rebuild`: route by `recommended_next_action.action_id`, not readiness alone. Preserve resumable actions such as `complete_scan_packets`; only `action_id=project_cognition.rebuild` may consume `rebuild_reasons[]` and `recommended_next_action.workflow_routes.classic.steps` as a rebuild handoff.
     - `blocked`: report the blocking runtime issue and continue with live evidence only where this workflow allows degraded navigation.
     - Use map-scan -> map-build only for first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation path_index rows, missing or invalid alias_index, explicit_rebuild_requested, or baseline_identity_invalid.
     - Pre-work map maintenance may record ordinary uncertain closure, partial/low-confidence facts, known unknowns, and `minimal_live_reads`. Use map-update for ordinary existing-baseline gaps. After a successful existing-baseline maintenance update, follow the receipt-bound `validate-build` then `complete-refresh` sequence defined by map-update, only for incremental freshness finalization. Do not run `complete-refresh` as a rebuild finalizer or invoke it without the matching validation receipt.
     - **CARRY FORWARD**: Use specify-runtime cognition signals to decide whether
       fast-path execution is still safe. Carry the selected capability, minimal reads,
       and verification route into the fast-task state or report.
   - Only after the cognition gate passes may you read the source files to change.

4. **Execute the fast lane**
   - Perform the fast-path change directly.
   - Keep the allowed write scope local and explicit.
   - Before reading any non-obvious path, confirm the resolved path stays inside the repository and is not a credential, secret, private key, or other sensitive file. If path safety is uncertain, stop and ask for a safer explicit path instead of probing broadly.
   - If the task is behavior-changing rather than docs-only, write a failing targeted test or failing repro check before editing production code.
   - The direct execution notes must include that RED gate before production edits.
   - Do not use manual sanity checks as a substitute for red when behavior changes.
   - If no reliable automated test surface exists for the affected behavior,
     add the smallest viable harness as Fast-owned recovery work, register any
     added write scope, and continue instead of hand-waving the verification gap.
   - For bug fixes and regressions, record the current root-cause explanation
     before implementation starts. If the root cause is not yet known, or if
     multiple plausible causes are still in play, enter autonomous recovery
     mode, prove the mechanism, and continue the requested fix instead of
     applying a quick symptom patch or ending at routing advice.
   - Keep the change as small and local as possible.
   - If the Senior Consequence Analysis Gate stands down, record the stand-down reason before continuing in `sp-fast`.
   - Do not add planning artifacts to satisfy this gate on the fast path. If required consequence outputs are needed, upgrade instead of manufacturing durable artifacts in `sp-fast`.

5. **Verify**
   - If playbook command tiers exist, focused is the fast-lane acceptance check.
   - Otherwise run the smallest meaningful local verification for the change.
   - Prefer targeted existing tests or a direct sanity check over broad workflows.

6. **Lightweight Review**
   - The same leader performs one inline Lightweight Review; use no review subagent and no worker packet.
   - Review the complete changed diff and confirm every edit stays inside the declared write scope, preserves unrelated work, and satisfies the requested acceptance.
   - Check the changed behavior surfaces for an obvious regression, missed consumer, security or consequence issue, and confirm the recorded verification actually exercises the change.
   - Repair any in-scope defect, then rerun the affected targeted verification
     and review the resulting diff once more. If a causal repair expands scope,
     register the additional intent, repair it inside Fast, and continue. A new
     unrelated product capability remains a separate `/sp-quick` handoff.
   - This Lightweight Review does not claim the independent system Review contract owned by `sp-review`; Fast produces only bounded self-review and targeted verification evidence.

7. **Report**
   - Summarize what changed, what was verified, and any remaining risk.
   - [AGENT] Keep the fast-path closeout truthful: report the exact verification you ran and any residual risk instead of implying broader validation.
   - Clean closeout keys on `result_state`; not `status=ok`, `update_id`, `last_update_id`, or freshness alone. Do not present `status=ok` alone as proof of cognition freshness or mutation closeout.
   - Include `changed_code_paths` with modified, added, deleted, and renamed paths.
   - Include `changed_behavior_surfaces` for commands, APIs, templates, generated assets, state files, tests, docs, validators, packets, or runtime assumptions affected by the change.
   - Include `verification_evidence` with the exact checks run and the result.
   - The completion claim must be backed by live code, tests, scripts, configuration, or authoritative docs; project cognition can support route selection but cannot be the sole evidence for completion. Continue only when verification is truthfully green and no explicit blocker prevents completion.

## Output Contract

- Keep the outcome to one tightly scoped change set plus the minimum truthful verification and Lightweight Review evidence.
- Report what changed, which code paths were modified/added/deleted/renamed, which behavior surfaces moved, how it was verified and reviewed, what residual risk remains, and the `project_cognition_refresh` outcome when the cognition runtime was affected.

## Guardrails

- No spec.md creation.
- No plan.md creation.
- No tasks.md creation.
- Use leader-direct execution only; create no worker packet and use no implementation or review subagent. If subagent lanes are needed, route to `/sp-quick`.
- Do not add planning artifacts just to satisfy process formality.
- If ordinary product scope grows while working, hand off to `/sp-quick`.
  Causally required blocker repair is not ordinary scope growth; own it through
  Recovery Continuity and resume the Fast gate.
