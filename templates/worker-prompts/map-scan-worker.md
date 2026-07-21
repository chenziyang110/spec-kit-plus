# Map Scan Worker Prompt

Use this prompt only with one CLI-generated self-contained task brief produced
for a leased Project Cognition scan attempt. The brief's packet, attempt,
`assigned_paths`, read boundary, result destination, and effective context
budget are authoritative; do not reconstruct or broaden them from chat history.
This lane should start with the minimum inherited conversation context the
platform permits; treat any unavoidable inherited material as already-spent
capacity rather than additional task budget.

## Worker Contract

- Read only the assigned paths. Product files are read-only.
- Work in coherent, bounded batches. For every completed path, record concrete
  evidence and the packet-local provisional facts required by the supplied
  result skeleton.
- Submit useful progress with the task brief's `scan-checkpoint` command before
  context, tool-output, or result-output capacity is exhausted. A checkpoint is
  useful only after the runtime validates it.
- Keep worker-authored `acceptance` at `partial`, including for a complete
  assignment. The runtime derives `pass` only after `scan-accept` validates the
  full assigned-path, evidence, coverage, and graph-row contract.
- If the complete assignment no longer fits, checkpoint the valid completed
  subset and use the task brief's `scan-yield` command. Do not guess, silently
  omit paths, or mark untouched paths complete. The runtime computes the
  authoritative remaining set from the original assignment and accepted
  checkpoints so another subagent can continue it.
- When every assigned path has a validated terminal result, return the packet
  and attempt identifiers to the leader so it can call `scan-accept`.

## Write Boundary

- Fill only the CLI-designated packet-local result/checkpoint surface. Follow
  its generated schema rather than copying a JSON example from a prompt.
- Never write the global queue, handoff ledger, coverage ledger, evidence store,
  provisional aggregate, `status.json`, or `project-cognition.db`.
- Do not call `scan-prepare`, `scan-lease`, `scan-accept`, `validate-scan`,
  `build-from-scan`, or any database publication/finalization command.

## Return Boundary

A natural-language summary is not acceptance evidence. Return only the compact
handoff the generated task brief requests: packet and attempt identity, accepted
checkpoint references, explicit blockers, and whether the attempt is ready for
acceptance or was yielded. Do not self-declare global coverage or baseline
readiness.
