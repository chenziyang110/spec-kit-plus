# Map Scan Packet Ledger Design

Date: 2026-05-25

## Context

`sp-map-scan` already requires bounded packets and structured handoffs, but the
current contract still leaves a gap in large repositories: a subagent can
receive a package that is technically bounded yet still large enough to invite
selective reading, shallow summaries, or silent omission of lower-salience
paths. When that happens, the leader can end up with a plausible scan package
that is not actually complete enough to trust.

The missing piece is not only packet sizing. It is packet-internal state. Each
subagent needs its own hard ledger so the leader can verify what was assigned,
what was read, what remains, and whether the lane failed because of genuine
overflow or because the result quality is too weak to accept.

## Goal

Make scan execution auditable at two levels:

1. the leader partitions the full project-relevant file universe into bounded
   packets
2. each subagent tracks its own internal task ledger and returns a machine-checkable handoff

The result should preserve full coverage intent while preventing large packets
from degrading into summary-only work.

## Non-Goals

- Do not require every file to be deep-read to the same depth.
- Do not reintroduce leader-only broad scan fallback for substantive work.
- Do not make `.cognitionignore` the primary user workflow for normal scan setup.
- Do not merge this into a general-purpose task planning redesign outside map
  scanning.

## Recommended Approach

Use a two-level contract:

1. The leader defines the full candidate universe after ignore filtering and
   assigns paths to packets by module or directory boundary.
2. Each packet carries a subagent-local task ledger that acts like mini
   `tasks.md`: `todo`, `doing`, `done`, `blocked`, `overflow`.
3. The subagent writes a structured result handoff under
   `workbench/worker-results/<packet-id>.json`.
4. The subagent must account for every assigned path and cannot silently narrow
   scope.
5. The leader accepts only handoffs that pass both coverage and quality checks.
6. When a packet fails, the leader repacks only the remaining or low-quality
   subset and redispatches.

This keeps the leader responsible for distribution and final acceptance, while
forcing each subagent to prove completion inside its own packet boundary.

## Packet Model

The packet boundary should be semantic first:

- prefer whole module or whole directory ownership
- split only when a packet is too large for one context window
- if a module must be split, preserve a module summary packet and then split by
  subdirectory, public entrypoint, or dependency cluster rather than arbitrary
  file count

Each input packet under `workbench/scan-packets/<lane-id>.md` should include:

- packet id and owning lane
- assigned paths
- packet-level objective
- packet-local ledger
- allowed reads and forbidden paths
- acceptance checks
- overflow handling rule
- `result_handoff_path` pointing to
  `workbench/worker-results/<packet-id>.json`

Each accepted worker result handoff should repeat `assigned_paths`, include
`paths_read` as a non-empty array of concrete paths, include packet-local
coverage rows, include confidence, and report the acceptance outcome. Boolean
read flags such as `paths_read: true` are not path-level evidence and must fail
acceptance.

The Markdown input packet and JSON result handoff must be bound by packet id:
`workbench/scan-packets/<lane-id>.md` needs a matching
`workbench/worker-results/<lane-id>.json`, and orphan worker results are
invalid.

The packet-local ledger should be mandatory, not advisory. It exists so the
subagent can answer:

- what is still left
- what has been read
- what is blocked
- what overflowed
- what evidence supports completion

## Disposition Alignment

`sampled` and `inventory_only` are not free-form convenience labels. They must
align with the path disposition and criticality already recorded in
`repository-universe.json`.

As a default rule:

- critical entrypoints, shared state, configuration, tests, verification
  surfaces, and generated-surface propagation chains should not pass as
  `sampled` just because a packet is bounded
- those surfaces should be `deep_read` unless the boundary artifact already
  records an explicit accepted gap or an equally explicit lower-depth decision
- `sampled` and `inventory_only` are acceptable only when the disposition and
  criticality together justify them

## Leader Acceptance

The leader should evaluate each packet with two independent gates.

### Coverage gate

Pass only when every assigned path has a declared outcome:

