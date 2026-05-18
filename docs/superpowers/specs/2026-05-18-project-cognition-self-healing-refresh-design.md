# Project Cognition Self-Healing Refresh Design

## Problem

Project cognition currently treats several different conditions as if they all
mean "run `sp-map-scan`, then `sp-map-build`":

- the baseline runtime is missing or unusable
- a query is broader than the indexed facts can prove
- changed paths are not present in `path_index`
- a discussion explores future work beyond current repository evidence

That is too coarse. It creates a poor loop for users who already built a fresh
baseline and then immediately see another rebuild recommendation during normal
discussion or ordinary iteration.

The core issue is that project cognition needs to distinguish baseline health,
query coverage, and workflow proof requirements. A healthy baseline can still
have incomplete coverage for a broad question. A broad discussion can continue
with unknowns. A normal new file can often be adopted into an existing module
without rebuilding the whole graph.

## Goals

- Make `sp-map-scan -> sp-map-build` a last-resort structural repair path.
- Let discussion and brainstorming continue when cognition coverage is
  incomplete, while clearly exposing unknowns and confidence.
- Let `sp-map-update` adopt safely classifiable new paths into the current
  runtime instead of forcing a full rebuild.
- Keep implementation and planning gates evidence-based when they write project
  facts into durable artifacts.
- Give the user one clear next action rather than a stack of competing recovery
  suggestions.

## Non-Goals

- Do not make project cognition silently claim facts that were not proven.
- Do not remove full rebuilds for missing, corrupt, schema-incompatible, or
  architecture-invalidated baselines.
- Do not make discussion outputs authoritative implementation facts without
  evidence.
- Do not require agents to manually choose between map commands when the runtime
  can classify the condition.

## Model

Project cognition decisions should be split into three independent axes:

1. `baseline_health`: whether the graph runtime itself is usable.
2. `query_coverage`: whether the current question or changed-path set is covered
   well enough by the runtime.
3. `workflow_requirement`: whether the active workflow needs proven facts,
   review-level guidance, or only exploratory discussion.

The runtime should derive next actions from the combination of those axes.

The new axes are additive compatibility fields. Existing consumers may keep
reading `freshness`, `readiness`, and `recommended_next_action` during the
transition, but those fields must be derived from the richer classification
instead of treating every coverage miss as a rebuild.

Examples:

- Healthy baseline, broad discussion, incomplete coverage:
  `discussion_allowed`, expose unknowns, suggest minimal live reads.
- Healthy baseline, new path under known module:
  `map_update_adopt`, create provisional path coverage.
- Healthy baseline, new path with uncertain ownership:
  `review`, record minimal live reads and low-confidence closure.
- Missing or unusable baseline:
  `run_map_scan_build`.
- Large architecture replacement or missing paths that exceed unadoptable
  thresholds:
  `run_map_scan_build`.

## Compatibility Mapping

Existing public fields remain stable:

- `freshness`: machine baseline state used by generated workflows.
- `readiness`: task-local routing state returned by query/update helpers.
- `recommended_next_action`: one public action for the operator or workflow.

The compatibility mapping is:

| baseline_health | query_coverage | workflow_requirement | freshness | readiness | recommended_next_action |
| --- | --- | --- | --- | --- | --- |
| `missing` | any | any | `missing` | `needs_rebuild` | `run_map_scan_build` |
| `unusable` | any | any | `missing` | `blocked` | `run_map_scan_build` |
| `schema_incompatible` | any | any | `missing` | `needs_rebuild` | `run_map_scan_build` |
| `healthy` | `covered` | any | `fresh` | `ready` | `retry_current_workflow` |
| `healthy` | `possibly_stale` | `discussion` | `possibly_stale` | `review` | `perform_minimal_live_reads` |
| `healthy` | `possibly_stale` | `planning_or_implementation` | `possibly_stale` | `review` | `run_map_update` when proof is required, otherwise `perform_minimal_live_reads` |
| `healthy` | `adoptable_path_gap` | any | `stale` before update, `fresh` or `possibly_stale` after adoption | `needs_update` before update, `ready` or `review` after adoption | `run_map_update` before update, then `retry_current_workflow` or `perform_minimal_live_reads` |
| `healthy` | `uncertain_path_gap` | `discussion` | `possibly_stale` | `review` | `perform_minimal_live_reads` |
| `healthy` | `uncertain_path_gap` | `planning_or_implementation` | `partial_refresh` only if required proof still failed after update | `review` or `needs_update` | `run_map_update` or `perform_minimal_live_reads`; not scan/build solely because a path is missing |
| `healthy` | `unadoptable_path_gap` | any | `stale` | `needs_rebuild` | `run_map_scan_build` |
| `healthy` | `baseline_identity_invalidated` | any | `stale` | `needs_rebuild` | `run_map_scan_build` |

`partial_refresh` is narrowed to mean "refresh data was recorded, but the
readiness required by the active workflow did not pass." It must not mean "a
path was absent from `path_index` before classification."

