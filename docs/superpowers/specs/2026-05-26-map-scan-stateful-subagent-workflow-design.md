# Map Scan Stateful Subagent Workflow Design

Date: 2026-05-26
Status: Draft for user review
Owner: Codex

## Summary

Large project cognition scans cannot rely on one subagent acting like it has
unbounded context. When a repository needs a 10,000-unit scan and each subagent
can only hold a 100-unit window, the workflow must make incomplete work
explicit and resumable instead of hoping the subagent will read everything.

This design extends the existing `sp-map-scan -> sp-map-build` packet contract
into a stateful scheduler. The leader owns a durable scan queue, validates each
subagent handoff, updates path-level coverage state, plans the next packet wave,
and repeats until the scan is build-ready or blocked. Subagents receive bounded
packet prompts with explicit context budgets, legal failure exits, and a
machine-readable output schema.

The goal is to prevent the observed failure mode where scan artifacts look
plausible at architecture level but only a small fraction of paths become
queryable through `path_index`.

## Context

Recent project cognition work already improved scan/build normalization:

- scan artifacts now have a canonical schema for nodes, edges, observations,
  evidence, and coverage rows
- the Go runtime accepts downstream natural aliases such as `node_id`, `kind`,
  `label`, `source_node_id`, `target_node_id`, `attrs_json`, and coverage
  arrays
- `build-from-scan` creates `path_index` rows from node paths and rejects
  coverage paths without a node relation
- docs and tests now state that `coverage.json` is coverage accounting, not a
  path-index source

Those fixes make malformed downstream artifacts importable, but they do not
solve the larger workflow problem: broad scan packets can still return shallow
or incomplete results, and the leader does not yet have a durable dispatch loop
that receives a result, reads current task state, derives the remaining gaps,
and dispatches the next subagent wave.

This design builds on:

- `2026-05-24-project-cognition-coverage-boundary-design.md`
- `2026-05-24-project-cognition-runtime-build-pipeline-design.md`
- `2026-05-25-map-scan-packet-ledger-design.md`

## Problem

The current system has packet validation and artifact validation, but it is not
yet a complete scan work scheduler.

The missing loop is:

```text
leader receives subagent result
-> leader reads durable scan state
-> leader validates handoff quality
-> leader updates queue, coverage, and handoff ledgers
-> leader plans next packets
-> leader dispatches another bounded subagent wave
-> repeat until build_ready or blocked
```

Without that loop, a subagent can optimize for a plausible summary. In a large
repository this produces a map that is useful for high-level orientation but
cannot reliably answer changed-path questions.

The practical symptoms are:

- many paths are `inventory_only`
- few paths are `deep_read`
- node `paths` arrays are sparse or empty
- broad aggregate nodes represent dozens of files without file-level ownership
- `coverage.json` contains paths that never become queryable `path_index` rows
- `project-cognition query` can return no affected nodes for concrete changed
  paths

## Lessons From The Recent Fix

The last normalization fix exposed five useful implementation lessons that this
design should preserve as regression requirements.

1. RED tests must model downstream reality before implementation. The useful
   tests were the ones that reproduced natural artifact shapes such as
   `node_id`, `kind`, `label`, `source_node_id`, `target_node_id`, `attrs_json`,
   and compatibility coverage arrays.
2. Generic helpers can be too broad. The initial coverage merge helper
   accidentally risked merging unrelated `nodes + rows` data. Coverage
   compatibility merging must stay scoped to `coverage.json`.
3. Empty arrays are valid arrays. Runtime helpers must track whether an array
   key was found separately from whether it had rows.
4. Test fakes must move with the real runtime. Python fake
   `project-cognition` behavior must mirror the Go runtime's accepted artifact
   shapes closely enough that hook and integration tests do not validate a
   different product.
5. Integration tests need stable collection entry points. Regression commands
   should target actual pytest collector functions or stable files, not guessed
   node ids.

These lessons point to the same conclusion: scan/build correctness is a
contract surface across prompts, templates, Go runtime, fake runtime, hooks,
docs, and tests. It cannot be optimized in one layer only.

## Goals

- Make `sp-map-scan` resumable from durable state, not chat history.
- Give the leader an explicit scheduler loop for packet intake, queue updates,
  gap planning, and redispatch.
- Make subagent prompts packet-specific, budget-aware, and output-schema-bound.
- Give subagents honest exits for `overflow`, `blocked`, `repack_required`, and
  known unknowns.
- Make queryable path closure a scan acceptance requirement.
- Keep `sp-map-build` conservative: it may normalize compatible scan fields,
  but it must not invent ownership from coverage rows alone.