- read and evidenced
- sampled
- inventory_only
- blocked
- excluded
- overflow

If any assigned path is missing from the handoff, the packet fails.

### Quality gate

Pass only when the results are trustworthy enough to merge into the scan
baseline.

Quality fails when:

- conclusions lack path-level evidence
- the subagent reports completion but omits critical entrypoints, shared state,
  tests, or configuration surfaces in its assigned scope
- the packet summary conflicts with its own ledger
- the handoff hides uncertainty instead of marking it

The leader should classify failure as:

- `fail_gap`: some assigned paths still need work
- `fail_quality`: paths were read, but the evidence is too weak or inconsistent
- `fail_contract`: the packet, handoff, or ledger schema is invalid, or the
  packet boundary itself is wrong
- `fail_systemic`: the same class of problem repeats across multiple sibling
  packets or indicates the partitioning strategy itself is wrong
- `pass`: the packet is accepted

When `fail_quality` is returned, the handoff must include a machine-checkable
repack subset. That subset must name at least one of:

- `paths[]`
- `claim_ids[]`
- `coverage_row_ids[]`
- `evidence_ids[]`

The subset is the repair target. A quality failure without a repackable subset
is a contract failure, not a quality failure.

## Redispatch Rule

When a packet fails, the leader should not rerun the whole original packet by
default.

Preferred retry order:

1. `fail_gap`: repack the remaining uncovered, overflowed, or blocked paths
2. `fail_quality`: repack the declared quality subset only
3. `fail_contract`: repair the packet boundary, handoff schema, or ledger
   schema, then regenerate the packet
4. `fail_systemic`: repack the affected packet family or rerun partitioning
   before attempting local retries

This keeps retries bounded and prevents a single large packet failure from
restarting the entire scan wave.

## Validation

The scan runtime should be able to validate these invariants:

- every packet has a packet-local task ledger
- every packet result handoff is read from `workbench/worker-results/*.json`,
  not from the Markdown scan-packet instruction files
- `repository-universe.json` includes a `criticality` object alongside
  `dispositions`
- every assigned path appears in a declared final outcome
- `paths_read` is a non-empty array of concrete paths and agrees with read /
  deep_read coverage rows
- accepted packet results include confidence
- read / deep_read coverage rows reference existing evidence ids, and at least
  one referenced evidence row has `source_path` equal to the covered path
- any non-`pass` packet outcome blocks scan acceptance until it is repacked,
  repaired, or recorded as an explicit unresolved gap
- every sampled or inventory_only outcome agrees with the repository-universe
  disposition and criticality for that path
- packet outcomes distinguish gap, quality failure, and pass
- quality failures include a repackable subset
- the leader can tell whether a retry is about missing coverage or weak evidence
- acceptance cannot succeed from summary-only handoffs
- contract-invalid packets are rejected before local redispatch
- repeated sibling-packet quality failures can escalate to systemic repack

`validate-scan` should fail when a handoff omits ledger state, omits assigned
path accounting, collapses a weak packet into a fake pass, or uses sampled /
inventory_only outcomes outside the recorded disposition and criticality.

## Open Risks

- Very large packets may still need a second decomposition step before they are
  safe for one subagent.
- Different repositories may want module boundaries, directory boundaries, or
  dependency clusters as the primary packet unit.
- The quality gate needs enough structure to catch shallow scans without
  forcing full deep-read uniformity.

## Acceptance Criteria

- A large repository can be partitioned into bounded scan packets without
  silently dropping tracked files.
- Each subagent packet returns a machine-checkable task ledger.
- `sampled` and `inventory_only` only appear when the recorded disposition and
  criticality justify them.
- The leader can distinguish gap failure from quality failure.
- Failed packets can be repacked and redispatched without rerunning the full
  original packet.
- `fail_contract` and `fail_systemic` trigger schema repair or repackaging of
  the affected packet family instead of local patching.
- Subagent outputs that only summarize work cannot pass scan acceptance.