`needs_rebuild` is reserved for missing, unusable, schema-incompatible, explicit
rebuild, baseline-identity-invalidated, or unadoptable coverage gaps. Missing
path-index coverage alone maps to `needs_update`, `review`, or `needs_rebuild`
only after adoption classification.

## Refresh Policy

The default path should be:

```text
query -> map-update/adopt -> live-read fallback -> scan/build as last resort
```

`sp-map-update` remains the normal maintenance entrypoint after the first
baseline build. It handles:

- existing indexed paths that changed
- user-supplied corrections for known areas
- new files that can be classified under existing modules, owners, or evidence
  routes
- bounded uncertain gaps within the review thresholds that can be carried as
  review-level unknowns

`sp-map-scan -> sp-map-build` is reserved for:

- no active baseline
- missing or corrupt graph runtime
- schema or contract incompatibility
- explicit user-requested rebuild
- broad architecture replacement that invalidates the baseline identity
- missing paths that exceed the unadoptable thresholds
- scan coverage policy gaps that miss a core project surface

## New Path Adoption

When `sp-map-update` sees paths missing from `path_index`, it should classify
them before recommending a rebuild.

Adoptable paths:

- share a directory with indexed siblings
- live under a known module or known test/script/docs surface
- match existing route, command, integration, or verification naming patterns
- can inherit an owner or nearest module relation within the adoption thresholds

For adoptable paths, `map-update` should create provisional coverage records and
mark them as low confidence until stronger evidence is collected. The status
should not become blocked solely because the path is new.

### Adoption Write Contract

Adoption must write a valid graph contract, not just append a path string.

For an adoptable path under an existing node, `map-update` should:

- create an `evidence` row with:
  - `source_kind = "path_adoption"`
  - `source_path = <adopted path>`
  - `extractor = "map-update-adoption"`
  - `content_hash` from file content when the file exists, otherwise a stable
    hash of the path plus update id for deleted or planned paths
  - `attrs_json` containing `adoption_status`, `adoption_reason`,
    `nearest_indexed_sibling`, and `update_id`
- add a `path_index` row pointing at the inherited nearest node:
  - `relation = "provisional_path"`
  - `confidence = "weak"` for inferred ownership or `partial` when live reads
    confirm the local relation
  - `evidence_id` referencing the new adoption evidence row
- write update metadata with `adopted_paths`, `adoption_confidence`, and
  `minimal_live_reads`. `adoption_confidence` may use review-oriented labels in
  update metadata, but graph confidence fields must use the existing
  `weak`/`partial`/`strong`/`grounded` vocabulary.

For a path that cannot safely inherit an existing node but is still small and
localized, the first implementation should not create a provisional node by
default. It should record update metadata and return `review` with
`minimal_live_reads`. Provisional node creation is allowed only when the nearest
module is known but no existing node represents the new sub-surface; in that
case it must create a `nodes` row with:

- `type = "provisional_surface"`
- `confidence = "weak"`
- `attrs_json` containing `adoption_status = "provisional"` and `update_id`
- `node_evidence` pointing at the adoption evidence row
- `path_index.relation = "provisional_owner"`

Adoption must never reuse an unrelated sibling's evidence id for the new path.
It may cite the nearest sibling in `attrs_json`, but the adopted path needs its
own evidence row so later scans can supersede or validate it cleanly.

Uncertain paths:

- have no indexed siblings but are small in number
- appear related to an existing concept but lack enough evidence for ownership
- are discussion-only hints rather than touched implementation files

For uncertain paths, `map-update` should return review readiness with
`minimal_live_reads`, `known_unknowns`, and confidence metadata. It should not
route directly to scan/build unless the active workflow requires stronger proof.

Unadoptable paths:

- introduce new top-level systems or large new directories
- cross many unrelated domains
- touch build, release, routing, or state ownership in a way that invalidates
  prior graph structure
- exceed configured missing-path thresholds
- reveal that the initial scan excluded core live surfaces

For unadoptable paths, the runtime should recommend `sp-map-scan -> sp-map-build`
with a concrete reason.

### Default Thresholds

The first implementation should use conservative defaults that can later move to
configuration:

- Adopt automatically when every missing path has an indexed sibling in the same
  directory, or under the nearest indexed ancestor within two directory levels.
- Adopt automatically when the missing path count is at most 10 and all missing
  paths resolve to one existing node or one known module family.
- Return `review` rather than rebuild when the missing path count is at most 5
  and the paths share one top-level directory but do not have enough evidence for
  automatic adoption.
- Escalate to scan/build when more than 25 missing paths are unclassified, when
  missing paths span more than 3 unrelated top-level live-surface directories, or
  when more than 40 percent of requested changed paths are unadoptable.
- Escalate to scan/build immediately for missing paths that reveal excluded or
  absent core live surfaces such as build/release orchestration, generated
  command templates, routing registries, schema registries, package manifests,
  or workflow dispatch maps, unless they are clearly under an already indexed
  module with indexed siblings.
