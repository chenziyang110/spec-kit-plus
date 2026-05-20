# Map Update First Maintenance Design

Date: 2026-05-21

## Context

Project cognition currently documents the intended lifecycle as:

- `map-scan -> map-build` creates the first brownfield cognition baseline.
- `map-update` maintains that baseline after ordinary source, runtime, workflow, or support changes.
- A full scan/build rebuild should be exceptional.

The current implementation still has several paths that can recommend or route to
`map-scan -> map-build` after ordinary work. In practice this violates the
operating principle that scan/build should run once for baseline creation and
that later maintenance should be absorbed by `map-update`.

## Problem

After completing a requirement, agents often invoke or recommend map maintenance.
When the project cognition runtime sees missing `path_index` coverage, high-impact
paths, large changed-path batches, or partial refresh states, it can still surface
`run_map_scan_build`. Agent prompts and CLI guidance may then tell the user to
scan and build again, even though a usable baseline exists.

This creates three problems:

- It makes scan/build feel like routine maintenance instead of a baseline rebuild.
- It trains agents to abandon incremental update whenever coverage is imperfect.
- It wastes time and increases drift risk by rebuilding broad map state for localized changes.

## Goals

- Make `map-update` the default and durable maintenance entrypoint after a usable baseline exists.
- Prevent ordinary changed-path gaps from recommending `map-scan -> map-build`.
- Make `map-update` handle as many scenarios as safely possible by recording partial, review, low-confidence, known-unknown, and minimal-live-read data.
- Preserve scan/build for true baseline creation or structural recovery only.
- Define a machine-readable baseline-identity-invalid contract so old count or ratio heuristics cannot survive under a new label.
- Align runtime machine fields, generated prompts, passive skills, CLI output, hooks, docs, and tests.

## Non-Goals

- Do not remove `map-scan` or `map-build`.
- Do not claim uncertain project cognition facts are strong evidence.
- Do not make map output authoritative for code behavior. Live evidence still proves technical claims.
- Do not redesign the SQLite schema unless a small compatibility-safe field adjustment is needed during implementation.

## Approved Approach

Use the hardline policy:

Once a usable active generation exists, ordinary maintenance must not route back
to `map-scan -> map-build`. Missing or weak coverage becomes an incremental
`map-update` concern. If the update cannot fully prove closure, it records the
best safe state instead of forcing a rebuild.

`map-scan -> map-build` remains appropriate only when:

- No project cognition baseline exists.
- The DB, status file, or active generation is missing or unusable.
- Schema validation proves the runtime cannot be read safely.
- The user explicitly requests a full rebuild.
- The current baseline identity is invalid because of broad architecture replacement, not merely because changed paths are numerous or unfamiliar.

## Baseline Identity Invalid Contract

Baseline identity invalidation is a structural state, not a path-gap heuristic.

The machine contract is:

- The canonical reason token is `baseline_identity_invalid`.
- The runtime records this state by setting `CognitionStatus.baseline_state` to
  `blocked` and including `baseline_identity_invalid` in `dirty_reasons` or
  `stale_reasons`.
- When the state is user-initiated, also preserve the explicit user-rebuild
  reason in `manual_force_stale_reasons` or the update result metadata.
- `recommended_next_action=run_map_scan_build`, `readiness=needs_rebuild`, and
  `query_coverage=unadoptable_path_gap` are allowed for an existing baseline
  only when this token is present or when the baseline is otherwise unusable.

Who may set it:

- A user-explicit rebuild request may set it directly.
- Runtime validation may set it when the DB, status file, schema, active
  generation, or required graph tables cannot be read safely.
- `map-update` may set it only after live evidence proves the active baseline no
  longer represents the repository's architecture-level identity.

What may not set it by itself:

- Path count.
- Unrelated top-level path count.
- Core-surface path status.
- Weak ownership.
- Missing `path_index` coverage for ordinary changed paths.
- Unadoptable ratio or similar aggregate heuristics.

An active generation with zero `path_index` rows counts as an unusable baseline,
not as an ordinary path gap. It may still route to `map-scan -> map-build`
because `map-update` has no safe graph route to patch.

## Runtime Behavior

The runtime should distinguish baseline availability from coverage quality.

When no usable baseline exists, `recommended_next_action` may remain
`run_map_scan_build`.