- Add build validation gates that fail sparse or non-queryable baselines.
- Keep fake runtime, hook tests, integration tests, generated templates, docs,
  and Go runtime aligned.

## Non-Goals

- Do not require every repository file to be deep-read.
- Do not let `build-from-scan` compensate for missing scan ownership by
  silently converting every coverage row into a path index.
- Do not replace `map-update` for ordinary post-baseline maintenance.
- Do not introduce durable `sp-teams` state for the common in-session packet
  loop unless a later implementation proves in-session state is insufficient.
- Do not turn this design into a full graph semantics rewrite beyond scan
  scheduling and build quality gates.

## Recommended Approach

Implement a stateful scan scheduler around four durable workbench artifacts:

- `repository-universe.json`
- `scan-queue.json`
- `coverage-ledger.json`
- `handoff-ledger.json`

The leader initializes the universe and queue, dispatches bounded packets,
validates structured worker results, updates the ledgers, plans gaps, and
repeats. Build is allowed only when the ledger state proves enough path-level
closure for the accepted baseline.

This is preferred over asking subagents to "scan more thoroughly" because it
matches the real constraint: subagents have bounded context and need explicit
handoff rules.

## State Model

### `repository-universe.json`

The universe remains the canonical boundary artifact. It should include the
existing fields and add or standardize packet and closure metadata:

- `schema_version`
- `candidate_universe`
- `included_paths`
- `excluded_paths`
- `ambiguous_paths`
- `dispositions`
- `criticality`
- `classification_reasons`
- `decision_source`
- `owner_hint`
- `packet_id`
- `coverage_state`

Every candidate path receives exactly one disposition:

- `deep_read`
- `sampled`
- `inventory_only`
- `excluded`
- `blocked`

Criticality remains separate:

- `critical`
- `important`
- `low_risk`

### `scan-queue.json`

`scan-queue.json` is the leader-owned scheduler state. It records packet
lifecycle and retry lineage.

Packet states:

- `pending`
- `claimed`
- `returned`
- `accepted`
- `repack_required`
- `overflow`
- `blocked`
- `cancelled`

Each packet row should include:

- `packet_id`
- `parent_packet_id`
- `wave`
- `attempt`
- `state`
- `assigned_paths`
- `expected_depth`
- `criticality_floor`
- `file_budget_hint`
- `token_budget_hint`
- `claimed_at`
- `returned_at`
- `result_handoff_path`
- `split_reason`
- `next_action`
- `blocking_reason`

### `coverage-ledger.json`

`coverage-ledger.json` is the path-level truth for scan closure. It should
continue carrying coverage rows and open gaps, but each row must be rich enough
for the leader to decide whether a path can proceed to build.

Each row should include:

- `path`
- `packet_id`
- `coverage_state`
- `read_depth`
- `criticality`
- `evidence_ids`
- `node_ids`
- `node_path_status`
- `known_unknowns`
- `confidence`
- `accepted_at`
- `revisit_condition`

Important closure states:

- `covered`
- `sampled`
- `inventory_only`
- `missing_evidence`
- `missing_node_path`
- `aggregate_only`
- `overflow`
- `blocked`
- `excluded`

### `handoff-ledger.json`

`handoff-ledger.json` records every dispatch and return event so another leader
can resume without reading conversation history.

Each row should include:

- `event_id`
- `packet_id`
- `wave`
- `attempt`
- `event_type`
- `dispatch_summary`
- `worker_result_path`
- `intake_status`
- `intake_errors`
- `accepted_paths`
- `remaining_paths`
- `recommended_followup_packets`
- `leader_decision`
- `created_at`

This ledger is not graph truth. It is operational state for recoverability.

## Leader Scheduler Loop

The leader follows the same loop for every scan wave:

```text
1. Load repository-universe.json, scan-queue.json, coverage-ledger.json, and
   handoff-ledger.json.
2. Select pending packets that fit available dispatch capacity.
3. Render a strict packet prompt for each selected packet.
4. Dispatch subagents.
5. Receive worker-results/<packet-id>.json.
6. Run intake validation.
7. Update queue, coverage, and handoff ledgers.
8. Run the gap planner.
9. Create new packets for remaining or low-quality work.
10. Repeat until build_ready or blocked.
```

Completion states:

- `build_ready`: all required packet and path closure gates pass
- `blocked`: a critical gap, systemic contract failure, or unrecoverable tool
  failure remains
- `partial_refresh`: reserved for update flows, not first baseline completion

The leader must not report scan completion from natural-language subagent
summaries. It reports completion from ledger state and validation output.

## Subagent Dispatch Prompt Contract

The prompt is product behavior, not ad hoc wording. It should be generated from
a template and mirrored in tests.

