{{spec-kit-include: ./cognition-reuse-and-paging.md}}

## Planning Cognition Policy

Use project cognition as advisory navigation, never as sole proof. Reuse a phase
capsule only after the valid-capsule checks in the shared Project Cognition
Advisory Gate: exact task/query, intent, target/scope/facets, constraints,
permissions, live evidence, runtime, and a successful read-only Expand snapshot
check. Preparatory API, artifact, dry-run, and board calls do not repeat intake
or that unchanged check. Missing facets or changed source, generation, status,
claim revision, relevant Learning/rules, or resume/recovery invalidate reuse.
Run at most one `specify-runtime cognition compass --intent plan` intake for
each unchanged phase pass that lacks this valid capsule; repair new invalidation
rather than retaining an outdated at-most-once result.

When needed, run:

```text
{{specify-subcmd:specify-runtime cognition compass --intent plan --query="$ARGUMENTS" --format json}}
```

- Read and carry `epistemic_contract` in the phase context capsule. Require `graph_role=route_candidate_only`, `fact_source_of_truth=live_repository`, `live_verification_required=true`, `graph_only_claims_allowed=false`, and `unverified_claim_action=withhold`. The contract cannot authorize source changes and cannot prove current behavior.
- Graph claims are indexed assertions. Even `verified_in_graph_generation` is only an active graph-generation state, not current repository truth; graph claims cannot authorize source changes and cannot set workflow `claim_ready=true`. Use related graph claims to narrow live reads, then prove or reject them from bounded repository evidence.
- Reuse the returned `compass_state`, `minimal_live_reads`, `first_pass_paths`, lane `claim_refs`, `coverage_diagnostics`, and `expansion_ref` as the phase context capsule. Treat `route_confidence` only within `confidence_scope=route_candidate`; use top-level advanced-query `claim_signals` or `{{specify-subcmd:specify-runtime cognition expand --id <id> --section claim_evidence --format json}}` for bounded `source_path`/`span` evidence, using the current `expansion_ref.id` only when `claim_evidence` is listed in `expansion_ref.available_sections`. These signals require live verification and cannot prove current repository truth. Read only the minimum live evidence needed for the active claim and let contradictory live evidence override the route candidate.
- Interpret `claim_ranking` only as a bounded rerank of candidates already eligible through `match_score`; claims cannot create candidates and cannot replace live verification. Fresh supported or graph-generation-verified claims add at most `+1`, while stale and contradicted claims subtract `-1` and `-2`. On `stale_claim_signal` or `contradicted_claim_signal`, preserve `usable_with_review`, follow `reconcile_claims_with_minimal_live_reads`, and complete the lane action against live repository evidence.
- When claim-specific bounded reads settle a stale or contradicted route, provide only an in-memory reconciliation intent: workflow, stable `claim_id`, reason, repository-relative `source_path`, bounded line `span`, `supporting` or `contradicting` role, and optional claim-specific verification. Run `specify-runtime cognition claim-reconcile prepare --input-json '<intent-json>' --format json`; never create an intent file. The runtime owns all integrity fields and the prepared packet path. Execute the returned `apply_argv` exactly (`specify-runtime cognition claim-reconcile apply --input <prepared_packet_path> --format json`) against that runtime-created file. Generic verification cannot re-promote a graph claim. If reconciliation is ready, rerun Compass once for the planning route; otherwise withhold the claim.
- `fresh`, `stale`, `possibly_stale`, `needs_update`, and `partial_refresh` are planning advisories. Follow returned `minimal_live_reads` and prove the active claim from live evidence; do not stop solely because the index is stale.
- Rebuild only for an unusable/missing baseline or explicit rebuild condition. Do not turn ordinary planning into map maintenance.
- Artifact-only specification, planning, and task generation do not mark project cognition dirty. A cognition follow-up is required only after actual source/runtime truth changes.
- For UI-bearing work, use the same intake to locate likely real entry points,
  token/theme/component owners, reusable patterns, required states, responsive
  behavior, visual/accessibility tests, and design assets. Verify selected paths
  live, then carry only the compact routes needed by downstream task packets.

## Exact Task Scope Availability

After the owning runtime compiles the canonical current task packet, and before
dependent graph consumption, require `specify-runtime api ensure --capabilities
cognition.scope-availability.v2 --format json`, then run `specify-runtime cognition
check --task-packet <exact-project-relative-packet-path> --format json`. Use the
compiler's returned packet path; do not assemble a substitute packet or infer
complete read dependencies from prose. Quick confirmation items declare optional
`read_scope` as an explicit array of exact paths, including required UI contract
and original reference inputs when applicable. Missing legacy `read_scope` is
unknown; explicit `[]` is a complete empty declaration. Null, non-arrays and
non-string paths refuse. Read metadata follows execution `write_scope` digest
exclusion; it never changes registered UI approval or grants worker write scope.

Carry native `availability`, `scope_ready`, `global_status`, `debt_assessments`,
`reasons`, `minimal_live_reads` and `binding` separately. Only an actual version 2
ready result permits scoped advisory graph navigation; proven unrelated debt
remains visible globally. Blocked/degraded/unavailable or unknown proof suspends
dependent graph consumption and uses bounded current live reads, with gaps
explicit. Do not erase blocked results or treat advisory warnings as uniform
protection. Commands without a canonical packet keep the global check and cannot
assert unrelated debt. This route applies with hooks and without hooks on every
CLI and both profiles.

At handoff/resume and before reusing graph context, rerun the same native check
with `--availability-json <previous-native-binding-json>` against the current
canonical packet. Changed source/packet/status/dependency/claim bytes or an old
contract invalidate reuse; repair the owning proof and obtain a new result. Scope
readiness never declares the project globally fresh, grants source write
authority, sets workflow `claim_ready`, or replaces independent Review and human
Accept. Preserve normal packet/Work/UI prerequisite and approval gates.
