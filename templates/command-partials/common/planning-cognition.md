## Planning Cognition Policy

Use project cognition as advisory navigation, never as sole proof. For an unchanged phase pass, run at most one `project-cognition compass --intent plan` intake when the canonical context capsule lacks a required facet.

Run or emulate:

```text
{{specify-subcmd:project-cognition compass --intent plan --query="$ARGUMENTS" --format json}}
```

- Read and carry `epistemic_contract` in the phase context capsule. Require `graph_role=route_candidate_only`, `fact_source_of_truth=live_repository`, `live_verification_required=true`, `graph_only_claims_allowed=false`, and `unverified_claim_action=withhold`. The contract cannot authorize source changes and cannot prove current behavior.
- Graph claims are indexed assertions. Even `verified_in_graph_generation` is only an active graph-generation state, not current repository truth; graph claims cannot authorize source changes and cannot set workflow `claim_ready=true`. Use related graph claims to narrow live reads, then prove or reject them from bounded repository evidence.
- Reuse the returned `compass_state`, `minimal_live_reads`, `first_pass_paths`, lane `claim_refs`, `coverage_diagnostics`, and `expansion_ref` as the phase context capsule. Treat `route_confidence` only within `confidence_scope=route_candidate`; use top-level advanced-query `claim_signals` or `project-cognition expand --section claim_evidence` for bounded `source_path`/`span` evidence. These signals require live verification and cannot prove current repository truth. Read only the minimum live evidence needed for the active claim and let contradictory live evidence override the route candidate.
- Interpret `claim_ranking` only as a bounded rerank of candidates already eligible through `match_score`; claims cannot create candidates and cannot replace live verification. Fresh supported or graph-generation-verified claims add at most `+1`, while stale and contradicted claims subtract `-1` and `-2`. On `stale_claim_signal` or `contradicted_claim_signal`, preserve `usable_with_review`, follow `reconcile_claims_with_minimal_live_reads`, and complete the lane action against live repository evidence.
- When claim-specific bounded reads settle a stale or contradicted route, provide only reconciliation intent: workflow, stable `claim_id`, reason, repository-relative `source_path`, bounded line `span`, `supporting` or `contradicting` role, and optional claim-specific verification. Run `project-cognition claim-reconcile prepare --input <intent.json> --format json`; the runtime owns all integrity fields and the prepared packet path. Execute the returned `apply_argv` exactly (`project-cognition claim-reconcile apply --input <prepared_packet_path> --format json`). Generic verification cannot re-promote a graph claim. If reconciliation is ready, rerun Compass once for the planning route; otherwise withhold the claim.
- `fresh`, `stale`, `possibly_stale`, `needs_update`, and `partial_refresh` are planning advisories. Follow returned `minimal_live_reads` and prove the active claim from live evidence; do not stop solely because the index is stale.
- Rebuild only for an unusable/missing baseline or explicit rebuild condition. Do not turn ordinary planning into map maintenance.
- Artifact-only specification, planning, and task generation do not mark project cognition dirty. A cognition follow-up is required only after actual source/runtime truth changes.
- For UI-bearing work, use the same intake to locate likely real entry points,
  token/theme/component owners, reusable patterns, required states, responsive
  behavior, visual/accessibility tests, and design assets. Verify selected paths
  live, then carry only the compact routes needed by downstream task packets.
