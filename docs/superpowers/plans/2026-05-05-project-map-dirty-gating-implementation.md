# Project-Map Dirty Gating Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop `sp-implement` from self-locking on its own `mark-dirty` fallback while preserving hard atlas gates for upstream entrypoints and cross-feature concurrency.

**Architecture:** Extend project-map dirty status with minimal origin metadata, teach preflight to distinguish same-feature `implement` resume from upstream or cross-feature entry, and align CLI/templates/docs/tests to the new contract. Keep the first cut conservative by using `feature_dir` as the safe-resume key and preserving global stale behavior elsewhere.

**Tech Stack:** Python hook/status helpers in `src/specify_cli`, Typer CLI surfaces, bash/powershell project-map helpers, Markdown workflow templates, pytest contract/integration/template tests.

---

## File Structure

```text
MODIFY
  src/specify_cli/project_map_status.py
    Purpose: persist dirty origin metadata and expose freshness output rich enough for preflight decisions.
  src/specify_cli/hooks/project_map.py
    Purpose: accept optional origin metadata on mark-dirty and keep project-map validation semantics centralized.
  src/specify_cli/hooks/preflight.py
    Purpose: allow same-feature implement resume under self-originated dirty fallback; keep upstream and cross-feature blocking.
  src/specify_cli/__init__.py
    Purpose: extend project-map and hook CLI surfaces with optional origin metadata.
  scripts/bash/project-map-freshness.sh
    Purpose: preserve parity for status serialization and helper inspection output.
  scripts/powershell/project-map-freshness.ps1
    Purpose: preserve parity for status serialization and helper inspection output.
  templates/commands/implement.md
    Purpose: explain that same-feature implement resume warns rather than blocks, but upstream/cross-feature work still requires refresh.
  README.md
    Purpose: document the new gating behavior and mark-dirty ownership metadata.
  PROJECT-HANDBOOK.md
    Purpose: align brownfield atlas lifecycle wording with same-feature implement resume behavior.

TESTS TO MODIFY
  tests/test_project_map_status.py
  tests/hooks/test_project_map_hooks.py
  tests/hooks/test_preflight_hooks.py
  tests/hooks/test_hook_engine.py
  tests/integrations/test_cli.py
  tests/test_project_map_freshness_scripts.py
  tests/test_alignment_templates.py
  tests/test_hook_template_guidance.py
  tests/test_command_surface_semantics.py
    Purpose: lock in serialization, hook semantics, CLI shapes, helper parity, and template/docs wording.
```

---

## Task 1: Lock the new behavior with failing tests

**Files:**
- Modify: `tests/hooks/test_preflight_hooks.py`
- Modify: `tests/test_project_map_status.py`
- Modify: `tests/hooks/test_project_map_hooks.py`
- Modify: `tests/integrations/test_cli.py`

- [ ] **Step 1: Add same-feature implement resume coverage**

Update `tests/hooks/test_preflight_hooks.py` with a new test that:

- seeds a dirty project-map status created by `implement`
- records `origin_feature_dir: "specs/001-demo"`
- invokes `workflow.preflight` for `implement` against that same feature dir
- expects `status == "warn"` rather than `blocked`

- [ ] **Step 2: Add cross-feature implement blocking coverage**

In the same test file, add a second test that:

- seeds the same dirty status for `specs/001-demo`
- invokes `workflow.preflight` for `implement` against `specs/002-other`
- expects `status == "blocked"`

- [ ] **Step 3: Add upstream entrypoint blocking coverage**

In `tests/hooks/test_preflight_hooks.py`, add a test proving dirty status still
blocks `specify` (and optionally `plan`/`tasks`) when origin metadata is
present.

- [ ] **Step 4: Add status round-trip coverage for dirty origin metadata**

Update `tests/test_project_map_status.py` so `ProjectMapStatus` round-trips:

- `dirty_origin_command`
- `dirty_origin_feature_dir`
- `dirty_origin_lane_id`

- [ ] **Step 5: Add hook/CLI coverage for origin metadata**

Update hook/CLI tests so `project_map.mark_dirty` and `project-map mark-dirty`
can accept and persist optional origin metadata fields.

- [ ] **Step 6: Run the focused red suite**

Run:

```bash
pytest tests/hooks/test_preflight_hooks.py tests/test_project_map_status.py tests/hooks/test_project_map_hooks.py tests/integrations/test_cli.py -q
```

Expected: FAIL because origin metadata and same-feature resume logic do not yet
exist.

## Task 2: Extend project-map status with dirty origin metadata

**Files:**
- Modify: `src/specify_cli/project_map_status.py`
- Modify: `tests/test_project_map_status.py`

- [ ] **Step 1: Add origin fields to `ProjectMapStatus`**

Persist:

- `global_dirty_origin_command`
- `global_dirty_origin_feature_dir`
- `global_dirty_origin_lane_id`

Expose compatibility accessors if needed.

- [ ] **Step 2: Include origin metadata in `to_dict()` / `from_dict()`**

Keep existing flat compatibility keys intact and add the new origin keys to both
global and legacy-flat payloads.

- [ ] **Step 3: Update `mark_project_map_dirty()` signature**

Allow optional keyword args:

