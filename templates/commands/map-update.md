---
description: Use when a query-backed project cognition baseline already exists and diff-based evidence refresh or user-supplied corrections must update it incrementally.
workflow_contract:
  when_to_use: A project cognition baseline exists and repository changes or user supplements must update the runtime without a full rebuild.
  primary_objective: Compute impact closure, refresh affected evidence, update claims and conflicts, and update only the affected SQLite runtime records.
  primary_outputs: '`.specify/project-cognition/status.json`, `.specify/project-cognition/project-cognition.db`, and query/update helper readiness metadata.'
  default_handoff: Return to the blocked workflow once the affected query scope is green or yellow.
---

## Objective

Refresh the existing query-backed project cognition baseline incrementally from diff-driven evidence or explicit user corrections.

## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.

## Process

- Query the current project cognition baseline and determine the affected closure before editing runtime outputs.
- Use the shared semantic intake contract when classifying changed paths or user supplements: build `semantic_intake` from the alias catalog, normalized query, `intent_facets`, `negative_constraints`, and `alias_interpretations`; preserve facet coverage in `concept_decisions` through `covered_facets`, `missing_facets`, and `match_sources`; write `repository_search_terms` derived from project language before source search. Agent-owned semantic normalization is mandatory: raw lexicon ranking and `agent_normalization` are only bootstrap signals, not route decisions. If `agent_normalization.required=true`, every raw candidate is `score=0`, or the prompt is localized, mixed-language, CJK, colloquial, symptom-first, or mixed-language or CJK text, extract embedded project terms and write `semantic_intake` from the alias catalog before selecting or rejecting concepts (raw lexicon ranking is only a bootstrap; action: write_semantic_intake_from_alias_catalog). If `agent_normalization` is omitted, treat it as `required=false`; omission does not make raw lexical ranking authoritative. CJK or mixed CJK/ASCII input still requires agent normalization even when positive raw lexical matches exist because embedded project tokens do not translate the surrounding user language. The agent still owns translation; `agent_normalization` is advisory guidance, not a route decision. Do not search only the raw user words; include component names, state names, file names, command names, UI labels, and route names from candidates, aliases, matched_terms, colloquial_matches, returned paths, `normalized_query`, and `expanded_queries`. Use these project-language search terms before broad repository search. Do not trust top similarity alone when deciding the affected closure.
- Prefer the smallest update that can truthfully restore readiness.
- Treat explicit user corrections and user-supplied scope as first-class routing input; user-supplied scope is authoritative for the touched area unless repository evidence disproves it.
- Dispatch only validated incremental update lanes with bounded affected scope.
- A tiny localized refresh may stay as one bounded lane even when native subagents are available.
- If a safe update lane cannot be packetized or delegated, record `subagent-blocked` with the affected paths and the smallest live-read recovery path; this is a dispatch/runtime blocker, not an excuse to skip the map-update duty.
- Update the affected runtime records that can be proven, and explicitly mark uncertain edges as partial, low-confidence, stale, or known-unknown instead of claiming the update cannot be performed.

## Git Delta Intake

- Start from Git, not memory: collect modified, added, deleted, and renamed paths from the current diff, supplied commit range, or explicit changed-path list.
- Filter changed paths through `.cognitionignore` before querying or patching the runtime. Read root `.cognitionignore` and `.specify/project-cognition/.cognitionignore`; both use gitignore-compatible syntax.
- User-supplied changed paths that match `.cognitionignore` are scope notes, not update targets. Report them as ignored unless a later `!` rule re-includes the path or the user explicitly changes the ignore rule.
- Treat user-supplied changed paths, behavior surfaces, and corrections as authoritative scope hints unless repository evidence contradicts them.
- Query `project-cognition.db` for each changed path before deciding update scope.
- For every changed path, look up current owner, consumers, lifecycle/state surfaces, shared mutable state, destructive-operation edges, generated-surface propagation, verification routes, conflicts, stale claims, and known unknowns.
- Expand the update closure through owners, downstream consumers, state surfaces, workflow artifacts, generated surfaces, and verification routes that project cognition already knows.

Every changed path must be accounted for as one of: updated, provisionally adopted, ignored with reason, partial with `minimal_live_reads`, blocked with recovery condition, or requiring full rebuild for a reserved rebuild reason.

Ignored `.cognitionignore` paths are reported in ignored-path accounting only. `sp-map-update` must not write `.cognitionignore`-excluded paths into update records, known unknowns, `minimal_live_reads`, graph evidence, or route indexes.

