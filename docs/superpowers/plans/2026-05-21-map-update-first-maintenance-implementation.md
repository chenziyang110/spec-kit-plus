# Map Update First Maintenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `map-update` the durable maintenance path after an initial usable project cognition baseline, while making `map-scan` and `map-build` produce complete subagent-backed baselines.

**Architecture:** Keep scan/build for baseline creation and structural recovery only. Demote ordinary existing-baseline path gaps to `map-update` review, partial refresh, low-confidence facts, known unknowns, and minimal live reads. Enforce scan/build baseline quality through validation, packet completeness, `subagent_blocked` persistence, and shared Python/bash/PowerShell freshness semantics.

**Tech Stack:** Python 3.11+, Typer CLI, SQLite, pytest, PowerShell, bash, Markdown workflow templates.

---

## Reference Spec

- `docs/superpowers/specs/2026-05-21-map-update-first-maintenance-design.md`

## Implementation Notes

- Human workflow prose may keep `subagent-blocked`; persisted machine fields use `subagent_blocked`.
- User intent uses `explicit_rebuild_requested`; proven architecture-level invalidation uses `baseline_identity_invalid`.
- Missing DB, missing status, missing active generation, unreadable schema, and active generation with zero `path_index` rows are unusable-baseline cases.
- Missing-baseline or no-active-generation update attempts should assert returned payload/status behavior. Do not force an `updates` row when there is no `generation_id`, because `updates.generation_id` is required.

## File Structure

- `src/specify_cli/cognition/path_adoption.py`: classify existing-baseline path gaps as adoptable, review, or unusable-baseline. Remove ordinary count/ratio rebuild heuristics.
- `src/specify_cli/cognition/update.py`: persist review/partial update records, known unknowns, minimal live reads, provisional paths, and status freshness without forcing rebuild for ordinary gaps.
- `src/specify_cli/cognition/query.py`: keep query readiness away from `needs_rebuild` and `unadoptable_path_gap` for ordinary existing-baseline gaps.
- `src/specify_cli/project_cognition_status.py`: central freshness `recommended_next_action` logic for Python callers.
- `src/specify_cli/hooks/project_cognition.py`: hook/preflight guidance for stale, partial, path-gap, explicit rebuild, and structural invalidation states.
- `src/specify_cli/cognition/validation.py`: `validate-scan` and `validate-build` enforcement for packet completeness, open gaps, reverse coverage, and `subagent_blocked`.
- `src/specify_cli/hooks/artifact_validation.py`: hook-facing map-scan/map-build artifact validation that delegates to cognition validation.
- `src/specify_cli/__init__.py`: CLI rendering for preflight/freshness guidance.
- `scripts/bash/project-map-freshness.sh`: standalone bash freshness semantics.
- `scripts/powershell/project-map-freshness.ps1`: standalone PowerShell freshness semantics.
- `templates/commands/map-update.md`: workflow contract for incremental update handling.
- `templates/commands/map-scan.md`: subagent-backed scan baseline contract.
- `templates/commands/map-build.md`: packet-consuming build baseline contract.
- `templates/command-partials/map-scan/shell.md`: shell guidance for scan acceptance.
- `templates/command-partials/map-build/shell.md`: shell guidance for build acceptance.
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`: passive guidance for map maintenance routing.
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`: generated workflow routing.
- `src/specify_cli/integrations/base.py` and `src/specify_cli/integrations/cursor_agent/__init__.py`: generated integration addenda that embed map-maintenance guidance.
- `README.md` and `PROJECT-HANDBOOK.md`: user-facing lifecycle docs.
- Tests: `tests/test_project_cognition_path_adoption.py`, `tests/test_project_cognition_db.py`, `tests/test_project_cognition_query.py`, `tests/test_project_map_status.py`, `tests/test_project_map_freshness_scripts.py`, `tests/test_project_cognition_validation.py`, `tests/contract/test_hook_cli_surface.py`, `tests/test_map_scan_build_template_guidance.py`, `tests/test_map_runtime_template_guidance.py`, `tests/test_alignment_templates.py`, `tests/test_specify_guidance_docs.py`, and affected integration tests.

---

### Task 1: Demote Ordinary Path Coverage Gaps To Review

**Files:**
- Modify: `tests/test_project_cognition_path_adoption.py`
- Modify: `src/specify_cli/cognition/path_adoption.py`

- [ ] **Step 1: Update failing path-adoption tests**

In `tests/test_project_cognition_path_adoption.py`, replace the current unadoptable expectations for large unrelated paths, core surfaces, and package manifests with review expectations:

```python
def test_classifies_many_unrelated_missing_paths_as_review(tmp_path: Path) -> None:
    generation_id = _seed_indexed_path(tmp_path)
    missing_paths = [f"new_system_{index}/entry.py" for index in range(26)]

    with closing(connect_cognition_db(tmp_path)) as conn:
        result = classify_path_coverage(
            conn,
            generation_id,
            missing_paths=missing_paths,
            requested_paths=missing_paths,
        )

    assert result.query_coverage == "uncertain_path_gap"
    assert result.recommended_next_action == "perform_minimal_live_reads"
    assert result.adoptable_paths == []
    assert result.review_paths == missing_paths
    assert result.unadoptable_paths == []
    assert any("more than 25" in reason for reason in result.reasons)


def test_core_surface_without_indexed_sibling_requires_review(tmp_path: Path) -> None:
    generation_id = _seed_indexed_path(tmp_path)

    with closing(connect_cognition_db(tmp_path)) as conn:
        result = classify_path_coverage(
            conn,
            generation_id,
            missing_paths=["scripts/release/package.ps1"],
            requested_paths=["scripts/release/package.ps1"],
        )

    assert result.query_coverage == "uncertain_path_gap"
    assert result.recommended_next_action == "perform_minimal_live_reads"
    assert result.adoptable_paths == []
    assert result.review_paths == ["scripts/release/package.ps1"]
    assert result.unadoptable_paths == []
    assert any("core live surface" in reason for reason in result.reasons)


def test_package_manifest_without_indexed_sibling_requires_review(tmp_path: Path) -> None:
    generation_id = _seed_indexed_path(tmp_path)

    with closing(connect_cognition_db(tmp_path)) as conn:
        result = classify_path_coverage(
            conn,
            generation_id,
            missing_paths=["package.json"],
            requested_paths=["package.json"],
        )

    assert result.query_coverage == "uncertain_path_gap"
    assert result.recommended_next_action == "perform_minimal_live_reads"
    assert result.review_paths == ["package.json"]
    assert result.unadoptable_paths == []
```

