# Agent-Native Project Cognition Design

## Context

`project-cognition` is a runtime used by agents, not a documentation product for humans. Its primary job is to make agent work more accurate and cheaper by caching facts, routing paths, classifying repository changes, and publishing queryable runtime state.

The current `sp-map-scan`, `sp-map-build`, and `sp-map-update` workflows already define strong contracts around `.cognitionignore`, scan artifacts, schema v2 publication, and incremental update boundaries. The next improvement is to shift more low-level, repeatable work into deterministic `project-cognition` commands so agents spend tokens only on semantic judgment.

The main external inspiration is the Understand-Anything workflow pattern: a thin skill orchestration layer, deterministic scripts for facts, bounded agent work for semantics, and strict machine-readable artifacts between phases.

## Goals

- Make `project-cognition` the agent's low-cost fact cache, change radar, structure index, query router, and runtime compiler.
- Let agents own semantic scanning and judgment while avoiding repeated low-level work such as path enumeration, ignore filtering, file classification, import discovery, symbol extraction, and Git diff analysis.
- Make `sp-map-update` the highest-frequency maintenance path and reserve `sp-map-scan -> sp-map-build` for first baseline, unusable baseline, or explicit rebuild conditions.
- Prefer machine-readable JSON, error codes, `next_action`, confidence, gaps, and minimal live reads over human-readable prose.
- Keep every published runtime fact rejectable, evidence-backed, and traceable to accepted scan or update inputs.

## Non-Goals

- Do not optimize project cognition for human map readability.
- Do not let deterministic commands claim complete business semantics.
- Do not make `sp-map-build` reread the repository or reconstruct truth from chat memory.
- Do not route ordinary missing paths, weak ownership, or partial closure to a full rebuild by default.
- Do not treat coverage rows as proof that a path is queryable runtime truth.

## Design Principle

The runtime should answer agent-native questions:

- What changed since the last cognition baseline?
- Which changed paths are ignored, cosmetic, structural, semantic-risk, renamed, deleted, or unknown?
- Which files should the agent read first, and why?
- Which runtime records are affected?
- Which scan packets are required?
- Which facts are proven, partial, stale, or blocked?
- What exact action should the agent take next?

The intended loop is:

```text
agent intent
  -> project-cognition changes/inventory/query/extract/update
  -> agent reads minimal live evidence
  -> agent writes bounded semantic payload
  -> project-cognition validates, normalizes, publishes, or rejects
```

## Runtime Command Surface

The design allows adding and changing `project-cognition` commands. The target command surface below is additive and focused on the low-level scan/build/update loop. It does not replace existing required runtime commands such as `init-empty`, `record-refresh`, `complete-refresh`, `compass`, `lexicon`, `query`, and `expand`.

Low-level commands added or strengthened by this design:

```text
project-cognition generate-ignore --format json
project-cognition changes --format json
project-cognition inventory --format json
project-cognition extract-structure --targets "$TARGETS_FILE" --format json
project-cognition packetize-scan --format json
project-cognition normalize-scan --format json
project-cognition affected-closure --changed-paths "$CHANGED_PATHS_FILE" --format json
project-cognition update --payload-file "$PAYLOAD_FILE" --reason "$REASON" --format json
project-cognition validate-scan --format json
project-cognition build-from-scan --format json
project-cognition validate-build --format json
```

Optional follow-up commands may be added when useful:

```text
project-cognition explain-build-blocker --format json
project-cognition classify-changes --format json
```

The command outputs should be stable JSON with explicit `status`, `next_action`, `errors`, `warnings`, and machine-readable reason fields.

## `sp-map-scan`

`sp-map-scan` becomes a scan planner and semantic packet runner. It should not rely on the agent to hand-classify the whole repository from scratch.

Target flow:

```text
generate-ignore
-> inventory
-> extract-structure
-> packetize-scan
-> agent/subagent semantic scan
-> validate-scan
```

Runtime duties:

- Apply `.cognitionignore` from the repository root and `.specify/project-cognition/.cognitionignore`.
- Enumerate paths using Git when available, with a filesystem fallback.
- Produce `.specify/project-cognition/workbench/repository-universe.json`.
- Classify path kind, language, size, Git tracking state, directory family, value tier, scan decision, disposition, criticality, and classification reasons.
- Produce `.specify/project-cognition/workbench/scan-targets.json`.
- Extract deterministic structure for selected paths: imports, exports, symbols, entrypoints, route-like surfaces, config surfaces, state surfaces, test surfaces, build/runtime surfaces, generated-surface references, and high-risk unknowns.
- Generate scan packets with assigned paths, must-read paths, optional paths, structure hints, expected outputs, known unknowns, and budget hints.