## Update-By-Default Rule

- Ordinary uncertainty is not an update failure.
- If the affected closure cannot be fully proven, still update the records that can be proven and record the rest as `partial_refresh`, low-confidence claims, conflicts, stale claims, `known_unknowns`, and `minimal_live_reads`.
- `sp-map-update` must not route to `sp-map-scan -> sp-map-build` merely because the closure is wider than expected, some consumers are ambiguous, or extra live reads are needed.
- Rebuild is reserved for missing baseline, unusable DB/status/schema, explicit rebuild request, or repository architecture replacement so broad that the baseline identity is invalid.

## Existing-Baseline Gap Policy

When a usable active generation exists, existing-baseline ordinary gaps are `sp-map-update`
work and must not route to `{{invoke:map-scan}}`, then `{{invoke:map-build}}` for ordinary path gaps,
path count, unrelated top-level count, core-surface status, weak ownership,
missing `path_index` coverage, or unadoptable-ratio heuristics.

Use `review`, `partial_refresh`, low-confidence claims, conflicts, stale claims,
known unknowns, and `minimal_live_reads` to preserve imperfect but useful
maintenance state.

`{{invoke:map-scan}} -> {{invoke:map-build}}` is allowed after an existing baseline
only for missing or unusable runtime, zero active-generation `path_index` rows,
schema failure, `explicit_rebuild_requested`, or `baseline_identity_invalid`.

## Incremental Rule

- `sp-map-update` is the normal maintenance entrypoint after baseline build.
- It must accept both diff-driven and user-supplement-driven updates.
- It must update the query-backed cognition runtime incrementally.
- It must treat `.specify/project-cognition/status.json` plus `.specify/project-cognition/project-cognition.db` as the runtime truth source for post-update readiness.
- It must not silently escalate to a full rebuild without recording why.
- When changed paths are missing from `path_index`, classify them before escalating: adoptable paths get provisional `path_index` and `alias_index` coverage, uncertain paths return `review` with `minimal_live_reads`, and existing-baseline ordinary gaps stay in `sp-map-update`.
- Provisional adoption must write valid graph records: an adoption `evidence` row, a `path_index` row with `relation="provisional_path"` and graph confidence `weak` or `partial`, and alias rows for the adopted node title, path material, workflow/source terms, and behavior surfaces so future `project-cognition compass` and alias-catalog routing can rediscover the adopted path.
- It must prefer metadata-only or single-slice updates when those are sufficient.
- After recording updates, re-evaluate runtime readiness through the shared freshness contract.
- Before `validate-build` or `complete-refresh`, build a payload or delta session and call:

```text
project-cognition update --payload-file ".specify/project-cognition/updates/<map-update-id>.json" --reason map-update --format json
```

Use the returned `result_state` to decide whether to finalize, report `partial_refresh`, route to rebuild, or report blocked state.

{{spec-kit-include: ../command-partials/common/inline-project-cognition-update.md}}

- After applying update records, run `{{specify-subcmd:project-cognition validate-build --format json}}`.
- If the update helper returns `needs_rebuild`, `sp-map-update` must not call `complete-refresh`; report the concrete first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation `path_index` rows, missing or invalid `alias_index`, `explicit_rebuild_requested`, or `baseline_identity_invalid` condition and route to `{{invoke:map-scan}}`, then `{{invoke:map-build}}`.
- If `validate-build` reports `identity_reconciliation=blocked` but the blocked set is bounded and path-led, `sp-map-update` must run a focused identity-repair pass before offering rebuild. Treat missing or unexpected `coverage_path` identities, renamed paths, deleted paths, ignored paths, stale DB path rows, and path-derived evidence identities as map-update repair work when they can be explained from git delta, file existence, `.cognitionignore`, existing merge records, or explicit row decisions.
- During the identity-repair pass, classify every blocked identity as one of: adopted with provisional path/evidence, merged to a canonical path, rejected with an explicit row decision, ignored by boundary rules, stale/deleted, or still blocked with a concrete reason. Then rerun `{{specify-subcmd:project-cognition validate-build --format json}}`.
- Do not ask the user to choose between focused identity repair and full rebuild when the repair set is bounded and no reserved rebuild reason is present; perform the focused repair first and escalate only if the repair cannot safely explain the identities or validation later reports a reserved rebuild condition.
- If `validate-build` is blocked after update recording, report `partial_refresh` and preserve the validation errors instead of claiming the runtime is fresh.
- If the re-evaluated runtime is `fresh` with `readiness=ready`, finalize the successful refresh through `{{specify-subcmd:project-cognition complete-refresh --format json}}` so cognition freshness metadata cannot remain stale.
- If the update helper returns `ready` and `validate-build` passes, but the shared freshness check still sees the same refreshed source paths only because those source changes are not committed yet, report the incremental update as recorded and baseline-finalization pending. Do not tell the user to run `{{invoke:map-scan}}` or `{{invoke:map-build}}` merely because refreshed source changes are not committed yet.
- After those source changes are committed, update the git-baseline freshness metadata with `{{specify-subcmd:project-cognition record-refresh --reason "map-update" --format json}}` or `{{specify-subcmd:project-cognition complete-refresh --format json}}` without rerunning `{{invoke:map-scan}}` or `{{invoke:map-build}}`, unless validation reports `needs_rebuild`, the baseline is unusable, or the affected closure cannot be bounded safely.
- Do not report refresh completion when the runtime remains blocked.
- A recorded refresh is not automatically a ready refresh: `partial_refresh` means update metadata was written but readiness still failed.