- [ ] **Step 2: Add the unusable zero-path-index test**

Add this test to the same file:

```python
def test_active_generation_without_indexed_paths_is_unusable(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)
    generation_id = seed_active_generation(tmp_path, source_commit="abc123")

    with closing(connect_cognition_db(tmp_path)) as conn:
        result = classify_path_coverage(
            conn,
            generation_id,
            missing_paths=["src/auth/session.ts"],
            requested_paths=["src/auth/session.ts"],
        )

    assert result.query_coverage == "unadoptable_path_gap"
    assert result.recommended_next_action == "run_map_scan_build"
    assert result.unadoptable_paths == ["src/auth/session.ts"]
    assert result.reasons == ["active generation has no path_index rows to adopt from"]
```

- [ ] **Step 3: Run the targeted tests and verify failure**

Run:

```powershell
pytest tests/test_project_cognition_path_adoption.py -q
```

Expected: the updated review tests fail because current code still returns `unadoptable_path_gap` and `run_map_scan_build`.

- [ ] **Step 4: Replace rebuild heuristics with review reasons**

In `src/specify_cli/cognition/path_adoption.py`, remove these rebuild constants because ordinary counts and ratios no longer trigger rebuild:

```python
UNCLASSIFIED_REBUILD_LIMIT = 25
UNRELATED_TOP_LEVEL_REBUILD_LIMIT = 3
UNADOPTABLE_RATIO_REBUILD_THRESHOLD = 0.40
```

Replace the core-surface branch in `classify_path_coverage()` with:

```python
        elif _is_core_live_surface(path):
            uncertain_paths.append(path)
            reasons.append(f"core live surface path needs review before adoption: {path}")
```

Replace the `_rebuild_reasons()` call and branch with review reasons:

```python
    review_reasons = _review_reasons(
        missing_paths=normalized_missing_paths,
        indexed_paths=indexed_paths,
        uncertain_paths=uncertain_paths,
    )

    if uncertain_paths:
        return PathCoverageClassification(
            query_coverage="uncertain_path_gap",
            recommended_next_action="perform_minimal_live_reads",
            adoptable_paths=adoptable_paths,
            review_paths=uncertain_paths,
            reasons=[*reasons, *review_reasons],
        )
```

Replace `_rebuild_reasons()` with:

```python
def _review_reasons(
    *,
    missing_paths: Sequence[str],
    indexed_paths: Sequence[IndexedPathRecord],
    uncertain_paths: Sequence[str],
) -> list[str]:
    reasons: list[str] = []
    if len(uncertain_paths) > REVIEW_LIMIT:
        reasons.append(f"more than {REVIEW_LIMIT} uncertain missing paths need review")
    if len(uncertain_paths) > 25:
        reasons.append("more than 25 missing paths are unclassified")

    unrelated_top_levels = _unrelated_top_level_count(missing_paths, indexed_paths)
    if unrelated_top_levels > 3:
        reasons.append("more than 3 unrelated top-level live-surface directories are missing")

    return reasons
```

Delete the later `if unadoptable_paths:` branch unless it is still reachable after the zero-index early return. If kept for defensive compatibility, make it return `uncertain_path_gap` with `review_paths=unadoptable_paths`.

- [ ] **Step 5: Run the targeted tests and commit**

Run:

```powershell
pytest tests/test_project_cognition_path_adoption.py -q
```

Expected: all tests in `tests/test_project_cognition_path_adoption.py` pass.

Commit:

```powershell
git add src/specify_cli/cognition/path_adoption.py tests/test_project_cognition_path_adoption.py
git commit -m "fix(cognition): demote ordinary path gaps to review"
```

---

### Task 2: Persist Map-Update Review State Instead Of Rebuild State

**Files:**
- Modify: `tests/test_project_cognition_db.py`
- Modify: `src/specify_cli/cognition/update.py`

- [ ] **Step 1: Replace core-surface rebuild update test**

In `tests/test_project_cognition_db.py`, replace `test_apply_cognition_update_routes_unadoptable_core_surface_to_rebuild` with:

```python
def test_apply_cognition_update_routes_core_surface_gap_to_review(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)
    generation_id = seed_active_generation(tmp_path, source_commit="abc123")
    with closing(connect_cognition_db(tmp_path)) as conn:
        conn.execute(
            "INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) "
            "VALUES ('E-update', ?, 'file', 'src/auth/login.ts', 'abc123', '1-80', 'test', 'old', '2026-05-13T00:00:00Z', '{}')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('capability:auth.login', ?, 'capability', 'User login', 'strong', '{}', '2026-05-13T00:00:00Z', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) "
            "VALUES ('P-update', ?, 'src/auth/login.ts', 'capability:auth.login', 'implements', 'strong', 'E-update', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.commit()

    result = apply_cognition_update(
        tmp_path,
        changed_paths=["scripts/release/package.ps1"],
        reason="unit-test",
    )

    assert result["readiness"] == "review"
    assert result["recommended_next_action"] == "perform_minimal_live_reads"
    assert result["adopted_paths"] == []
    assert result["review_paths"] == ["scripts/release/package.ps1"]
    assert result["unadoptable_paths"] == []
    assert result["minimal_live_reads"] == ["scripts/release/package.ps1"]
    assert result["missing_coverage"] == [
        "path requires minimal live read before adoption: scripts/release/package.ps1"
    ]
    assert result["known_unknowns"] == [
        "path requires minimal live read before adoption: scripts/release/package.ps1"
    ]
    with closing(connect_cognition_db(tmp_path)) as conn:
        row = conn.execute("SELECT path FROM path_index WHERE path = 'scripts/release/package.ps1'").fetchone()
        update_row = conn.execute("SELECT result_state, attrs_json FROM updates").fetchone()
    assert row is None
    assert update_row["result_state"] == "review"
    attrs = json.loads(update_row["attrs_json"])
    assert attrs["path_adoption"]["query_coverage"] == "uncertain_path_gap"
    assert attrs["path_adoption"]["review_paths"] == ["scripts/release/package.ps1"]
    assert attrs["path_adoption"]["unadoptable_paths"] == []
    assert attrs["known_unknowns"] == [
        "path requires minimal live read before adoption: scripts/release/package.ps1"
    ]
    assert attrs["minimal_live_reads"] == ["scripts/release/package.ps1"]
    assert attrs["confidence"] == "weak"
    status = read_cognition_status(tmp_path)
    assert status.baseline_state == "ready"
    assert status.freshness == "possibly_stale"
    assert status.stale_paths == ["scripts/release/package.ps1"]
    assert status.stale_reasons == [
        "path requires minimal live read before adoption: scripts/release/package.ps1"
    ]
    assert status.dirty_reasons == []
    assert status.dirty_origin_command == ""
```

- [ ] **Step 2: Add no-active-generation update-row guard test**

Add this assertion to `test_apply_cognition_update_without_active_generation_includes_empty_update_id`:

```python
    with closing(connect_cognition_db(tmp_path)) as conn:
        update_count = conn.execute("SELECT COUNT(*) AS count FROM updates").fetchone()["count"]

    assert update_count == 0
```

- [ ] **Step 3: Run the targeted test and verify failure**

Run:

```powershell
pytest tests/test_project_cognition_db.py::test_apply_cognition_update_routes_core_surface_gap_to_review tests/test_project_cognition_db.py::test_apply_cognition_update_without_active_generation_includes_empty_update_id -q
```

Expected: the core-surface test fails until Task 1 and update persistence changes are complete.

- [ ] **Step 4: Update persistence helper names and reasons**

In `src/specify_cli/cognition/update.py`, keep `_result_state_for_update()` returning `review` for `uncertain_path_gap`. Update `_missing_coverage_for_gaps()` so ordinary review paths produce the only missing-coverage reason for core surfaces:

```python
def _missing_coverage_for_gaps(
    *,
    review_paths: list[str],
    unadoptable_paths: list[str],
) -> list[str]:
    return [
        *[
            f"path requires minimal live read before adoption: {path}"
            for path in review_paths
        ],
        *[
            f"path not safely adoptable by project cognition index: {path}"
            for path in unadoptable_paths
        ],
    ]
```

Replace prior-unadoptable guard usage with scan/build reason tokens:

```python
SCAN_BUILD_REASON_TOKENS = {
    "baseline_identity_invalid",
    "explicit_rebuild_requested",
}


def _has_scan_build_allowed_reason(reasons: list[str]) -> bool:
    reason_text = " ".join(str(reason or "") for reason in reasons).lower()
    compact_reason_text = reason_text.replace("-", "_").replace(" ", "_")
    return any(token in compact_reason_text for token in SCAN_BUILD_REASON_TOKENS)
```

Use `_has_scan_build_allowed_reason()` where the current code uses `_has_prior_unadoptable_path_gap`. Keep no-active-generation behavior returning `needs_rebuild` with an empty `update_id`.

- [ ] **Step 5: Run update persistence tests and commit**

Run:

```powershell
pytest tests/test_project_cognition_db.py -q
```

Expected: all project cognition DB tests pass after updating expectations affected by the new review policy.

Commit:

```powershell
git add src/specify_cli/cognition/update.py tests/test_project_cognition_db.py
git commit -m "fix(cognition): persist update review gaps"
```

---

### Task 3: Align Query Readiness And Python Freshness Recommendations

**Files:**
- Modify: `tests/test_project_cognition_query.py`
- Modify: `tests/test_project_map_status.py`
- Modify: `src/specify_cli/cognition/query.py`
- Modify: `src/specify_cli/project_cognition_status.py`
- Modify: `src/specify_cli/hooks/project_cognition.py`
- Modify: `src/specify_cli/__init__.py`
- Modify: `tests/contract/test_hook_cli_surface.py`
- Modify: `tests/test_project_map_hard_gate_guidance.py`

- [ ] **Step 1: Update query tests for existing-baseline ordinary gaps**

In `tests/test_project_cognition_query.py`, replace `test_query_routes_unadoptable_core_surface_gap_to_rebuild` with:

```python
def test_query_routes_core_surface_gap_to_update_review(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    result = query_project_cognition(
        tmp_path,
        intent="planning_or_implementation",
        query_text="release package script",
        paths=["scripts/release/package.ps1"],
        selected_concepts=[],
        rejected_concepts=[],
        selection_reason="path-specific request",
    )

    assert result["query_coverage"] == "uncertain_path_gap"
    assert result["readiness"] == "needs_update"
    assert result["recommended_next_action"] == "run_map_update"
    assert result["path_adoption"]["review_paths"] == ["scripts/release/package.ps1"]
    assert result["path_adoption"]["unadoptable_paths"] == []
    assert result["minimal_live_reads"] == ["scripts/release/package.ps1"]
```

Keep the missing DB and no active generation tests expecting `needs_rebuild` and `run_map_scan_build`.

- [ ] **Step 2: Update freshness status tests**

In `tests/test_project_map_status.py`, replace tests that route path-index dirty gaps or unadoptable coverage reasons to scan/build. Use these expectations:

```python
def test_assess_project_map_freshness_routes_path_index_dirty_gap_to_map_update(tmp_path):
    status = ProjectMapStatus(
        freshness="stale",
        last_mapped_commit="abc123",
        dirty=True,
        dirty_reasons=["58 changed paths missing from project cognition path_index"],
    )
    write_project_map_status(tmp_path, status)

    result = assess_project_map_freshness(
        tmp_path,
        head_commit="def456",
        changed_files=[],
        has_git=True,
    )

    assert result["recommended_next_action"] == "run_map_update"
```

Add explicit token tests:

```python
def test_assess_project_map_freshness_routes_explicit_rebuild_token_to_scan_build(tmp_path):
    status = ProjectMapStatus(
        freshness="stale",
        last_mapped_commit="abc123",
        dirty=True,
        dirty_reasons=["explicit_rebuild_requested"],
    )
    write_project_map_status(tmp_path, status)

    result = assess_project_map_freshness(
        tmp_path,
        head_commit="def456",
        changed_files=[],
        has_git=True,
    )

    assert result["recommended_next_action"] == "run_map_scan_build"


def test_assess_project_map_freshness_routes_baseline_identity_invalid_to_scan_build(tmp_path):
    status = ProjectMapStatus(
        freshness="stale",
        last_mapped_commit="abc123",
        dirty=True,
        dirty_reasons=["baseline_identity_invalid"],
    )
    write_project_map_status(tmp_path, status)

    result = assess_project_map_freshness(
        tmp_path,
        head_commit="def456",
        changed_files=[],
        has_git=True,
    )

    assert result["recommended_next_action"] == "run_map_scan_build"
```

- [ ] **Step 3: Run targeted query and status tests**

Run:

```powershell
pytest tests/test_project_cognition_query.py tests/test_project_map_status.py -q
```

Expected: tests fail where current code maps unadoptable/path-gap reasons to `run_map_scan_build`.

- [ ] **Step 4: Update query readiness mapping**

In `src/specify_cli/cognition/query.py`, keep this behavior:

```python
def _readiness_for_path_coverage(classification: PathCoverageClassification, workflow_requirement: str) -> str:
    if classification.query_coverage == "covered":
        return "ready"
    if classification.query_coverage == "unadoptable_path_gap":
        return "needs_rebuild"
    if classification.query_coverage == "adoptable_path_gap":
        return "needs_update"
    if classification.query_coverage == "uncertain_path_gap":
        return "review" if workflow_requirement == "discussion" else "needs_update"
    return "review"
```

After Task 1, ordinary existing-baseline gaps should arrive as `uncertain_path_gap`, not `unadoptable_path_gap`.

- [ ] **Step 5: Replace Python freshness scan/build heuristic**

In `src/specify_cli/project_cognition_status.py`, replace `_has_unadoptable_path_index_gap_reason()` with:

```python
SCAN_BUILD_ALLOWED_REASON_TOKENS = {
    "baseline_identity_invalid",
    "explicit_rebuild_requested",
}


def _has_scan_build_allowed_reason(reasons: list[str]) -> bool:
    reason_text = " ".join(str(reason or "") for reason in reasons).lower()
    compact_reason_text = reason_text.replace("-", "_").replace(" ", "_")
    return any(token in compact_reason_text for token in SCAN_BUILD_ALLOWED_REASON_TOKENS)
```

Update `recommended_next_action_for_freshness()`:

```python
def recommended_next_action_for_freshness(*, freshness: str, reasons: list[str]) -> str:
    normalized = str(freshness or "").strip().lower()
    reason_text = " ".join(str(reason or "") for reason in reasons).lower()
    if normalized == FRESHNESS_MISSING_STATE:
        return NEXT_ACTION_MAP_SCAN_BUILD
    if normalized == FRESHNESS_RUNTIME_STALE_STATE:
        if _has_scan_build_allowed_reason(reasons):
            return NEXT_ACTION_MAP_SCAN_BUILD
        return NEXT_ACTION_MAP_UPDATE
    if normalized == FRESHNESS_SUPPORT_DRIFT_STATE:
        if "policy" in reason_text:
            return NEXT_ACTION_POLICY
        return NEXT_ACTION_SUPPORT
    if normalized == FRESHNESS_PARTIAL_REFRESH_STATE:
        return NEXT_ACTION_MAP_UPDATE
    if normalized == FRESHNESS_POSSIBLY_STALE_STATE:
        return NEXT_ACTION_MAP_UPDATE
    return NEXT_ACTION_RETRY
```

- [ ] **Step 6: Update hook and CLI copy**

