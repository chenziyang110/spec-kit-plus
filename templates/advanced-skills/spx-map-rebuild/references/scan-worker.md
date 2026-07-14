# Low-tier scan worker

Use this contract for one bounded scan packet. Prefer the lowest-cost model
that can read repository files and return reliable structured data.

The prepared packet supplies `packet_id`, concrete `assigned_paths`, the
`pending-results/<packet-id>.json` submission path, and its required handoff
shape. Treat it as authoritative.

- Read only `assigned_paths`; do not broaden scope with repository-wide search.
- Account for every assigned path as `read` or `deep_read` in a passing
  baseline packet. Never silently omit, sample, exclude, or block one; return
  a non-pass gap instead.
- Extract evidence and the requested provisional nodes, edges, observations,
  and coverage. Separate observed facts, inference, and unknowns.
- Write only the packet's designated `pending-results/<packet-id>.json`.
  Product source, tests, configuration, and documentation are read-only.
- Return exactly: `packet_id`, optional `family_id`, `assigned_paths`,
  `paths_read`, `ledger`, `coverage`, `evidence`, `nodes`, `edges`,
  `observations`, optional `claims`, `confidence`, and `acceptance`. Preserve
  concrete `nodes[].paths`; coverage rows cannot substitute for them.
- Copy the prepared packet's prefilled JSON skeleton and replace its example
  rows. Do not invent field names or collapse nested ledgers into prose.
- For a relationship proved by an assigned file but targeting another packet,
  an edge may name the other endpoint by its concrete repository path. At
  least one endpoint must remain packet-local; do not read the other packet.
- A pass result accounts for every assigned path as read, includes matching
  packet-local evidence, leaves no ledger gap, and uses `acceptance: pass`.
- On insufficient context or ambiguity, return a gap with the smallest useful
  retry split. Do not guess and do not make final architecture judgments.

Do not run `build-from-scan`, publish the database, complete the refresh, or
claim the cognition baseline is valid. Those gates belong to the leader and
the deterministic project-cognition runtime.