Required sections:

1. Role:
   - "You are a bounded map-scan worker."
   - "Your job is to advance exactly one packet, not understand the whole
     repository."
2. Packet:
   - `packet_id`
   - `assigned_paths`
   - `expected_depth`
   - `criticality`
   - `token_budget_hint`
   - `file_budget_hint`
   - allowed and forbidden paths
3. Budget rule:
   - If the assigned paths exceed budget, return `overflow` with split
     recommendations.
   - `overflow` is a valid handoff; pretending to finish is not.
4. Evidence rule:
   - Every `read` or `deep_read` path must produce evidence.
   - Evidence must include `source_path`, span or equivalent location,
     extractor, summary or content hash, and confidence.
5. Node path rule:
   - Every queryable path the worker understands must appear in at least one
     returned node `paths` array.
   - Do not invent ownership for unread files.
6. Follow-up rule:
   - Do not expand scope silently.
   - Adjacent paths go into `recommended_followup_packets`.
7. Output rule:
   - Return only JSON matching the worker handoff schema.

Prompt skeleton:

```text
You are a bounded map-scan worker.

Your job is not to understand the whole repository.
Your job is to advance exactly one scan packet to a verifiable state.

Packet:
- packet_id: <id>
- assigned_paths: [...]
- expected_depth: deep_read | sampled | inventory_only
- criticality: critical | important | low_risk
- token_budget_hint: <n>
- file_budget_hint: <n>

Rules:
- Read only assigned_paths unless a path is required to understand an assigned
  path.
- If the packet exceeds budget, stop and return overflow with split
  recommendations.
- Every read/deep_read outcome must include evidence.
- Every queryable source path you understand must appear in a node paths array.
- Do not invent ownership for unread files.
- Do not return natural-language-only summaries.

Return only JSON matching the schema.
```

## Worker Handoff Schema

Each worker result should be JSON and should include:

- `packet_id`
- `assigned_paths`
- `paths_read`
- `coverage`
- `evidence`
- `nodes`
- `edges`
- `observations`
- `known_unknowns`
- `recommended_followup_packets`
- `acceptance_self_check`
- `outcome`
- `confidence`

Allowed outcomes:

- `pass`
- `overflow`
- `blocked`
- `fail_gap`
- `fail_quality`
- `fail_contract`
- `fail_systemic`

`pass` is only a worker self-assessment. The leader still owns final
acceptance.

## Intake Validation

The leader must validate every worker result before merging it into scan
artifacts.

Format checks:

- result is valid JSON
- required keys exist
- `packet_id` matches a queue row and scan packet
- `assigned_paths` match the packet
- `paths_read` is an array of concrete paths, not a boolean or summary flag
- no unassigned path is treated as accepted coverage

Evidence checks:

- every `read` or `deep_read` coverage row references existing evidence ids
- at least one referenced evidence row has `source_path` equal to the coverage
  path
- evidence paths do not enter `.specify/**` or `.cognitionignore`-excluded
  areas

Ownership checks:

- queryable paths must be represented in node `paths`
- broad aggregate nodes must either include file/module child nodes or mark
  `paths_complete=false`
- critical paths cannot pass with only aggregate ownership

Quality checks:

- summary-only output fails
- hidden uncertainty fails
- critical or important inventory-only results fail unless the universe
  recorded an accepted lower-depth decision
- repeated sibling quality failures escalate to `fail_systemic`

## Gap Planner

After intake, the leader runs a deterministic gap planner.

Gap to next-packet mapping:

- `overflow` creates child packets with smaller assigned path sets.
- `missing_evidence` creates evidence-deepening packets.
- `missing_node_path` creates node-path repair packets.
- `aggregate_only` creates file/module split packets.
- `fail_quality` creates stricter retry packets for the declared subset.
- `fail_contract` repairs packet schema or worker prompt shape before
  redispatch.
- discovered adjacent surfaces create follow-up packets when they are relevant
  to owner, consumer, state, generated surface, or verification closure.
- critical `blocked` gaps block the baseline until resolved or explicitly
  accepted by policy.

The planner should never rerun the full original packet by default. It should
retry only the uncovered, low-quality, or overflowed subset unless the failure
is systemic.

## Build Contract Changes

`build-from-scan` stays conservative.

Allowed build behavior:

- normalize accepted compatibility fields
- generate stable ids for compatible rows when the scan contract allows it
- create `path_index` rows from node paths
- record coverage rejections such as `no_node_relation`

Disallowed build behavior:

- silently convert every `coverage.json` path into `path_index`
- infer node ownership from evidence paths unless scan state explicitly
  declared that evidence path belongs to the node