- Treat deleted paths that were never indexed as `review` for discussion and
  `needs_update` for implementation, not scan/build, unless the deletion is part
  of a broad architecture replacement.

## Discussion Behavior

Discussion, brainstorming, and early feasibility exploration may exceed current
cognition coverage. In those modes, incomplete coverage is not a blocker.

The runtime should return:

- discussion can continue
- which claims are project-proven
- which claims require live reads
- which claims are speculative or future-facing
- when stronger proof is needed before planning or implementation

The agent may continue the conversation, but must not write unsupported project
facts into durable plans, tasks, or implementation decisions.

Discussion still blocks on structural runtime failures:

- missing active baseline
- missing DB or status file
- corrupt DB
- schema or contract incompatibility
- explicit rebuild requested by the user

Discussion does not block on ordinary stale, partial-refresh, or path-coverage
gaps when the conversation is exploratory. In those cases it continues with
unknowns, confidence labels, and minimal live reads. Handoff from discussion to
`specify`, `plan`, or implementation must re-check proof requirements before
turning discussion claims into durable project facts.

## Workflow Behavior

Planning and implementation workflows need stricter gates than discussion.

- If the workflow only needs orientation, review-level cognition plus minimal
  live reads is enough.
- If the workflow will write source-changing tasks, durable implementation
  assumptions, or build/release facts, the required surfaces must be proven or
  explicitly marked as unknown.
- If required surfaces are missing but adoptable, `map-update` should adopt them.
- If required surfaces are missing and unadoptable, only then should the workflow
  route to `sp-map-scan -> sp-map-build`.

## User Experience

The user should see one concrete state and one next action.

Good examples:

- "You can continue discussion. These facts are not yet proven by project
  cognition: ..."
- "New paths were adopted into the existing cognition baseline with review-level
  confidence."
- "The baseline is healthy, but this implementation plan requires build-system
  facts that are not covered. Run `sp-map-update` first."
- "The baseline missed a core build surface and cannot safely adopt these paths.
  Run `sp-map-scan`, then `sp-map-build`."

Avoid generic recommendations that ask for scan/build merely because a query is
wide or a discussion goes beyond indexed facts.

## Testing

Add regression coverage for:

- missing active generation still routes to scan/build
- corrupt or schema-incompatible DB still routes to scan/build
- broad architecture replacement still routes to scan/build
- changed indexed paths route through update
- new path under indexed sibling is adopted without scan/build
- bounded uncertain new path returns review/minimal live reads, not rebuild
- discussion mode with incomplete coverage returns discussion-allowed
- implementation mode with the same incomplete coverage requires proof before
  durable source-changing work
- path-index gap reasons no longer always map to `run_map_scan_build`
- `freshness`, `readiness`, and `recommended_next_action` preserve compatibility
  while deriving from `baseline_health`, `query_coverage`, and
  `workflow_requirement`
- adopted paths create valid `evidence`, optional `nodes` or `node_evidence`,
  and `path_index` rows with no dangling references
- discussion still blocks on missing, corrupt, or schema-incompatible baselines
- generated workflow guidance no longer says every missing `path_index` gap
  requires scan/build

## Implementation Surfaces

Implementation must update the runtime, tests, and generated guidance together.

Runtime/code:

- `src/specify_cli/cognition/query.py`
- `src/specify_cli/cognition/update.py`
- `src/specify_cli/project_cognition_status.py`
- `src/specify_cli/hooks/project_cognition.py`
- CLI output helpers in `src/specify_cli/__init__.py`
- compatibility freshness helpers in
  `scripts/bash/project-map-freshness.sh` and
  `scripts/powershell/project-map-freshness.ps1`

Tests:

- `tests/test_project_cognition_query.py`
- `tests/test_project_cognition_db.py`
- `tests/test_project_map_status.py`
- `tests/integrations/test_cli.py`
- hook and template guidance tests that assert freshness routing text

Generated guidance and docs:

- `templates/commands/map-update.md`
- `templates/commands/discussion.md`
- `templates/commands/{specify,plan,tasks,analyze,debug,quick,prd-scan}.md`
- `templates/command-partials/common/context-loading-gradient.md`
- `templates/command-partials/common/senior-consequence-analysis-gate.md`
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- `templates/project-handbook-template.md`
- `PROJECT-HANDBOOK.md`
- `README.md`
- generated integration renderers in `src/specify_cli/integrations/base.py`

## Open Implementation Notes

- Existing status vocabulary can remain, but the payload should add explicit
  fields for `baseline_health`, `query_coverage`, and `workflow_requirement`.
- Existing `partial_refresh` should be narrowed to "refresh data recorded but
  required readiness did not pass", not "any missing path exists".
- The first implementation should prefer conservative adoption rules and
  threshold-based rebuild escalation.
- Add a follow-up migration note if existing generated projects rely on the old
  interpretation that missing path coverage always requires full rebuild.
