## Project Cognition Advisory Gate

This planning-only command should treat the project cognition runtime as an
advisory navigation index, not a mandatory pre-source gate.

Reuse one cognition context capsule only while its exact task/query, workflow
intent/binding, target project, scope, required facets, negative constraints,
permissions, relevant live-source/evidence digests, and runtime identity remain
unchanged. Keep the original `expansion_ref.id`, `query_fingerprint`,
`active_generation_id`, `navigation_digest`, and contract versions with it;
claim revisions are covered by that navigation snapshot, including same-generation
changes. Before reusing a prior capsule for an unchanged phase pass, perform one
actual read-only `{{specify-subcmd:specify-runtime cognition expand --id <id> --section <section> --format json}}`
using that ID and an available section such as `related_paths`. Require the
inner cognition payload's `status=ok`, usable `readiness=query_ready|review`,
`expansion_contract_version=2`, matching
ID, query fingerprint, active generation, and the advisory `epistemic_contract`.
A native outer exit code 0 alone is not proof. Missing, stale, incompatible,
invalid, or unsuccessful expansion disables reuse; follow its recovery action
and refresh supported intake or use live evidence within the workflow boundary.

A verified capsule does not restart Compass or Learning after each preparatory
capability/API, artifact query, script dry run, or board call. These calls alone
also do not require another Expand check. Refresh on target, task/query, intent,
scope/facet, constraint, permission, runtime, relevant source/evidence, generation,
status, or claim-revision drift, contradictory evidence, and required resume or
recovery gates. Preserve live verification and mutation-closeout freshness.
Learning reuse separately requires unchanged applicable lessons, Learning
index/source evidence, and project rules; a graph digest does not prove Learning
unchanged. If relevant lessons/rules drift or their applicability cannot be
confirmed, repeat the owning read-only Learning start/list/show intake.

Before using snapshot reuse, claim-evidence paging, or catalog continuation,
require their respective capability IDs: `cognition.expansion.snapshot.v2`,
`cognition.claim-evidence.page.v1`, and `cognition.catalog.snapshot.v1`. Verify
only the needed set once with
`{{specify-subcmd:specify-runtime api ensure --capabilities <comma-separated-capability-ids> --format json}}`;
reuse its proof while runtime identity is unchanged. Older runtimes may fall back
once to `api list`. Missing capability disables the affected route; use supported
fresh Compass/live evidence instead of assuming newer contracts. These IDs are
capabilities, not CLI commands.

### Facet Coverage and Bound Continuation

`query` is an exact binding consumer, not a natural-language search endpoint.
Never submit only `--query`, `raw_query`, `normalized_query`, or rewritten search
words. Inspect catalog semantic cards and bind exact current `concept_id` values
in `selected_concepts` with the same `lexicon_generation_id`, or exact paths.
Stop catalog paging only when every required facet has a valid binding and live
evidence: owners, necessary consumers/dependencies, verification routes, and
negative constraints, with ambiguity/conflicts resolved and `missing_facets`
empty. The first word match or one bound owner is insufficient. Otherwise,
while `catalog_page.has_more=true`, execute `catalog_page.next_argv` exactly;
keep its `revision`, `navigation_digest`, and `snapshot_bound` proof and the
`offset`, `limit`, `returned`, and `total` accounting. The project launcher may
replace only argv's executable; do not reconstruct `--offset`, `--catalog-revision`,
query, intent, or other continuation flags. A stale catalog/expansion requires
fresh intake rather than combining pages from different snapshots. Do not
claim no match or complete coverage until the relevant pages are exhausted;
preserve unresolved terminology, missing facets, and index gaps as
`insufficient_index`. `resolution_state=resolved_exact` proves binding only;
`binding_required`, `invalid_binding`, and `stale_binding` require repair.

For required claim details, use the selected expansion's `claim_evidence`
section. Preserve `total_count`, `returned_count`, `offset`, and `has_more`,
including exact zero counts; follow its `next_argv` exactly while needed.
The full risk summary remains binding even when details are paged; returned
claims are not the whole denominator. Never rebuild continuation flags, infer
absent metadata as zero, or treat paging as live proof or write permission.

### Readiness and Structured Recovery

Readiness values are `query_ready`, `review`, `needs_rebuild`, `blocked`, and
`unsupported_runtime`. Treat `recommended_next_action` as an object. Do not
treat `recommended_next_action` as a string. Read
`recommended_next_action.action_id` for every packet; preserve non-rebuild
actions, which omit `recommended_next_action.workflow_routes`.

- For `query_ready`, read top-level `minimal_live_reads` first, then lane-level
  `first_pass_paths` reasons. For `review`, inspect those live reads and carry
  `coverage_diagnostics` review notes before expanding.
- `needs_rebuild` alone is not a rebuild route: it can accompany the resumable
  `complete_scan_packets` action. Only for `action_id=project_cognition.rebuild`,
  inspect every `rebuild_reasons[]` entry, preserving its stable `code`,
  human-readable `message`, and relevant `evidence`; consume
  `recommended_next_action.workflow_routes.classic.steps` and project those
  canonical names through this integration's invocation syntax. Reserve
  `{{invoke:map-scan}} -> {{invoke:map-build}}` for that structured route;
  never infer a map workflow from readiness or an internal action ID.
- If a non-workflow action includes `recommended_next_action.argv`, execute
  that exact argv through the project-pinned cognition launcher; replace only
  its executable and preserve every runtime argument. The
  `project_cognition.repair_status` action owns deterministic status
  reconstruction after the graph store validates. Never patch graph metadata
  by hand or directly edit, move, remove, archive, or replace cognition storage
  or pending intents; use runtime-owned guarded recovery routes.
- For blocked, missing, or unsupported runtime/baseline state, report the
  returned status and unavailable intake. Continue with bounded live repository
  evidence only when this workflow permits degraded advisory navigation.
  Preserve workflow invocation, authorization, and final-claim boundaries;
  neither recovery advice nor graph claims authorize source changes, enter a
  map workflow, or set workflow `claim_ready=true`.