- hide sparse path-index coverage behind a successful structural import

`validate-build` should add quality gates:

- `included_paths_count`
- `coverage_paths_count`
- `path_index_count`
- `path_index_to_included_ratio`
- `critical_missing_path_index`
- `important_missing_path_index`
- `aggregate_nodes_without_file_paths`
- `coverage_rejections_count`

Build should fail when:

- active generation has zero `path_index` rows
- critical included paths lack path-index ownership
- important included paths lack path-index ownership without accepted gaps
- path-index coverage is far below the included path universe threshold
- aggregate nodes represent broad file sets without file/module closure

The threshold should be configurable or staged, but the observed shape of
thousands of included paths and only dozens of path-index rows must not pass as
query-ready.

## Runtime And Fake Alignment

The Go runtime remains the source of truth. Python fake runtime tests must track
the behavior that templates and hooks rely on.

Alignment rules:

- compatibility coverage array support must exist in both Go runtime and test
  fake when tests depend on it
- compatibility merging must be scoped to `coverage.json`
- empty arrays must count as present arrays
- fake runtime should validate the same high-level sparse-build failures when
  integration tests exercise those gates
- fake behavior should be intentionally smaller than Go only where tests do not
  depend on the omitted behavior

## Documentation And Template Surfaces

This change affects product prompts and generated workflow behavior, so it must
be cross-surface:

- `templates/commands/map-scan.md`
- `templates/commands/map-build.md`
- `templates/command-partials/map-scan/shell.md`
- `templates/command-partials/map-build/shell.md`
- passive skill mirrors that mention scan/build
- worker prompts for scan/build lanes
- `README.md`
- `PROJECT-HANDBOOK.md`
- `templates/project-handbook-template.md`
- hook validation surfaces
- Go runtime validation and tests
- Python fake runtime and integration tests

Do not ship this as a template-only prompt edit. The runtime validators need to
enforce the contract the prompt teaches.

## Testing Strategy

Add or update Go tests for:

- scan queue lifecycle validation
- worker result intake validation
- overflow split packet planning
- missing evidence to evidence-deepening packet planning
- missing node paths to repair packet planning
- sparse path-index build validation failure
- critical path missing path index failure
- aggregate node without file-level paths failure
- empty compatibility arrays treated as present
- coverage compatibility merge scoped only to coverage

Add or update Python/template tests for:

- generated `map-scan` teaches the stateful leader loop
- generated `map-scan` includes the worker prompt contract
- generated `map-build` explains sparse path-index quality gates
- fake `project-cognition` mirrors accepted compatibility shapes
- hook contract tests reject sparse query readiness
- integration tests use stable collector entry points

Add a regression fixture with this failure shape:

- 3,000+ included paths
- most paths are inventory-only
- nodes exist but many have empty `paths`
- path-index count is tiny relative to included paths
- query for a concrete changed path returns no owning node

The expected result is not a successful query-ready baseline. The expected
result is `validate-build` blocked with specific sparse-coverage diagnostics.

## Acceptance Criteria

- A leader can resume a scan from state files without relying on conversation
  history.
- Every dispatched packet has a queue row and a handoff-ledger entry.
- Every accepted packet result has path-level coverage accounting.
- Subagents can return `overflow` or `blocked` without being treated as failed
  workers.
- The leader can automatically generate the next packet wave from ledger gaps.
- Scan cannot be build-ready while critical paths lack evidence or node paths.
- Build cannot be query-ready with thousands of included paths and only dozens
  of path-index rows.
- Runtime, fake runtime, hooks, docs, templates, and tests agree on accepted
  artifact shapes.
- Regression tests protect against broad helper side effects and empty-array
  presence bugs.

## Open Risks

- A scheduler that is too strict may block useful partial maps. The first
  implementation should distinguish first-baseline acceptance from advisory
  map use by ordinary workflows.
- Packet splitting heuristics will need tuning across languages and repository
  shapes.
- Some aggregate nodes are legitimate. The validator must distinguish useful
  aggregate ownership from aggregate-only coverage that prevents changed-path
  queries.
- Fake runtime fidelity can become expensive if it grows into a second runtime.
  Keep it scoped to test-observed behavior.

## Implementation Notes

Start with validation and template changes before broad runtime behavior:

1. Teach `map-scan` the durable scheduler loop and prompt contract.
2. Add scan queue and handoff ledger schema validation.
3. Add intake validation for existing worker result artifacts.
4. Add build sparse-path-index gates.
5. Update fake runtime and integration tests.
6. Add gap planner behavior after the state files and validators are stable.

This order keeps the work testable while preventing another prompt-only
contract from drifting away from runtime behavior.