When a usable active generation exists, `recommended_next_action` should not be
`run_map_scan_build` for ordinary path coverage gaps. Existing-baseline ordinary
gaps should also avoid `readiness=needs_rebuild` and
`query_coverage=unadoptable_path_gap` unless the explicit
`baseline_identity_invalid` contract or another unusable-baseline condition is
present. Instead:

- Covered changed paths return ready-style update results.
- Same-directory or near-ancestor missing paths are provisionally adopted by `map-update`.
- Unknown ownership or weak closure returns `review` or partial refresh with `minimal_live_reads`.
- Core live surfaces without indexed siblings return review or partial data, not rebuild.
- Large ordinary batches return review or partial data, not rebuild only because of size.
- Many unrelated top-level paths return review or partial data unless a separate baseline-identity-invalid condition is explicitly proven.

`apply_cognition_update` should maximize incremental handling:

- Write update records for all proven paths.
- Write provisional `path_index` rows where safe.
- Write known unknowns for uncertain paths.
- Preserve `minimal_live_reads` for the current workflow.
- Mark stale or partial areas explicitly instead of declaring the whole baseline unusable.
- Return `needs_rebuild` only for missing or unusable baseline conditions.

## Partial And Review Persistence Contract

`map-update` must persist imperfect maintenance results in a predictable shape.

For every update, the `updates` row should record:

- `updates.result_state=ready` when all changed paths are covered or safely adopted.
- `updates.result_state=review` when any ordinary existing-baseline gap requires
  live inspection, low-confidence closure, or user/operator review.
- `updates.result_state=needs_rebuild` only for missing baseline, unusable
  runtime, zero `path_index` active generation, schema failure, explicit rebuild,
  or recorded `baseline_identity_invalid`.
- `updates.attrs_json.known_unknowns` for facts that could not be proven.
- `updates.attrs_json.minimal_live_reads` for the smallest live evidence set the
  current workflow should inspect.
- `updates.attrs_json.path_adoption.review_paths` for paths that are not safely
  auto-adopted but are still maintainable through `map-update`.
- `updates.attrs_json.path_adoption.query_coverage=covered`,
  `adoptable_path_gap`, or `uncertain_path_gap` for ordinary existing-baseline
  cases. `unadoptable_path_gap` is reserved for unusable-baseline or
  `baseline_identity_invalid` cases.

For provisional coverage, `map-update` should write:

- An `evidence` row with `source_kind=path_adoption`.
- A `path_index` row with `relation=provisional_path`.
- `path_index.confidence=weak` or `partial`.
- Metadata linking the row to the update id and nearest indexed sibling or
  adoption reason when available.

For status metadata:

- Ready updates clear stale path-gap state and may set `freshness=fresh` when
  validation passes.
- Review updates set or preserve `freshness=possibly_stale`, keep
  `baseline_state=ready` when the graph is otherwise usable, and store
  `stale_paths`/`stale_reasons` for the review paths.
- Partial refresh after failed acceptance sets `freshness=partial_refresh` and
  recommends `run_map_update`, not scan/build, unless an unusable-baseline
  condition is present.
- Baseline identity invalidation sets `baseline_state=blocked`, uses the
  `baseline_identity_invalid` token, and is the existing-baseline path that may
  recommend scan/build.

Freshness recommendations should also follow this split:

- `missing` can recommend `run_map_scan_build`.
- `stale`, `possibly_stale`, and `partial_refresh` should recommend `run_map_update` or minimal review.
- Path-index-gap wording must not silently imply that scan/build is the next ordinary step.

## Prompt And Guidance Behavior

Generated prompts, passive skills, and preflight guidance should use the same policy:

- `map-update` is the ordinary maintenance workflow after baseline build.
- Do not auto-enter or recommend scan/build after every requirement completion.
- Do not escalate to scan/build just because closure is uncertain, a path is new, or many files changed.
- Tell the user to continue with live repository evidence when cognition is stale or partial.
- Tell the user to run `map-update` when refreshed advisory navigation is useful.
- Mention scan/build only for first baseline creation, missing or unusable runtime, schema incompatibility, explicit rebuild, or proven baseline identity invalidation.

The `map-update` command template should explicitly say that it handles:

- Added files and directories.
- Moved or renamed paths.
- Core runtime or workflow surfaces.
- Large ordinary changed-path batches.
- Unknown or weak ownership.
- Low-confidence closure.
- Partial facts, conflicts, stale claims, known unknowns, and minimal live reads.

## CLI And Hook Behavior