In `src/specify_cli/hooks/project_cognition.py`, change `PATH_INDEX_STALE_FALLBACK_GUIDANCE` so it recommends `sp-map-update` first and mentions scan/build only for explicit rebuild, baseline identity invalidation, or unusable baseline:

```python
PATH_INDEX_STALE_FALLBACK_GUIDANCE = (
    "project cognition runtime freshness is stale because changed paths are missing from path_index; "
    "run /sp-map-update first so ordinary gaps can receive provisional coverage, review state, known unknowns, "
    "and minimal live reads; rebuild through /sp-map-scan -> /sp-map-build only for missing or unusable baseline, "
    "explicit_rebuild_requested, or baseline_identity_invalid"
)
```

In `_render_project_map_preflight_guidance()` in `src/specify_cli/__init__.py`, update the `run_map_scan_build` branch to say scan/build is only for missing or unusable baseline, `explicit_rebuild_requested`, or `baseline_identity_invalid`. The path-gap branch should print `Run /sp-map-update`.

- [ ] **Step 7: Update hook/preflight tests and commit**

Run:

```powershell
pytest tests/test_project_cognition_query.py tests/test_project_map_status.py tests/test_project_map_hard_gate_guidance.py tests/contract/test_hook_cli_surface.py::test_project_map_preflight_path_index_gap_routes_to_scan_build -q
```

Expected: update the contract test name to `test_project_map_preflight_path_index_gap_routes_to_map_update`; it should assert no `sp-map-scan` or `sp-map-build` in the path-gap guidance.

Commit:

```powershell
git add src/specify_cli/cognition/query.py src/specify_cli/project_cognition_status.py src/specify_cli/hooks/project_cognition.py src/specify_cli/__init__.py tests/test_project_cognition_query.py tests/test_project_map_status.py tests/test_project_map_hard_gate_guidance.py tests/contract/test_hook_cli_surface.py
git commit -m "fix(cognition): reserve rebuild recommendations for explicit reasons"
```

---

### Task 4: Align Bash And PowerShell Freshness Scripts

**Files:**
- Modify: `scripts/bash/project-map-freshness.sh`
- Modify: `scripts/powershell/project-map-freshness.ps1`
- Modify: `tests/test_project_map_freshness_scripts.py`

- [ ] **Step 1: Update script tests for path gaps and explicit tokens**

In `tests/test_project_map_freshness_scripts.py`, rename script tests that route unadoptable path gaps to scan/build so they expect `run_map_update`. Add explicit token tests for both bash and PowerShell:

```python
def test_bash_mark_dirty_routes_explicit_rebuild_token_to_scan_build(git_repo: Path):
    _run_bash(git_repo, "record-refresh", "map-build")
    result = _run_bash(git_repo, "mark-dirty", "explicit_rebuild_requested")

    assert result["recommended_next_action"] == "run_map_scan_build"


def test_bash_mark_dirty_routes_baseline_identity_invalid_to_scan_build(git_repo: Path):
    _run_bash(git_repo, "record-refresh", "map-build")
    result = _run_bash(git_repo, "mark-dirty", "baseline_identity_invalid")

    assert result["recommended_next_action"] == "run_map_scan_build"


def test_powershell_mark_dirty_routes_explicit_rebuild_token_to_scan_build(git_repo: Path):
    _run_powershell(git_repo, "record-refresh", "map-build")
    result = _run_powershell(git_repo, "mark-dirty", "explicit_rebuild_requested")

    assert result["recommended_next_action"] == "run_map_scan_build"


def test_powershell_mark_dirty_routes_baseline_identity_invalid_to_scan_build(git_repo: Path):
    _run_powershell(git_repo, "record-refresh", "map-build")
    result = _run_powershell(git_repo, "mark-dirty", "baseline_identity_invalid")

    assert result["recommended_next_action"] == "run_map_scan_build"
```

For path-index gap reasons such as `58 changed paths missing from project cognition path_index`, assert:

```python
assert result["recommended_next_action"] == "run_map_update"
```

- [ ] **Step 2: Run script tests and verify failure**

Run:

```powershell
pytest tests/test_project_map_freshness_scripts.py -q
```

Expected: script tests fail because current bash/PowerShell helpers still route unadoptable/path count reasons to scan/build.

- [ ] **Step 3: Update bash helper**

In `scripts/bash/project-map-freshness.sh`, replace `path_gap_requires_rebuild()` with:

```bash
scan_build_allowed_reason() {
    local reasons="${1:-}"
    local normalized_reasons
    normalized_reasons="$(printf '%s' "$reasons" | tr '[:upper:]' '[:lower:]' | sed -E 's/[-[:space:]]+/_/g')"

    if [[ "$normalized_reasons" == *"baseline_identity_invalid"* ]]; then
        return 0
    fi
    if [[ "$normalized_reasons" == *"explicit_rebuild_requested"* ]]; then
        return 0
    fi
    return 1
}
```

Replace calls to `path_gap_requires_rebuild` with `scan_build_allowed_reason`.

- [ ] **Step 4: Update PowerShell helper**

In `scripts/powershell/project-map-freshness.ps1`, replace the path-gap rebuild helper with:

```powershell
function Test-ScanBuildAllowedReason {
    param([string]$Reasons)
    $normalizedReasonText = (($Reasons ?? '').ToLowerInvariant() -replace '[-\s]+', '_')
    return (
        $normalizedReasonText.Contains('baseline_identity_invalid') -or
        $normalizedReasonText.Contains('explicit_rebuild_requested')
    )
}
```

Replace calls to the previous unadoptable path-gap helper with `Test-ScanBuildAllowedReason`.

- [ ] **Step 5: Run script tests and commit**

Run:

```powershell
pytest tests/test_project_map_freshness_scripts.py -q
```

Expected: all script freshness tests pass.

Commit:

```powershell
git add scripts/bash/project-map-freshness.sh scripts/powershell/project-map-freshness.ps1 tests/test_project_map_freshness_scripts.py
git commit -m "fix(cognition): align shell freshness rebuild reasons"
```

---

### Task 5: Enforce Scan/Build Coverage And subagent_blocked Validation

**Files:**
- Modify: `tests/test_project_cognition_validation.py`
- Modify: `tests/contract/test_hook_cli_surface.py`
- Modify: `src/specify_cli/cognition/validation.py`
- Modify: `src/specify_cli/hooks/artifact_validation.py`

- [ ] **Step 1: Add validation tests for open-gap states**

In `tests/test_project_cognition_validation.py`, add these tests near the existing scan validation open-gap tests:

```python
def test_validate_scan_blocks_important_open_gaps(tmp_path: Path) -> None:
    _write_complete_scan_package(tmp_path)
    _write_json(
        tmp_path / ".specify" / "project-cognition" / "workbench" / "coverage-ledger.json",
        {
            "version": 1,
            "rows": [
                {
                    "path": "src/payments/service.py",
                    "criticality": "important",
                    "coverage_state": "unknown",
                }
            ],
            "open_gaps": [
                {
                    "criticality": "important",
                    "reason": "owner unavailable",
                    "owner": "map-scan",
                    "revisit_condition": "owner confirms payment service boundaries",
                }
            ],
        },
    )

    result = validate_scan_acceptance(tmp_path)

    assert result["status"] == "blocked"
    assert any("important" in message.lower() for message in result["errors"])


def test_validate_scan_blocks_subagent_blocked_open_gap(tmp_path: Path) -> None:
    _write_complete_scan_package(tmp_path)
    _write_json(
        tmp_path / ".specify" / "project-cognition" / "workbench" / "coverage-ledger.json",
        {
            "version": 1,
            "rows": [
                {
                    "path": "src/auth/login.ts",
                    "criticality": "critical",
                    "coverage_state": "blocked",
                }
            ],
            "open_gaps": [
                {
                    "reason": "subagent_blocked",
                    "lane_id": "scan-auth",
                    "packet_id": "packet-auth",
                    "blocked_scope": ["src/auth"],
                    "criticality": "critical",
                    "owner": "map-scan",
                    "status": "blocked",
                    "recovery_condition": "rerun scan-auth packet with native subagent dispatch",
                }
            ],
        },
    )

    result = validate_scan_acceptance(tmp_path)

    assert result["status"] == "blocked"
    assert any("subagent_blocked" in message for message in result["errors"])


def test_validate_scan_accepts_low_risk_open_gap_with_required_metadata(tmp_path: Path) -> None:
    _write_complete_scan_package(tmp_path)
    _write_json(
        tmp_path / ".specify" / "project-cognition" / "workbench" / "coverage-ledger.json",
        {
            "version": 1,
            "rows": [
                {
                    "path": "docs/archive/old-note.md",
                    "criticality": "low-risk",
                    "coverage_state": "low_risk_open_gap",
                }
            ],
            "open_gaps": [
                {
                    "criticality": "low-risk",
                    "reason": "archived reference only",
                    "owner": "map-scan",
                    "evidence_expectation": "no runtime behavior expected",
                    "revisit_condition": "file becomes linked from active docs",
                    "status": "open",
                }
            ],
        },
    )

    result = validate_scan_acceptance(tmp_path)

    assert result["status"] == "ok"
    assert any("non-critical open gaps" in message for message in result["warnings"])
```

- [ ] **Step 2: Add artifact-validation contract test**

In `tests/contract/test_hook_cli_surface.py`, add a map-scan artifact validation test that writes a `coverage-ledger.json` with `reason="subagent_blocked"` and asserts the hook blocks:

```python
def test_map_scan_artifact_validation_blocks_subagent_blocked_gap(tmp_path: Path):
    run_dir = tmp_path / ".specify" / "project-cognition"
    _write_project_cognition_scan_artifacts(run_dir)
    (run_dir / "workbench" / "coverage-ledger.json").write_text(
        json.dumps(
            {
                "version": 1,
                "rows": [
                    {
                        "path": "src/auth/login.ts",
                        "criticality": "critical",
                        "coverage_state": "blocked",
                    }
                ],
                "open_gaps": [
                    {
                        "reason": "subagent_blocked",
                        "lane_id": "scan-auth",
                        "packet_id": "packet-auth",
                        "blocked_scope": ["src/auth"],
                        "criticality": "critical",
                        "owner": "map-scan",
                        "status": "blocked",
                        "recovery_condition": "rerun scan-auth packet",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["hook", "validate-artifacts", "--command", "map-scan", "--feature-dir", str(run_dir)],
        catch_exceptions=False,
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert any("subagent_blocked" in message for message in payload["errors"])
```

- [ ] **Step 3: Run validation tests and verify failure**

Run:

```powershell
pytest tests/test_project_cognition_validation.py tests/contract/test_hook_cli_surface.py::test_map_scan_artifact_validation_blocks_subagent_blocked_gap -q
```

Expected: tests fail until validation recognizes important gaps, low-risk metadata, and `subagent_blocked`.

- [ ] **Step 4: Update scan acceptance validation**

In `src/specify_cli/cognition/validation.py`, add constants near validation helpers:

```python
ACCEPTED_COVERAGE_STATES = {"accepted", "complete", "covered", "excluded", "low_risk_open_gap"}
BLOCKING_CRITICALITIES = {"critical", "important"}
LOW_RISK_CRITICALITIES = {"low-risk", "low_risk"}
REQUIRED_LOW_RISK_GAP_FIELDS = ("owner", "reason", "evidence_expectation", "revisit_condition")
REQUIRED_SUBAGENT_BLOCKED_FIELDS = (
    "reason",
    "lane_id",
    "packet_id",
    "blocked_scope",
    "criticality",
    "owner",
    "status",
    "recovery_condition",
)
```

Update `_check_unresolved_scan_gaps()` so critical and important rows block unless covered/excluded:

```python
    unresolved_blocking_rows = [
        row
        for row in rows
        if isinstance(row, dict)
        and str(row.get("criticality", "")).lower() in BLOCKING_CRITICALITIES
        and str(row.get("coverage_state", row.get("state", ""))).lower() not in ACCEPTED_COVERAGE_STATES
    ]
    if unresolved_blocking_rows:
        errors.append("coverage-ledger.json has unresolved critical or important rows")
```

Inside open gap loop:

```python
        reason = str(gap.get("reason", "")).strip().lower()
        status = str(gap.get("status", "")).strip().lower()
        if reason == "subagent_blocked" or status == "blocked":
            missing = [field for field in REQUIRED_SUBAGENT_BLOCKED_FIELDS if not gap.get(field)]
            if missing:
                errors.append(
                    f"coverage-ledger.json subagent_blocked open gap {index} is missing required metadata: {', '.join(missing)}"
                )
            else:
                errors.append("coverage-ledger.json has subagent_blocked open gaps")
            continue

        if criticality in BLOCKING_CRITICALITIES:
            errors.append("coverage-ledger.json has unresolved critical or important open gaps")
            continue

        if criticality in LOW_RISK_CRITICALITIES:
            missing_metadata = [
                field
                for field in REQUIRED_LOW_RISK_GAP_FIELDS
                if not str(gap.get(field, "")).strip()
            ]
            if missing_metadata:
                errors.append(
                    f"coverage-ledger.json low-risk open gap {index} is missing required metadata: {', '.join(missing_metadata)}"
                )
                continue
            valid_noncritical_count += 1
            continue
```

- [ ] **Step 5: Run validation tests and commit**

Run:

```powershell
pytest tests/test_project_cognition_validation.py tests/contract/test_hook_cli_surface.py -q
```

Expected: cognition validation tests and hook artifact contract tests pass.

Commit:

```powershell
git add src/specify_cli/cognition/validation.py src/specify_cli/hooks/artifact_validation.py tests/test_project_cognition_validation.py tests/contract/test_hook_cli_surface.py
git commit -m "fix(cognition): enforce scan coverage gaps"
```

---

### Task 6: Update Workflow Templates, Passive Skills, And Documentation

**Files:**
- Modify: `templates/commands/map-update.md`
- Modify: `templates/commands/map-scan.md`
- Modify: `templates/commands/map-build.md`
- Modify: `templates/command-partials/map-scan/shell.md`
- Modify: `templates/command-partials/map-build/shell.md`
- Modify: `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `src/specify_cli/integrations/cursor_agent/__init__.py`
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `tests/test_map_scan_build_template_guidance.py`
- Modify: `tests/test_map_runtime_template_guidance.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_specify_guidance_docs.py`
- Modify: affected `tests/integrations/test_integration_*` files

- [ ] **Step 1: Add template tests for map-update-first semantics**

In `tests/test_map_runtime_template_guidance.py`, add:

```python
def test_map_update_template_handles_existing_baseline_gaps_without_rebuild():
    content = _read("templates/commands/map-update.md").lower()

    assert "existing-baseline ordinary gaps" in content
    assert "partial_refresh" in content
    assert "minimal_live_reads" in content
    assert "baseline_identity_invalid" in content
    assert "explicit_rebuild_requested" in content
    assert "path count" in content
    assert "must not route to `{{invoke:map-scan}}`, then `{{invoke:map-build}}` for ordinary path gaps" in content
```

In `tests/test_map_scan_build_template_guidance.py`, add:

```python
def test_map_scan_build_templates_require_subagent_blocked_persistence() -> None:
    scan_content = _read("templates/commands/map-scan.md").lower()
    build_content = _read("templates/commands/map-build.md").lower()

    for content in (scan_content, build_content):
        assert "subagent_blocked" in content
        assert "coverage-ledger.json.open_gaps" in content
        assert "map-state.md" in content
        assert "low_risk_open_gap" in content
        assert "unknown` blocks" in content
```

- [ ] **Step 2: Run template tests and verify failure**

Run:

```powershell
pytest tests/test_map_runtime_template_guidance.py tests/test_map_scan_build_template_guidance.py -q
```

Expected: new tests fail until templates are updated.

- [ ] **Step 3: Update map-update template**

In `templates/commands/map-update.md`, add a section named `Existing-Baseline Gap Policy` with this text:

```markdown
## Existing-Baseline Gap Policy

When a usable active generation exists, ordinary changed-path gaps are `sp-map-update`
work. Do not route to `{{invoke:map-scan}}`, then `{{invoke:map-build}}` for
ordinary path gaps, path count, unrelated top-level count, core-surface status,
weak ownership, missing `path_index` coverage, or unadoptable-ratio heuristics.

Use `review`, `partial_refresh`, low-confidence claims, conflicts, stale claims,
known unknowns, and `minimal_live_reads` to preserve imperfect but useful
maintenance state.

