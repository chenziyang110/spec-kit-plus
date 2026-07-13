## Planning Cognition Policy

Use project cognition as advisory navigation, never as sole proof. For an unchanged phase pass, run at most one `project-cognition compass --intent plan` intake when the canonical context capsule lacks a required facet.

Run or emulate:

```text
{{specify-subcmd:project-cognition compass --intent plan --query="$ARGUMENTS" --format json}}
```

- Read and carry `epistemic_contract` in the phase context capsule. Require `graph_role=route_candidate_only`, `fact_source_of_truth=live_repository`, `live_verification_required=true`, `graph_only_claims_allowed=false`, and `unverified_claim_action=withhold`. The contract cannot authorize source changes and cannot prove current behavior.
- Reuse the returned `compass_state`, `minimal_live_reads`, `first_pass_paths`, `coverage_diagnostics`, and `expansion_ref` as the phase context capsule. Read only the minimum live evidence needed for the active claim and let contradictory live evidence override the route candidate.
- `fresh`, `stale`, `possibly_stale`, `needs_update`, and `partial_refresh` are planning advisories. Follow returned `minimal_live_reads` and prove the active claim from live evidence; do not stop solely because the index is stale.
- Rebuild only for an unusable/missing baseline or explicit rebuild condition. Do not turn ordinary planning into map maintenance.
- Artifact-only specification, planning, and task generation do not mark project cognition dirty. A cognition follow-up is required only after actual source/runtime truth changes.
