# Low-tier scan worker

Use this contract for one leased packet with the lowest-cost model capable of
reliable repository reading and structured output. The CLI-generated
self-contained task brief is authoritative; do not reconstruct it from leader
chat history.

The packet's `packet_id`, concrete `assigned_paths`,
`pending-results/<packet-id>.json` destination, and prefilled shape are
authoritative, together with the attempt identity and effective context budget.

- Read only `assigned_paths`; do not broaden with repository-wide search.
- Work in coherent batches and account concretely for each path you finish as
  `read` or `deep_read`. Never silently omit, sample, exclude, or claim an
  untouched path complete.
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
- Copy the supplied JSON skeleton and write only the designated packet-local
  pending result. Submit coherent completed batches with the `scan-checkpoint`
  command supplied by the task brief before context, tool-output, or
  result-output capacity is exhausted.
- Keep worker-authored `acceptance` at `partial`, even for a complete packet;
  the runtime derives `pass` only after `scan-accept` validates the full result.
- If the full assignment no longer fits, checkpoint the useful completed subset
  and call the `scan-yield` command supplied by the task brief. The runtime
  computes the authoritative remaining set from assigned paths minus accepted
  terminal path results and makes it available to a new subagent; do not invent
  a retry list.
- A natural-language summary is not acceptance evidence. Do not self-declare
  `acceptance: pass`; return packet/attempt identity, checkpoint references,
  explicit blockers, and whether the attempt is ready for leader acceptance or
  was yielded.

Product files are read-only. Do not write global queue, handoff, coverage,
evidence, provisional, or status artifacts. Do not run `scan-accept`. Also do
not run `scan-prepare`, `scan-lease`, `scan-status`, `validate-scan`,
`build-from-scan`, publish/patch SQLite, or make final architecture judgments.