CLI and hook output should stop presenting scan/build as the ordinary recovery for
path gaps.

Preflight output should:

- Warn that cognition is advisory.
- Recommend `map-update` for stale, possibly stale, path-gap, and partial-refresh states.
- Preserve live-evidence continuation guidance.
- Show scan/build guidance only for missing or unusable baseline states.

Hook messages should:

- Block or warn according to existing command policy.
- Explain that `map-update` is the next maintenance action when a baseline exists.
- Avoid fallback text that says path-index gaps rebuild through scan/build.

## Implementation Surface

The implementation must update all map-maintenance surfaces that can emit rebuild
guidance:

- `src/specify_cli/cognition/path_adoption.py`
- `src/specify_cli/cognition/query.py`
- `src/specify_cli/cognition/update.py`
- `src/specify_cli/project_cognition_status.py`
- `src/specify_cli/hooks/project_cognition.py`
- CLI rendering in `src/specify_cli/__init__.py`
- `scripts/bash/project-map-freshness.sh`
- `scripts/powershell/project-map-freshness.ps1`
- `templates/commands/map-update.md`
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Generated integration guidance that embeds map-maintenance rules.
- User-facing docs that describe project cognition lifecycle, including
  `README.md` and `PROJECT-HANDBOOK.md`.

## Testing Strategy

Add or update regression tests so the policy is enforced at both runtime and prompt surfaces.

Runtime tests should cover:

- A core live surface missing from `path_index` returns review/update guidance, not `run_map_scan_build`, when an active generation exists.
- Many unrelated missing paths return review or partial guidance, not rebuild, when an active generation exists.
- Ordinary unknown subproject batches remain review/minimal-live-read cases.
- Existing-baseline ordinary gaps do not produce `readiness=needs_rebuild` or
  `query_coverage=unadoptable_path_gap`.
- `apply_cognition_update` writes update metadata and returns review or partial data for existing-baseline gaps.
- Missing active generation still returns `needs_rebuild` with `run_map_scan_build`.
- Active generation with zero `path_index` rows still counts as unusable and may
  return `needs_rebuild` with `run_map_scan_build`.
- A recorded `baseline_identity_invalid` token is required before existing-baseline
  path gaps can return scan/build guidance.
- `partial_refresh` recommends `run_map_update`.

Prompt and CLI tests should cover:

- Generated `map-update` instructions prefer partial/review handling over rebuild.
- Passive project cognition guidance does not describe ordinary path gaps as scan/build triggers.
- Preflight output for path gaps does not tell the user to run scan/build.
- Scan/build wording remains present for missing baseline and explicit rebuild cases.
- Bash and PowerShell freshness scripts match Python freshness behavior for
  path-index gaps, partial refresh, missing baseline, and explicit baseline
  identity invalidation.

## Acceptance Criteria

- Searching generated workflow guidance shows no ordinary changed-path or path-index-gap rule that routes directly to `map-scan -> map-build`.
- Existing-baseline runtime path gaps do not return `recommended_next_action=run_map_scan_build`.
- Existing-baseline ordinary gaps do not return `readiness=needs_rebuild` or
  `query_coverage=unadoptable_path_gap` unless `baseline_identity_invalid` or an
  unusable-baseline condition is recorded.
- `map-update` records useful partial or review state for uncertain coverage rather than failing closed.
- Partial/review results persist `updates.result_state`, `attrs_json.known_unknowns`,
  `attrs_json.minimal_live_reads`, `attrs_json.path_adoption.review_paths`,
  provisional `path_index` rows where safe, and matching status freshness.
- `run_map_scan_build` remains available for missing or unusable baseline recovery.
- Python, bash, and PowerShell freshness surfaces agree on when scan/build is
  permitted.
- Tests prove both the hardline policy and the remaining rebuild exceptions.

## Risks And Mitigations

Risk: The runtime may preserve a stale baseline too aggressively.

Mitigation: Use `partial_refresh`, low-confidence facts, known unknowns, and `minimal_live_reads` so workflows know where live evidence is required.

Risk: Agents may overtrust provisional update data.

Mitigation: Prompt guidance must state that project cognition is advisory and code behavior must be proven from live evidence.

Risk: Truly invalid baseline identity may be hidden as review state.

Mitigation: Keep a separate explicit baseline-identity-invalid condition for broad architecture replacement, but require that condition to be recorded directly instead of inferred from path count alone.