Agent duties:

- Read the packet-defined minimal file set.
- Produce provisional nodes, edges, observations, evidence rows, coverage rows, confidence notes, unresolved gaps, and minimal live reads.
- Override runtime path classification only with an explicit override reason.

`validate-scan` must reject or block when:

- Ignored paths appear in evidence, provisional graph rows, coverage rows, or packet scopes.
- P0/P1 paths selected for scan lack accepted packet results.
- Worker result `paths_read` is missing or not a concrete path array.
- Evidence IDs are missing or point to incompatible source paths.
- Coverage rows cannot be tied to packet-local coverage.
- Open gaps lack owner, reason, evidence expectation, and revisit condition.

## `sp-map-build`

`sp-map-build` becomes a compiler for scan packages. It must not reread the repository and must not use chat memory as runtime truth.

Target flow:

```text
validate-scan
-> normalize-scan
-> build-from-scan
-> validate-build
```

`normalize-scan` consumes:

- `repository-universe.json`
- `scan-targets.json`
- deterministic structure facts
- provisional nodes, edges, and observations
- coverage rows
- worker results
- evidence rows

`normalize-scan` outputs a normalized package with:

- canonical node IDs
- deduplicated paths
- resolved evidence references
- rejected rows with reason
- path identity merge records
- confidence floors
- carried known unknowns
- ignored path violations removed or rejected

`build-from-scan` compiles only the normalized package into schema v2 SQLite runtime tables:

- `metadata`
- `generations`
- `evidence`
- `nodes`
- `node_evidence`
- `edges`
- `edge_evidence`
- `observations`
- `observation_evidence`
- `path_index`
- `alias_index`
- `updates`

Publication rules:

- `nodes[].paths` is the primary source for `path_index`.
- `coverage.json` is boundary accounting and must not create path-index rows by itself.
- `alias_index` is route vocabulary for agent query normalization, not behavioral proof.
- Ignored paths must remain hard-excluded from evidence, path indexes, aliases, route rows, update records, and minimal live reads unless a `!` re-include or ignore-rule change brings them back into scope.
- Inventory-only paths must stay out of graph-facing runtime truth by default, but may be promoted when scan targets explicitly promote them and accepted evidence supports the promotion.
- Build blockers must return an executable repair packet with `next_action`, `paths_to_read`, `packets_to_rerun`, `rows_to_fix`, and `why_runtime_refused`.

## `sp-map-update`

`sp-map-update` is the default maintenance path after a usable baseline exists. It starts from Git, not agent guessing.

Target flow:

```text
changes
-> affected-closure
-> agent minimal semantic refresh
-> update
-> validate-build
-> complete-refresh | record-refresh when the freshness contract allows finalization
```

`project-cognition changes --format json` should:

- Read the baseline commit from `.specify/project-cognition/status.json`.
- Compare baseline to `HEAD`.
- Include staged changes, unstaged changes, and untracked files when requested or by default for workflow-finalize/update contexts.
- Preserve Git status codes such as `A`, `M`, `D`, `R`, and `C`.
- Track old path, new path, tracked state, dirty state, old blob hash, new blob hash, and file existence.
- Apply `.cognitionignore` before runtime update planning.
- Query the current DB for known paths, node IDs, aliases, owners, consumers, verification routes, stale records, and known unknowns.
- Run deterministic structure comparison for source-like changed paths.

Change levels:

```text
no_op
cosmetic
structural
semantic_risk
deleted
renamed
ignored
unknown
rebuild_required
```

`affected-closure` should return:

- changed paths
- known runtime scope
- must-read paths
- optional-read paths
- records to invalidate
- records to refresh
- minimal live reads
- unknowns
- verification paths
- whether a safe patch is possible

Agent duties:

- Read only changed paths, must-read paths, and necessary verification evidence.
- Write a bounded update payload with changed paths, behavior surfaces, generated surfaces, state contracts, verification, known unknowns, and confidence notes.

`project-cognition update` owns:

- Staling old records.
- Patching the active generation.
- Adding provisional path or alias rows when the affected scope is bounded.
- Preserving partial and low-confidence facts.
- Returning a final result state.