## Required Inputs

At minimum, read:

- `.specify/project-cognition/status.json`
- `.specify/project-cognition/project-cognition.db` through the
  `project-cognition` query/update helpers
- changed paths or changed commit range
- user supplement input if provided

Do not read or rewrite raw graph JSON artifacts; they are not runtime truth.

## Output Contract

The canonical outputs for this command are:

- updated `.specify/project-cognition/status.json`
- updated `.specify/project-cognition/project-cognition.db`
- query/update helper readiness metadata
- the post-recording freshness result, including `freshness`, `readiness`, and `recommended_next_action`
- when the post-recording freshness result is ready, a completed cognition refresh finalizer via `{{specify-subcmd:project-cognition complete-refresh --format json}}`

## Guardrails

- Do not silently escalate to a full rebuild without recording why.
- Do not present full rebuild as an equal next option for bounded identity reconciliation debt; run the focused repair pass first.
- Do not refresh unaffected runtime records just because the touched area is ambiguous; record partial or low-confidence closure for the affected records instead.
- Do not invent closure when changed paths or user supplements do not support the update.
- Do not re-read or rewrite raw graph JSON artifacts; use the query/update helpers and the smallest affected runtime records that can truthfully restore readiness.
- Do not split small localized updates into parallel scan-style lanes just because subagents are available.
- If the affected update lane cannot be safely packetized or delegated, record `subagent-blocked` with affected paths and recovery evidence; do not describe ordinary ambiguous closure as impossible to update.
- Do not write `.cognitionignore`-excluded paths into update records, `known_unknowns`, or `minimal_live_reads`; report ignored paths separately so the operator can revise `.cognitionignore` when the exclusion is wrong.

## Escalation Boundary

- Escalate to `sp-map-scan`, then `sp-map-build` only when no query-backed baseline exists, the current baseline is unusable, DB/status/schema validation fails, zero active-generation `path_index` rows exist, the user explicitly requested a rebuild (`explicit_rebuild_requested`), or the repository architecture changed so broadly that the baseline identity is invalid (`baseline_identity_invalid`).
- Do not escalate merely because the affected closure is uncertain; record the uncertainty as partial/low-confidence update data with `known_unknowns` and `minimal_live_reads`.
- Do not escalate merely because `validate-build` reports bounded path identity reconciliation debt; classify and repair those identities inside `sp-map-update` first.
- Record the exact reason for escalation, including the failed baseline, DB, schema, explicit-request, or architecture-replacement fact.

## Update Duties

`sp-map-update` must:

- compute diff impact closure
- refresh affected evidence
- apply updates as a `patch-in-active-generation` operation against the current
  query-backed baseline unless validation proves a rebuild is required
- invalidate stale claims
- detect and repair stale retrieval signals, including obsolete aliases,
  colloquial user phrases, concept routes, and ownership hints
- update or create conflicts
- preserve or revise `selected_concepts` routing evidence when changed paths,
  user supplements, or runtime validation show that prior concept selection
  would now misroute a query
- preserve or revise `rejected_concepts` routing evidence when user corrections
  or repository evidence show that a plausible alias belongs to the wrong
  domain
- update affected runtime records with proven facts, low-confidence claims, conflicts, stale markers, known unknowns, and minimal live reads
- produce an incremental update record
- verify the shared freshness contract after the update record is written
- run the successful-refresh finalizer when that verification proves the runtime ready