- `origin_command`
- `origin_feature_dir`
- `origin_lane_id`

and persist them when provided.

- [ ] **Step 4: Clear origin metadata on refresh/clear paths**

Ensure `mark_project_map_refreshed()` and `clear_project_map_dirty()` remove the
origin metadata so a fresh atlas does not retain stale ownership markers.

- [ ] **Step 5: Run the status tests**

Run:

```bash
pytest tests/test_project_map_status.py -q
```

Expected: PASS.

## Task 3: Update hook and preflight behavior

**Files:**
- Modify: `src/specify_cli/hooks/project_map.py`
- Modify: `src/specify_cli/hooks/preflight.py`
- Modify: `tests/hooks/test_preflight_hooks.py`
- Modify: `tests/hooks/test_project_map_hooks.py`
- Modify: `tests/hooks/test_hook_engine.py`

- [ ] **Step 1: Accept origin metadata in `mark_dirty_hook()`**

Read optional payload fields and forward them to `mark_project_map_dirty()`.

- [ ] **Step 2: Add implement-safe-resume branch in preflight**

In `workflow_preflight_hook()`:

- inspect freshness payload
- if command is `implement`
- and freshness is stale only because of manual dirty
- and dirty origin command is `implement`
- and current feature dir matches dirty origin feature dir
- downgrade to warning instead of blocking

- [ ] **Step 3: Preserve blocking for upstream and cross-feature entry**

Keep existing blocking semantics for:

- `specify`
- `plan`
- `tasks`
- `implement` with mismatched feature dir

- [ ] **Step 4: Run the hook tests**

Run:

```bash
pytest tests/hooks/test_preflight_hooks.py tests/hooks/test_project_map_hooks.py tests/hooks/test_hook_engine.py -q
```

Expected: PASS.

## Task 4: Extend CLI/helper surfaces and keep shell parity

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Modify: `scripts/bash/project-map-freshness.sh`
- Modify: `scripts/powershell/project-map-freshness.ps1`
- Modify: `tests/integrations/test_cli.py`
- Modify: `tests/test_project_map_freshness_scripts.py`

- [ ] **Step 1: Extend `project-map mark-dirty` CLI**

Add optional flags:

- `--origin-command`
- `--origin-feature-dir`
- `--origin-lane-id`

- [ ] **Step 2: Extend `hook mark-dirty` CLI**

Expose the same optional flags and pass them through to the hook payload.

- [ ] **Step 3: Keep helper output schema aligned**

Update bash/powershell helper writers and readers so status JSON can preserve and
return the new origin metadata fields.

- [ ] **Step 4: Run CLI/helper tests**

Run:

```bash
pytest tests/integrations/test_cli.py tests/test_project_map_freshness_scripts.py -q
```

Expected: PASS.

## Task 5: Align templates and docs

**Files:**
- Modify: `templates/commands/implement.md`
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_hook_template_guidance.py`
- Modify: `tests/test_command_surface_semantics.py`

- [ ] **Step 1: Update implement map-maintenance wording**

Document that:

- same-feature `sp-implement` resume may continue under self-originated dirty
  fallback with warning
- upstream brownfield workflows and other features must refresh before
  continuing

- [ ] **Step 2: Update README / handbook wording**

Clarify that `mark-dirty` is still a fallback, but its blocking behavior depends
on workflow entry type and dirty ownership.

- [ ] **Step 3: Update wording tests**

Adjust template/doc expectations to the new semantics.

- [ ] **Step 4: Run wording tests**

Run:

```bash
pytest tests/test_alignment_templates.py tests/test_hook_template_guidance.py tests/test_command_surface_semantics.py -q
```

Expected: PASS.

## Task 6: Final verification

**Files:**
- Modify: none
- Test: focused full verification set

- [ ] **Step 1: Run the focused verification suite**

Run:

```bash
pytest tests/hooks/test_preflight_hooks.py tests/test_project_map_status.py tests/hooks/test_project_map_hooks.py tests/hooks/test_hook_engine.py tests/integrations/test_cli.py tests/test_project_map_freshness_scripts.py tests/test_alignment_templates.py tests/test_hook_template_guidance.py tests/test_command_surface_semantics.py -q
```

Expected: PASS.

- [ ] **Step 2: Inspect diff before closeout**

Run:

```bash
git diff -- docs/superpowers/specs/2026-05-05-project-map-dirty-gating-design.md docs/superpowers/plans/2026-05-05-project-map-dirty-gating-implementation.md src/specify_cli/project_map_status.py src/specify_cli/hooks/project_map.py src/specify_cli/hooks/preflight.py src/specify_cli/__init__.py scripts/bash/project-map-freshness.sh scripts/powershell/project-map-freshness.ps1 templates/commands/implement.md README.md PROJECT-HANDBOOK.md tests/hooks/test_preflight_hooks.py tests/test_project_map_status.py tests/hooks/test_project_map_hooks.py tests/hooks/test_hook_engine.py tests/integrations/test_cli.py tests/test_project_map_freshness_scripts.py tests/test_alignment_templates.py tests/test_hook_template_guidance.py tests/test_command_surface_semantics.py
```

Expected: only the intended gating, status-schema, docs, and test updates appear.
