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

## Runtime Behavior

The runtime should distinguish baseline availability from coverage quality.

When no usable baseline exists, `recommended_next_action` may remain
`run_map_scan_build`.

When a usable active generation exists, `recommended_next_action` should not be
`run_map_scan_build` for ordinary path coverage gaps. Instead:

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

## Testing Strategy

Add or update regression tests so the policy is enforced at both runtime and prompt surfaces.

Runtime tests should cover:

- A core live surface missing from `path_index` returns review/update guidance, not `run_map_scan_build`, when an active generation exists.
- Many unrelated missing paths return review or partial guidance, not rebuild, when an active generation exists.
- Ordinary unknown subproject batches remain review/minimal-live-read cases.
- `apply_cognition_update` writes update metadata and returns review or partial data for existing-baseline gaps.
- Missing active generation still returns `needs_rebuild` with `run_map_scan_build`.
- `partial_refresh` recommends `run_map_update`.

Prompt and CLI tests should cover:

- Generated `map-update` instructions prefer partial/review handling over rebuild.
- Passive project cognition guidance does not describe ordinary path gaps as scan/build triggers.
- Preflight output for path gaps does not tell the user to run scan/build.
- Scan/build wording remains present for missing baseline and explicit rebuild cases.

## Acceptance Criteria

- Searching generated workflow guidance shows no ordinary changed-path or path-index-gap rule that routes directly to `map-scan -> map-build`.
- Existing-baseline runtime path gaps do not return `recommended_next_action=run_map_scan_build`.
- `map-update` records useful partial or review state for uncertain coverage rather than failing closed.
- `run_map_scan_build` remains available for missing or unusable baseline recovery.
- Tests prove both the hardline policy and the remaining rebuild exceptions.

## Risks And Mitigations

Risk: The runtime may preserve a stale baseline too aggressively.

Mitigation: Use `partial_refresh`, low-confidence facts, known unknowns, and `minimal_live_reads` so workflows know where live evidence is required.

Risk: Agents may overtrust provisional update data.

Mitigation: Prompt guidance must state that project cognition is advisory and code behavior must be proven from live evidence.

Risk: Truly invalid baseline identity may be hidden as review state.

Mitigation: Keep a separate explicit baseline-identity-invalid condition for broad architecture replacement, but require that condition to be recorded directly instead of inferred from path count alone.