Valid result states:

```text
ready
no_op
partial_refresh
needs_rebuild
blocked
```

These result states are the completion gate. `update_id`, freshness timestamps, or recorded metadata alone are not sufficient.

Freshness finalization is explicit:

- If `update` returns `ready` or `no_op` and `validate-build` passes, run `project-cognition complete-refresh --format json` when the runtime can finalize against the current Git baseline.
- If the update was recorded while source changes are not yet committed, report the update as recorded and baseline finalization pending. After those source changes are committed, run `project-cognition record-refresh --reason "map-update" --format json` or `project-cognition complete-refresh --format json` to align freshness metadata without a full rebuild, unless validation reports `needs_rebuild`.
- If `update` returns `partial_refresh`, `blocked`, or `needs_rebuild`, do not call successful-refresh finalizers. Preserve the runtime state and surface the next action.

## Rebuild Boundary

`sp-map-update` must not escalate to `sp-map-scan -> sp-map-build` for ordinary uncertainty. Rebuild is reserved for:

- missing or unusable runtime
- schema invalid
- zero active-generation `path_index` rows outside a greenfield-empty baseline
- missing or invalid `alias_index`
- explicit rebuild request
- baseline identity invalid
- architecture replacement too broad to bound safely

Ordinary missing paths, weak ownership, weak aliases, partial closure, and bounded identity reconciliation debt should be handled through provisional adoption, low-confidence updates, known unknowns, `minimal_live_reads`, or `partial_refresh`.

## Error Model

Every command should prefer actionable machine state over prose.

Common output fields:

```json
{
  "status": "ok | review | blocked | error",
  "next_action": "no_op | affected_closure | repair_scan | rerun_scan_packet | identity_repair | rebuild_required | manual_ignore_review",
  "result_state": "ready | no_op | partial_refresh | needs_rebuild | blocked",
  "errors": [],
  "warnings": [],
  "reason_codes": [],
  "paths_to_read": [],
  "packets_to_rerun": [],
  "rows_to_fix": [],
  "minimal_live_reads": []
}
```

`result_state` is required for update-style commands and omitted only for commands where no runtime refresh state is being decided. Templates must not treat `status=ok` alone as update completion.

Blocked output must describe the smallest recovery action. If the runtime refuses to publish or update, it must state exactly which paths, rows, packet results, evidence references, or identity records caused the refusal.

## Testing Strategy

Runtime tests:

- Ignore loading, starter ignore generation, and ignored path filtering.
- Git-native change intake across committed, staged, unstaged, untracked, added, modified, deleted, renamed, and copied files.
- Structure extraction and structure diff for supported file families.
- Inventory classification and value-tier assignment.
- Packet generation with stable packet IDs and bounded must-read paths.
- Scan normalization with canonical IDs, evidence reference resolution, ignored path rejection, and path identity merging.
- Affected closure from changed paths to owners, consumers, state surfaces, generated surfaces, verification routes, aliases, and known unknowns.

CLI contract tests:

- JSON shape, exit codes, `status`, `next_action`, `errors`, and `warnings` for every command.
- Blocked and repair outputs include actionable path and row details.
- `changes` output is stable with dirty working trees.

Template tests:

- `sp-map-scan` calls `generate-ignore`, `inventory`, `extract-structure`, `packetize-scan`, and `validate-scan`.
- `sp-map-build` calls `validate-scan`, `normalize-scan`, `build-from-scan`, and `validate-build`.
- `sp-map-update` starts with `changes`, then uses `affected-closure`, `update`, and `validate-build`.
- Templates must not instruct agents to bypass runtime gates or publish DB truth directly.

Regression tests:

- `.cognitionignore`-excluded paths never enter evidence, provisional graph rows, path indexes, aliases, update records, or minimal live reads.
- Coverage rows do not create queryable runtime truth without node paths and accepted evidence.
- Bounded missing paths become provisional or partial update cases, not automatic rebuilds.
- Reserved rebuild conditions still route to `sp-map-scan -> sp-map-build`.

## Rollout

Implement in phases:

1. Git-native `changes` command and `sp-map-update` template integration.
2. Deterministic `inventory` and scan target generation.
3. `extract-structure` and `packetize-scan`.
4. `normalize-scan` before `build-from-scan`.
5. Stronger affected closure and query packet publication.

This order improves the highest-frequency path first while keeping the scan/build baseline compatible with current contracts.