`{{invoke:map-scan}} -> {{invoke:map-build}}` is allowed after an existing baseline
only for missing or unusable runtime, zero active-generation `path_index` rows,
schema failure, `explicit_rebuild_requested`, or `baseline_identity_invalid`.
```

- [ ] **Step 4: Update map-scan and map-build templates**

In both `templates/commands/map-scan.md` and `templates/commands/map-build.md`, add a `Machine-Readable Blocked State` subsection:

```markdown
## Machine-Readable Blocked State

Human workflow prose may say `subagent-blocked`, but persisted machine fields use
`subagent_blocked`.

If a substantive scan/build lane cannot dispatch or complete, write:

- `.specify/project-cognition/status.json` with `baseline_state=blocked` and
  `subagent_blocked` in `stale_reasons` or `dirty_reasons`
- `.specify/project-cognition/workbench/map-state.md` with
  `readiness=blocked`, `blocking_reason=subagent_blocked`, blocked lane ids,
  blocked scope, and recovery condition
- `.specify/project-cognition/workbench/coverage-ledger.json.open_gaps[]` with
  `reason="subagent_blocked"`, `lane_id`, `packet_id`, `blocked_scope`,
  `criticality`, `owner`, `status="blocked"`, and `recovery_condition`

`unknown`, `blocked`, `critical_open_gap`, and `subagent_blocked` block baseline
activation. `low_risk_open_gap` may pass only with owner, reason,
`evidence_expectation`, and `revisit_condition`.
```

- [ ] **Step 5: Update passive skills, integrations, README, and handbook**

Use this search to find stale rebuild wording:

```powershell
rg -n "unadoptable coverage gaps|path-index gap is unadoptable|blocked by unadoptable|run_map_scan_build|map-scan.*map-build" templates src README.md PROJECT-HANDBOOK.md tests
```

Update guidance to say:

```text
Use `map-update` for ordinary existing-baseline gaps. Use `map-scan -> map-build`
only for missing or unusable baseline, schema failure, zero active-generation
path_index rows, `explicit_rebuild_requested`, or `baseline_identity_invalid`.
```

Keep first-baseline guidance intact.

- [ ] **Step 6: Run template, docs, and integration guidance tests**

Run:

```powershell
pytest tests/test_map_runtime_template_guidance.py tests/test_map_scan_build_template_guidance.py tests/test_alignment_templates.py tests/test_specify_guidance_docs.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_cursor_agent.py -q
```

Expected: all listed tests pass after updating expected strings.

Commit:

```powershell
git add templates src/specify_cli/integrations README.md PROJECT-HANDBOOK.md tests/test_map_runtime_template_guidance.py tests/test_map_scan_build_template_guidance.py tests/test_alignment_templates.py tests/test_specify_guidance_docs.py tests/integrations
git commit -m "docs: align map maintenance guidance"
```

---

### Task 7: Full Regression Sweep

**Files:**
- No direct code edits unless this task finds a failing assertion that must be corrected.

- [ ] **Step 1: Run focused cognition suite**

Run:

```powershell
pytest tests/test_project_cognition_path_adoption.py tests/test_project_cognition_db.py tests/test_project_cognition_query.py tests/test_project_map_status.py tests/test_project_map_freshness_scripts.py tests/test_project_cognition_validation.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run hook and generated guidance suite**

Run:

```powershell
pytest tests/contract/test_hook_cli_surface.py tests/test_project_map_hard_gate_guidance.py tests/test_map_runtime_template_guidance.py tests/test_map_scan_build_template_guidance.py tests/test_alignment_templates.py tests/test_specify_guidance_docs.py -q
```

Expected: all tests pass.

- [ ] **Step 3: Run integration rendering suite**

Run:

```powershell
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_cursor_agent.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Run the full test suite if focused tests pass**

Run:

```powershell
pytest -q
```

Expected: the full suite passes. If unrelated failures appear, capture the failing test names and the first assertion message before deciding whether to fix them in this branch.

- [ ] **Step 5: Run final grep checks**

Run:

```powershell
rg -n "unadoptable coverage gaps|path-index gap is unadoptable|blocked by unadoptable coverage|unadoptable path ratio|more than 25 changed paths missing" templates src scripts README.md PROJECT-HANDBOOK.md tests
```

Expected: no results, unless a test name or fixture intentionally verifies legacy text is absent.

Run:

```powershell
rg -n "baseline_identity_invalid|explicit_rebuild_requested|subagent_blocked|low_risk_open_gap" templates src scripts README.md PROJECT-HANDBOOK.md tests
```

Expected: results appear in runtime helpers, templates, scripts, docs, and tests.

- [ ] **Step 6: Review final diff and commit any verification fixes**

Run:

```powershell
git diff --check
git status --short
```

Expected: `git diff --check` prints no whitespace errors. `git status --short` contains only intended files.

If verification fixes were required after prior commits, commit them:

```powershell
git add src/specify_cli/cognition/path_adoption.py src/specify_cli/cognition/update.py src/specify_cli/cognition/query.py src/specify_cli/cognition/validation.py src/specify_cli/project_cognition_status.py src/specify_cli/hooks/project_cognition.py src/specify_cli/hooks/artifact_validation.py src/specify_cli/__init__.py scripts/bash/project-map-freshness.sh scripts/powershell/project-map-freshness.ps1 templates/commands/map-update.md templates/commands/map-scan.md templates/commands/map-build.md templates/command-partials/map-scan/shell.md templates/command-partials/map-build/shell.md templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md templates/passive-skills/spec-kit-workflow-routing/SKILL.md src/specify_cli/integrations/base.py src/specify_cli/integrations/cursor_agent/__init__.py README.md PROJECT-HANDBOOK.md tests
git commit -m "test: cover map-update-first maintenance policy"
```
