# Low-tier scan worker

Use this contract for one prepared packet with the lowest-cost model capable of
reliable repository reading and structured output.

The packet's `packet_id`, concrete `assigned_paths`,
`pending-results/<packet-id>.json` destination, and prefilled shape are
authoritative.

- Read only `assigned_paths`; do not broaden with repository-wide search.
- Account for every path as `read` or `deep_read`. Never silently omit, sample,
  exclude, or block one; return a non-pass gap instead.
- Extract packet-local evidence, provisional nodes, edges, observations,
  coverage, and optional claims. Separate observation, inference, and unknown.
- When assigned paths are UI-bearing, classify live UI entry points/navigation,
  token/theme/typography owners, reusable components/patterns, responsive and
  state rules, visual/accessibility tests, and design assets. Put supported UI
  role language in node type/title/aliases plus owner, route, and verification
  hints so existing cognition retrieval can find it; do not hide it only in
  opaque attrs.
- Preserve concrete `nodes[].paths`; coverage rows cannot replace path-backed
  nodes. Cross-packet edges may name an external concrete path while at least
  one endpoint remains packet-local.
- Copy the supplied JSON skeleton and write only the designated pending result.
  Return `packet_id`, assigned/read paths, ledger, coverage, evidence, nodes,
  edges, observations, optional claims, confidence, and `acceptance`.
- A pass accounts for every assigned path, has matching evidence, no ledger
  gap, and `acceptance: pass`. Otherwise return the smallest useful retry split.

Product files are read-only. Do not run `scan-accept`, `validate-scan`,
`build-from-scan`, publish the database, or make final architecture judgments.
