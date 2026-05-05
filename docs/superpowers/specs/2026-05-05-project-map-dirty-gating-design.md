# Project-Map Dirty Gating Design

**Date:** 2026-05-05  
**Status:** Approved  
**Owner:** Codex

## Summary

This change removes the current `sp-implement` self-lock failure mode caused by
`project-map mark-dirty`, while preserving hard safety gates for new planning
entrypoints and concurrent lane risk.

Today, `mark-dirty` is documented as a manual fallback for cases where a full
atlas refresh cannot be completed in the current pass. In practice, the current
runtime turns that fallback into a blocking state for later `sp-implement`
resumes because project-map freshness is evaluated globally and `implement`
preflight blocks on `stale`.

The approved behavior is:

- same-feature `sp-implement` resume must not be hard blocked solely because the
  current lane previously marked the atlas dirty
- upstream brownfield entrypoints such as `sp-specify`, `sp-plan`, and
  `sp-tasks` must still hard block on dirty/stale atlas state
- `sp-implement` must still hard block when the atlas was dirtied by a
  different feature lane or when no safe ownership match can be established

## Problem

The current status model stores manual stale state globally. It records a dirty
bit and reason set, but not the workflow owner that created the dirty fallback.

That produces an execution contradiction:

1. `sp-implement` changes map-level truth
2. the run cannot complete `sp-map-scan -> sp-map-build -> complete-refresh`
3. `mark-dirty` is used as the documented fallback
4. the next `sp-implement` resume sees global stale state and is blocked before
   it can continue the same lane

This is acceptable as an upstream planning guard but bad as a resumable
implementation contract.

## Goals

- Preserve atlas hard-gate safety for new brownfield planning/execution entry.
- Remove same-lane `sp-implement` self-locking.
- Make dirty fallback ownership explicit enough to reason about multi-lane
  concurrency.
- Keep the first implementation narrow and auditable rather than introducing a
  full module-aware or diff-aware policy engine.

## Non-Goals

- Do not implement module-level or path-level dirty scoping in this change.
- Do not weaken `sp-map-scan -> sp-map-build` as the required atlas refresh
  path.
- Do not silently clear dirty state during `sp-implement` resume.
- Do not make cross-feature concurrent implementation permissive when ownership
  is ambiguous.

## Approved Policy

### 1. Dirty fallback remains global truth, but gains minimal ownership metadata

`project-map mark-dirty` will continue to mark the atlas stale globally, but it
must also be able to record:

- `origin_command`
- `origin_feature_dir`
- `origin_lane_id`

This metadata exists to explain who created the fallback. It does not by itself
clear or reduce the stale state.

### 2. Upstream planning entrypoints stay hard-blocked

These commands must continue to hard block on dirty/stale atlas state:

- `specify`
- `plan`
- `tasks`

Rationale: those commands create or refine truth that depends on trustworthy
atlas context. They are the right place to force a refresh before new work
branches.

### 3. Same-feature implement resume downgrades dirty to warning

`implement` preflight may continue when all of the following are true:

- project-map freshness is `stale` only because of manual dirty fallback
- the dirty origin command is `implement`
- the current `feature_dir` matches the recorded `origin_feature_dir`

In this case, the hook returns `warn`, not `blocked`. The run may resume, but
the stale atlas must still be reported as an outstanding follow-up.

This initial version keys the safe-resume exception on `feature_dir`, not
`lane_id`, because `feature_dir` is always available to current preflight
callers while `lane_id` is not yet passed everywhere.

### 4. Cross-feature implement remains blocked

If `implement` sees dirty/stale atlas state created by another feature, it must
remain blocked.

This is the conservative concurrent-lane choice. Without module-level scoping,
the system cannot safely infer that the dirty atlas change is irrelevant to the
new feature.

### 5. Team auto-dispatch remains hard-blocked on stale atlas

The Codex team/auto-dispatch paths continue to require a fresh atlas. They are
parallel execution accelerators and should not continue under known stale global
knowledge.

## Design Notes

### Why `feature_dir` first instead of `lane_id`

`feature_dir` is already part of `implement` preflight payloads and current
workflow-state/tracker flows. `lane_id` would be a better long-term ownership
key, but adding it everywhere would enlarge the change surface.

The narrow first step is:

- persist both `origin_feature_dir` and `origin_lane_id` when available
- enforce the safe-resume exception using `origin_feature_dir`
- leave lane-aware refinement as a future upgrade

### Why not gate only on `sp-specify`

That is too narrow for multi-lane development. `sp-plan` and `sp-tasks` also
make high-leverage brownfield decisions from atlas truth. A dirty atlas must
block those upstream entrypoints as well.

### Why not allow all implement resumes

Because global dirty state created by feature A is not safely ignorable by
feature B. The current model does not encode enough scope information to permit
that.

## Files Affected

- `src/specify_cli/project_map_status.py`
- `src/specify_cli/hooks/project_map.py`
- `src/specify_cli/hooks/preflight.py`
- `src/specify_cli/__init__.py`
- `templates/commands/implement.md`
- `README.md`
- `PROJECT-HANDBOOK.md`
- `scripts/bash/project-map-freshness.sh`
- `scripts/powershell/project-map-freshness.ps1`
- tests covering hook behavior, CLI behavior, status serialization, and
  template/doc wording

## Acceptance Criteria

- Dirty fallback created during `sp-implement` no longer blocks later resume of
  the same feature's `sp-implement`.
- Dirty fallback still blocks `sp-specify`, `sp-plan`, and `sp-tasks`.
- Dirty fallback created by feature A blocks `sp-implement` for feature B.
- Team auto-dispatch remains blocked on dirty/stale atlas.
- Status serialization preserves backward compatibility with existing flat
  `dirty` / `dirty_reasons` readers.
