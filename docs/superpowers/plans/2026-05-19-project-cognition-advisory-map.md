# Project Cognition Advisory Map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert project cognition from a hard workflow gate into an advisory navigation index while preserving map-specific validation and compatibility payloads.

**Architecture:** Keep `sp-map-scan`, `sp-map-build`, `sp-map-update`, readiness payloads, and validation commands intact. Change ordinary consumers so freshness/readiness problems produce warnings and live-code fallback instructions instead of blocking source work; map-maintenance commands keep their own validation failures. Update generated prompts, runtime hooks, CLI helpers, Codex team dispatch, docs, and tests together.

**Tech Stack:** Python 3.11+, Typer CLI, Rich output, pytest, Markdown command templates, generated AI integration guidance.

---

## Reference Spec

- `docs/superpowers/specs/2026-05-19-project-cognition-advisory-map-design.md`

## File Structure

- `src/specify_cli/hooks/project_cognition.py`: central hook result for project cognition freshness. Ordinary commands should receive `warn`, not `blocked`, for missing/stale/update/rebuild diagnostics.
- `src/specify_cli/hooks/preflight.py`: workflow preflight must keep true workflow-state and integrate blockers, but should not convert cognition freshness warnings into errors.
- `src/specify_cli/debug/cli.py`: direct debug helper should warn about degraded cognition and continue.
- `src/specify_cli/__init__.py`: CLI preflight renderer and `sp-teams auto-dispatch` should warn instead of exiting on cognition freshness.
- `src/specify_cli/codex_team/api_surface.py`: structured Codex team API should return `status=ok` for auto-dispatch when cognition is stale/missing, while carrying an advisory payload.
- `src/specify_cli/integrations/base.py`: generated integration addenda should say "advisory project cognition" and code-backed evidence, not "hard gate".
- `src/specify_cli/integrations/cursor_agent/__init__.py`: Cursor-specific generated addendum should match the advisory policy.
- `templates/command-partials/common/context-loading-gradient.md`: shared context loading contract becomes advisory.
- `templates/command-partials/common/senior-consequence-analysis-gate.md`: consequence analysis consumes map hints but uses live evidence when map state is weak.
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`: passive skill becomes advisory routing guidance.
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`: workflow routing no longer says ordinary workflows must detour through map refresh.
- `templates/commands/*.md`: ordinary workflow templates interpret readiness as advisory; map-specific templates keep validation semantics.
- `README.md`, `PROJECT-HANDBOOK.md`, `templates/constitution-template.md`, `templates/constitution/profiles/product.yml`: public docs and generated constitution wording align with advisory map semantics.
- Tests under `tests/`, especially `tests/test_project_map_hard_gate_guidance.py`, `tests/hooks/test_preflight_hooks.py`, `tests/contract/test_codex_team_auto_dispatch_cli.py`, `tests/integrations/test_integration_*`, `tests/test_alignment_templates.py`, and `tests/test_debug_template_guidance.py`.

## Terms

- Ordinary consumer: any workflow or helper using project cognition to navigate a separate task, including specify, plan, tasks, implement, quick, fast, debug, analyze, checklist, deep-research, PRD extraction, direct debug helpers, Codex team auto-dispatch, preflight checks, and generated integration guidance.
- Map-maintenance workflow: `sp-map-scan`, `sp-map-build`, `sp-map-update`, explicit user-requested map repair, `project-cognition validate-scan`, `project-cognition validate-build`, `project-cognition complete-refresh`, and related map finalizers.
- Advisory map result: a warning that says project cognition is degraded and recommends map maintenance, while allowing ordinary work to continue with live repository evidence.

---

### Task 1: Central Freshness Hook Becomes Advisory

**Files:**
- Modify: `src/specify_cli/hooks/project_cognition.py`
- Modify: `tests/test_project_map_hard_gate_guidance.py`

- [ ] **Step 1: Replace hard-gate hook expectations with warning expectations**

In `tests/test_project_map_hard_gate_guidance.py`, update the hook tests so ordinary commands warn instead of block. Replace `test_project_map_hook_fallback_wording_names_project_cognition_runtime` with this test:

```python
def test_project_map_hook_warns_with_advisory_guidance(monkeypatch) -> None:
    def stale_without_reason(_project_root: Path) -> dict[str, object]:
        return {
            "freshness": "stale",
            "state": "runtime_stale",
            "readiness": "blocked",
            "recommended_next_action": "run_map_update",
            "reasons": [],
        }

    def missing_without_reason(_project_root: Path) -> dict[str, object]:
        return {"freshness": "missing", "state": "missing_baseline", "readiness": "blocked", "reasons": []}

    def support_drift_without_reason(_project_root: Path) -> dict[str, object]:
        return {
            "freshness": "support_drift",
            "state": "support_drift",
            "readiness": "blocked",
            "recommended_next_action": "commit_or_ignore_support_files",
            "reasons": [],
        }

    monkeypatch.setattr("specify_cli.hooks.project_cognition.inspect_project_cognition_freshness", stale_without_reason)
    stale = project_map_freshness_result(PROJECT_ROOT, command_name="implement")
    assert stale.status == "warn"
    assert stale.errors == []
    assert stale.warnings == [STALE_FALLBACK_GUIDANCE]
    assert "advisory" in stale.warnings[0].lower()
    assert "/sp-map-update" in stale.warnings[0]

    monkeypatch.setattr("specify_cli.hooks.project_cognition.inspect_project_cognition_freshness", missing_without_reason)
    missing = project_map_freshness_result(PROJECT_ROOT, command_name="debug")
    assert missing.status == "warn"
    assert missing.errors == []
    assert missing.warnings == [MISSING_BASELINE_FALLBACK_GUIDANCE]
    assert "/sp-map-scan -> /sp-map-build" in missing.warnings[0]

    monkeypatch.setattr("specify_cli.hooks.project_cognition.inspect_project_cognition_freshness", support_drift_without_reason)
    support = project_map_freshness_result(PROJECT_ROOT, command_name="implement")
    assert support.status == "warn"
    assert support.errors == []
    assert support.warnings == [SUPPORT_DRIFT_FALLBACK_GUIDANCE]
    assert "support" in support.warnings[0].lower()
```

Replace `test_project_map_hook_blocks_path_index_stale_runtime_with_scan_build_guidance` with:

```python
def test_project_map_hook_warns_path_index_stale_runtime_with_scan_build_guidance(monkeypatch) -> None:
    def path_index_stale(_project_root: Path) -> dict[str, object]:
        return {
            "freshness": "stale",
            "state": "runtime_stale",
            "readiness": "blocked",
            "recommended_next_action": "run_map_scan_build",
            "reasons": [],
        }

    monkeypatch.setattr("specify_cli.hooks.project_cognition.inspect_project_cognition_freshness", path_index_stale)

    result = project_map_freshness_result(PROJECT_ROOT, command_name="debug")

    assert result.status == "warn"
    assert result.errors == []
    assert result.warnings == [PATH_INDEX_STALE_FALLBACK_GUIDANCE]
    assert "path_index" in result.warnings[0]
    assert "/sp-map-scan -> /sp-map-build" in result.warnings[0]
```

Update `test_project_cognition_gate_alias_matches_project_map_gate` so it expects `warn`:

```python
def test_project_cognition_gate_alias_matches_project_map_gate(monkeypatch) -> None:
    def stale_without_reason(_project_root: Path) -> dict[str, object]:
        return {
            "freshness": "stale",
            "state": "runtime_stale",
            "readiness": "blocked",
            "recommended_next_action": "run_map_update",
            "reasons": [],
        }

    monkeypatch.setattr("specify_cli.hooks.project_cognition.inspect_project_cognition_freshness", stale_without_reason)
    result = project_cognition_freshness_result(PROJECT_ROOT, command_name="implement")
    aliased = project_map_freshness_result(PROJECT_ROOT, command_name="implement")

    assert result.status == "warn"
    assert result.warnings == aliased.warnings
    assert result.errors == []
```

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run:

```bash
pytest tests/test_project_map_hard_gate_guidance.py -q
```

Expected: failures showing old `blocked` status and old guidance text.

- [ ] **Step 3: Replace hard-gate constants and hook branching**

In `src/specify_cli/hooks/project_cognition.py`, replace the freshness guidance constants and `project_cognition_freshness_result()` with this implementation. Keep `mark_dirty_hook()` and `complete_refresh_hook()` unchanged.

```python
STALE_FALLBACK_GUIDANCE = (
    "project cognition index is stale; treat map output as advisory, continue with live repository evidence, "
    "and recommend /sp-map-update as follow-up map maintenance for changed paths"
)
PATH_INDEX_STALE_FALLBACK_GUIDANCE = (
    "project cognition index is stale because changed paths are missing from path_index; treat map output as advisory, "
    "continue with live repository evidence, and recommend /sp-map-scan -> /sp-map-build only if the user wants map repair"
)
SUPPORT_DRIFT_FALLBACK_GUIDANCE = (
    "project cognition support-surface drift was detected; treat map output as advisory, continue with live repository evidence, "
    "and recommend resolving, committing, or intentionally ignoring support files as follow-up"
)
PARTIAL_REFRESH_FALLBACK_GUIDANCE = (
    "project cognition refresh data was recorded, but readiness did not pass; treat map output as advisory, "
    "continue with live repository evidence, and recommend the reported map-maintenance next action as follow-up"
)
NON_STALE_FALLBACK_GUIDANCE = (
    "project cognition index state is {state}; treat map output as advisory and use live code, tests, scripts, "
    "configuration, or authoritative docs as evidence"
)
MISSING_BASELINE_FALLBACK_GUIDANCE = (
    "project cognition index is missing; continue with live repository evidence and recommend /sp-map-scan -> /sp-map-build "
    "only if the user wants a map baseline"
)


def project_cognition_freshness_result(project_root: Path, *, command_name: str) -> HookResult:
    normalized = command_name.strip().lower()
    freshness = inspect_project_cognition_freshness(project_root)
    raw_freshness = str(freshness.get("freshness", "")).strip().lower()
    state = str(freshness.get("state", freshness.get("freshness", ""))).strip().lower()
    readiness = str(freshness.get("readiness", "")).strip().lower()
    next_action = str(freshness.get("recommended_next_action", "")).strip().lower()
    reasons = [str(item) for item in freshness.get("reasons", []) if str(item).strip()]

    data = {"freshness": freshness, "advisory": True, "command_name": normalized}
    if state == "fresh":
        return HookResult(
            event="project_cognition.refresh.validate",
            status="ok",
            severity="info",
            data=data,
        )

    if state == "missing_baseline":
        guidance = MISSING_BASELINE_FALLBACK_GUIDANCE
    elif state == "runtime_stale" and readiness == "blocked" and raw_freshness != "possibly_stale":
        guidance = PATH_INDEX_STALE_FALLBACK_GUIDANCE if next_action == "run_map_scan_build" else STALE_FALLBACK_GUIDANCE
    elif state == "support_drift":
        guidance = SUPPORT_DRIFT_FALLBACK_GUIDANCE
    elif state == "partial_refresh":
        guidance = PARTIAL_REFRESH_FALLBACK_GUIDANCE
    elif readiness == "blocked" and next_action == "run_map_update":
        guidance = STALE_FALLBACK_GUIDANCE
    else:
        guidance = NON_STALE_FALLBACK_GUIDANCE.format(state=state or "unknown")

    return HookResult(
        event="project_cognition.refresh.validate",
        status="warn",
        severity="warning",
        warnings=reasons or [guidance],
        data=data,
    )
```

- [ ] **Step 4: Run focused tests and commit**

Run:

```bash
pytest tests/test_project_map_hard_gate_guidance.py -q
```

Expected: all tests in the file pass.

Commit:

```bash
git add src/specify_cli/hooks/project_cognition.py tests/test_project_map_hard_gate_guidance.py
git commit -m "fix: make cognition freshness hook advisory"
```

---

### Task 2: Workflow Preflight Warns On Map State But Still Blocks Real Workflow Errors

**Files:**
- Modify: `src/specify_cli/hooks/preflight.py`
- Modify: `tests/hooks/test_preflight_hooks.py`

- [ ] **Step 1: Update preflight tests for advisory cognition**

In `tests/hooks/test_preflight_hooks.py`, rename and update these tests:

```python
def test_preflight_warns_when_project_map_status_is_missing_for_brownfield_work(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        active_command="sp-specify",
        status="active",
        phase_mode="planning-only",
        next_command="/sp.plan",
    )

    result = run_quality_hook(
        project,
        "workflow.preflight",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "warn"
    assert result.severity == "warning"
    assert result.errors == []
    assert any("cognition" in message.lower() for message in result.warnings)
```

For the dirty-origin tests, change only the assertions so cognition staleness is a warning:

```python
assert result.status == "warn"
assert result.errors == []
assert any("cognition" in message.lower() or "shared_surface_changed" in message for message in result.warnings)
```

Apply that assertion shape to:

- `test_preflight_blocks_same_feature_implement_when_lane_id_differs`
- `test_preflight_blocks_same_lane_implement_when_dirty_scope_does_not_overlap`
- `test_preflight_blocks_cross_feature_implement_when_dirty_origin_differs`
- `test_preflight_blocks_specify_when_dirty_origin_exists`
- `test_preflight_blocks_support_drift_with_support_specific_guidance`

Do not change tests that block on workflow-state ordering, analyze gates, or integrate readiness.

- [ ] **Step 2: Run focused tests and confirm failures**

Run:

```bash
pytest tests/hooks/test_preflight_hooks.py -q
```

Expected: old cognition-related tests fail because preflight still returns `blocked` for map state.

- [ ] **Step 3: Simplify cognition handling in preflight**

In `src/specify_cli/hooks/preflight.py`, replace the initial cognition error/warning setup with:

```python
    errors: list[str] = []
    warnings = list(freshness.warnings)
    if freshness.errors:
        warnings.extend(freshness.errors)
```

Delete the implement-specific block that starts with:

```python
        if (
            freshness.status == "blocked"
            and str(freshness_payload.get("state", freshness_payload.get("freshness", ""))).strip().lower() == "runtime_stale"
```

and ends before:

```python
        if not state_path.exists():
```

The remaining implement checks must still block on missing `workflow-state.md`, wrong `next_command`, and active analyze gates.

- [ ] **Step 4: Run focused tests and commit**

Run:

```bash
pytest tests/hooks/test_preflight_hooks.py -q
```

Expected: all tests in the file pass.

Commit:

```bash
git add src/specify_cli/hooks/preflight.py tests/hooks/test_preflight_hooks.py
git commit -m "fix: make workflow preflight cognition advisory"
```

---

### Task 3: Direct CLI Consumers Warn Instead Of Blocking On Cognition

**Files:**
- Modify: `src/specify_cli/debug/cli.py`
- Modify: `src/specify_cli/__init__.py`
- Modify: `src/specify_cli/codex_team/api_surface.py`
- Create: `tests/debug/test_debug_cli_preflight.py`
- Modify: `tests/contract/test_codex_team_auto_dispatch_cli.py`

- [ ] **Step 1: Add a direct debug preflight regression test**

Create `tests/debug/test_debug_cli_preflight.py`:

```python
from pathlib import Path

from specify_cli.debug.cli import _project_map_preflight_for_debug


def test_debug_preflight_warns_instead_of_exiting_on_stale_cognition(monkeypatch, tmp_path: Path):
    project = tmp_path / "debug-project"
    project.mkdir()
    (project / ".specify").mkdir()
    monkeypatch.chdir(project)

    def stale(_project_root: Path) -> dict[str, object]:
        return {
            "freshness": "stale",
            "state": "runtime_stale",
            "readiness": "blocked",
            "recommended_next_action": "run_map_update",
            "reasons": ["changed path not reflected in map"],
        }

    monkeypatch.setattr("specify_cli.debug.cli.inspect_project_cognition_freshness", stale)

    _project_map_preflight_for_debug()
```

- [ ] **Step 2: Update Codex team auto-dispatch tests**

In `tests/contract/test_codex_team_auto_dispatch_cli.py`, rename and update the cognition dirty tests:

```python
def test_team_auto_dispatch_warns_when_project_cognition_is_dirty(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    env = _fake_tmux_env(tmp_path)

    status_path = project / ".specify" / "project-cognition" / "status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    payload["freshness"] = "stale"
    payload["dirty"] = True
    payload["dirty_reasons"] = ["shared_surface_changed"]
    status_path.write_text(json.dumps(payload), encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["sp-teams", "auto-dispatch", "--feature-dir", "specs/001-auto-dispatch"],
        env=env,
    )

    assert result.exit_code == 0, result.output
    output = strip_ansi(result.output)
    assert "Cognition Freshness" in output
    assert "Auto-dispatched" in output
```

```python
def test_team_auto_dispatch_warns_with_legacy_project_map_dirty_status(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    env = _fake_tmux_env(tmp_path)

    canonical_status_path = project / ".specify" / "project-cognition" / "status.json"
    canonical_status_path.unlink()
    legacy_status_path = project / ".specify" / "project-map" / "status.json"
    legacy_status_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_status_path.write_text(
        json.dumps(
            {
                "version": 1,
                "last_mapped_commit": "",
                "last_mapped_at": "2026-04-21T00:00:00Z",
                "last_mapped_branch": "",
                "freshness": "stale",
                "last_refresh_reason": "legacy-dirty-status",
                "dirty": True,
                "dirty_reasons": ["shared_surface_changed"],
            }
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["sp-teams", "auto-dispatch", "--feature-dir", "specs/001-auto-dispatch"],
        env=env,
    )

    assert result.exit_code == 0, result.output
    output = strip_ansi(result.output)
    assert "Cognition Freshness" in output
    assert "Auto-dispatched" in output
```

Keep `test_team_auto_dispatch_blocks_when_baseline_build_is_known_blocked` unchanged; baseline build failure is not map maintenance.

- [ ] **Step 3: Add structured API assertion**

In `test_team_api_auto_dispatch_returns_json_payload`, add:

```python
    assert envelope["payload"].get("project_cognition_advisory", {}).get("freshness") in {None, "missing", "stale", "fresh"}
```

Add a new stale API test:

```python
def test_team_api_auto_dispatch_returns_advisory_when_cognition_is_stale(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    env = _fake_tmux_env(tmp_path)
    status_path = project / ".specify" / "project-cognition" / "status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    payload["freshness"] = "stale"
    payload["dirty"] = True
    payload["dirty_reasons"] = ["shared_surface_changed"]
    status_path.write_text(json.dumps(payload), encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["sp-teams", "api", "auto-dispatch", "--feature-dir", "specs/001-auto-dispatch"],
        env=env,
    )

    assert result.exit_code == 0, result.output
    envelope = json.loads(result.output.strip())
    assert envelope["status"] == "ok"
    advisory = envelope["payload"]["project_cognition_advisory"]
    assert advisory["freshness"] == "stale"
    assert "shared_surface_changed" in advisory["reasons"]
```

- [ ] **Step 4: Run focused tests and confirm failures**

Run:

```bash
pytest tests/debug/test_debug_cli_preflight.py tests/contract/test_codex_team_auto_dispatch_cli.py -q
```

Expected: failures from old debug exit and old team auto-dispatch block.

- [ ] **Step 5: Make debug CLI preflight advisory**

In `src/specify_cli/debug/cli.py`, replace `_project_map_preflight_for_debug()` with:

```python
def _project_map_preflight_for_debug() -> None:
    project_root = Path.cwd()
    if not (project_root / ".specify").exists():
        return

    result = inspect_project_cognition_freshness(project_root)
    state = str(result.get("state", result["freshness"])).strip().lower()
    if state == "fresh":
        return

    console.print(
        "[yellow]Warning:[/yellow] Project cognition is degraded or unavailable; "
        "debug will continue with live repository evidence. Treat map output as advisory."
    )
    next_action = str(result.get("recommended_next_action", "")).strip()
    if next_action:
        console.print(f"[yellow]Map maintenance follow-up:[/yellow] {next_action}")
    for reason in result.get("reasons", []):
        console.print(f"- {reason}")
```

- [ ] **Step 6: Make shared CLI preflight advisory**

In `src/specify_cli/__init__.py`, change `_render_project_map_preflight_guidance()` so it prints warnings and recommendations instead of errors. Replace the first `console.print()` call in that function with:

```python
    console.print(
        f"[yellow]Warning:[/yellow] Project cognition is {state or 'unknown'} for [cyan]{command_name}[/cyan]. "
        "Treat map output as advisory and use live repository evidence for conclusions."
    )
```

Update the branch messages:

```python
    if state == "missing_baseline":
        console.print(
            "Recommended map maintenance: run [cyan]/sp-map-scan[/cyan], then [cyan]/sp-map-build[/cyan] when you want a project cognition baseline."
        )
    elif state == "support_drift":
        console.print(
            "Recommended map maintenance: resolve, commit, or intentionally ignore the support-surface drift."
        )
    elif state == "partial_refresh":
        console.print(
            "Refresh data was recorded, but runtime readiness did not pass. Continue this task from live repository evidence."
        )
        console.print(
            f"Recommended map maintenance: {result.get('recommended_next_action') or 'none'}."
        )
    elif str(result.get("recommended_next_action", "")).strip().lower() == "run_map_scan_build":
        console.print(
            "Recommended map maintenance: run [cyan]/sp-map-scan[/cyan], then [cyan]/sp-map-build[/cyan] if you want to repair missing path_index coverage."
        )
    else:
        console.print(
            "Recommended map maintenance: run [cyan]/sp-map-update[/cyan] with changed paths after the current task."
        )
```

In `_project_map_preflight()`, replace the blocking branch:

```python
    if freshness in block_levels and readiness == "blocked":
        _render_project_map_freshness(result)
        _render_project_map_preflight_guidance(result, command_name=command_name)
        raise typer.Exit(1)
```

with:

```python
    if freshness in block_levels and readiness == "blocked":
        _render_project_map_freshness(result)
        _render_project_map_preflight_guidance(result, command_name=command_name)
        return result
```

In `team_auto_dispatch()`, keep the preflight call but treat it as advisory:

```python
    _project_map_preflight(project_root, command_name="team auto-dispatch")
```

- [ ] **Step 7: Make structured Codex team API advisory**

In `src/specify_cli/codex_team/api_surface.py`, replace the `if freshness["freshness"] in {"missing", "stale"}:` block with:

```python
        project_cognition_advisory = {
            "freshness": freshness.get("freshness"),
            "state": freshness.get("state", freshness.get("freshness")),
            "readiness": freshness.get("readiness"),
            "recommended_next_action": freshness.get("recommended_next_action"),
            "reasons": freshness.get("reasons", []),
        }
```

After `route_ready_parallel_batch()` succeeds, include that advisory in the payload:

```python
                "project_cognition_advisory": project_cognition_advisory,
```

- [ ] **Step 8: Run focused tests and commit**

Run:

```bash
pytest tests/debug/test_debug_cli_preflight.py tests/contract/test_codex_team_auto_dispatch_cli.py -q
```

Expected: all selected tests pass.

Commit:

```bash
git add src/specify_cli/debug/cli.py src/specify_cli/__init__.py src/specify_cli/codex_team/api_surface.py tests/debug/test_debug_cli_preflight.py tests/contract/test_codex_team_auto_dispatch_cli.py
git commit -m "fix: make direct cognition consumers advisory"
```

---

### Task 4: Generated Integration Guidance Uses Advisory Language

**Files:**
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `src/specify_cli/integrations/cursor_agent/__init__.py`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_claude.py`
- Modify: `tests/integrations/test_integration_codex.py`

- [ ] **Step 1: Update integration tests away from hard-gate wording**

In the three base integration test files, replace assertions using:

```python
hard_gate_index = content.find("project cognition hard gate")
```

with:

```python
advisory_index = content.find("project cognition advisory")
assert advisory_index != -1
```

Add these assertions where the generated content for runtime commands is checked:

```python
assert "map output as advisory" in lower
assert "code, tests, scripts, configuration, or authoritative docs" in lower
assert "needs_update` routes through" not in lower
assert "needs_rebuild` routes through" not in lower
assert "treat this as a hard gate" not in lower
```

In `tests/integrations/test_integration_codex.py`, replace the two assertions:

```python
assert "if cognition freshness is `missing`, stop and tell the user to run `$sp-map-scan`, then `$sp-map-build`" in content
assert "if cognition freshness is `stale`, stop and tell the user to use `$sp-map-update`" in content
```

with:

```python
assert "if cognition freshness is `missing`, continue with live repository evidence" in content
assert "if cognition freshness is `stale`, treat map output as advisory" in content
```

- [ ] **Step 2: Run integration guidance tests and confirm failures**

Run:

```bash
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_codex.py -q
```

Expected: failures from old "hard gate" generated guidance.

- [ ] **Step 3: Update base integration addenda**

In `src/specify_cli/integrations/base.py`, rename the marker in `_append_runtime_project_cognition_gate()` from:

```python
marker = f"## {agent_name} Project Cognition Hard Gate"
```

to:

```python
marker = f"## {agent_name} Project Cognition Advisory"
```

Replace the addendum body inside `_append_runtime_project_cognition_gate()` with:

```python
        addendum = (
            "\n"
            f"## {agent_name} Project Cognition Advisory\n\n"
            f"{query_gate}\n"
            "- Interpret returned readiness as map quality diagnostics. `ready` and `review` can guide the first live reads; `ambiguous`, `needs_update`, `needs_rebuild`, and `blocked` do not stop ordinary work outside map-maintenance workflows.\n"
            "- Treat the project cognition query bundle as an advisory brownfield navigation surface. Use it to choose likely owners, affected paths, risks, and verification routes.\n"
            "- Do not treat map output as evidence by itself. Technical claims must be backed by live code, tests, scripts, configuration, or authoritative docs.\n"
            "- If the map is missing, stale, blocked, or too incomplete for the requested work, continue with live repository inspection and recommend map maintenance as follow-up.\n"
            "- A project-cognition query is useful only when its route hints, `minimal_live_reads`, missing coverage, and conflicts are carried into the next workflow artifact or execution state as advisory context.\n"
            f"{carry_forward}"
        )
```

Update `_project_cognition_query_gate_line()` so it no longer says `MUST`:

```python
        return (
            "**Advisory First Pass**: When project cognition is available, use agent-assisted query planning first: "
            f"retrieve the map lexicon with `{{{{specify-subcmd:project-cognition lexicon --intent {intent} --query=\"$ARGUMENTS\" --format json}}}}`, "
            "translate the raw user intent into a query_plan using returned map terms, then run "
            f"`{{{{specify-subcmd:project-cognition query --intent {intent} --query-plan \"<query_plan_json>\" --format json}}}}` "
            f"{command_step}. Use returned readiness, the task-local bundle, and `minimal_live_reads` as navigation hints, then verify claims from live project evidence."
        )
```

In `_append_planning_skill_cognition_refresh_guidance()`, replace the refresh closeout addendum with:

```python
        addendum = (
            "\n"
            f"{marker}\n\n"
            "- This workflow is artifact-only unless the user explicitly requested source/runtime changes; do not call `project-cognition mark-dirty`, `project-cognition complete-refresh`, or `project-cognition validate-build --format json` just because `sp-specify`, `sp-plan`, or `sp-tasks` wrote planning artifacts.\n"
            "- When later actual source/runtime changes update ownership, workflow names, integration contracts, verification entry points, runtime assumptions, or other cognition coverage facts, recommend `/sp-map-update` with the changed paths as follow-up map maintenance.\n"
            "- Do not mutate project cognition freshness as a completion requirement for ordinary work. `mark-dirty`, `complete-refresh`, and build validation belong to map-maintenance workflows or explicit user-requested repair.\n"
            "- Use live code, tests, scripts, configuration, and authoritative docs as evidence for technical claims; use project cognition only as advisory routing context.\n"
        )
```

- [ ] **Step 4: Update Cursor-specific guidance**

In `src/specify_cli/integrations/cursor_agent/__init__.py`, rename `_append_project_cognition_gate_to_file()` marker text from `"## Cursor Project Cognition Gate"` to `"## Cursor Project Cognition Advisory"` and replace the addendum with:

```python
        addendum = (
            "\n"
            "## Cursor Project Cognition Advisory\n\n"
            "**Advisory First Pass**: Before repository analysis or implementation, query project cognition when available and use it to choose likely live reads.\n"
            "- Use `.specify/project-cognition/` as the graph-native project cognition source when present.\n"
            "- If the runtime is missing, stale, blocked, or too incomplete for the requested work, continue with live repository inspection instead of stopping for map repair.\n"
            "- Treat `sp-map-scan`, `sp-map-build`, and `sp-map-update` as recommended map-maintenance follow-ups unless the user explicitly requested map repair first.\n"
            "- Do not treat map output as evidence by itself; verify technical claims from live code, tests, scripts, configuration, or authoritative docs.\n"
        )
```

- [ ] **Step 5: Run integration guidance tests and commit**

Run:

```bash
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_codex.py -q
```

Expected: all selected integration guidance tests pass.

Commit:

```bash
git add src/specify_cli/integrations/base.py src/specify_cli/integrations/cursor_agent/__init__.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_codex.py
git commit -m "docs: generate advisory cognition guidance"
```

---

### Task 5: Shared Templates And Passive Skills Use Advisory Routing

**Files:**
- Modify: `templates/command-partials/common/context-loading-gradient.md`
- Modify: `templates/command-partials/common/senior-consequence-analysis-gate.md`
- Modify: `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `tests/test_project_map_hard_gate_guidance.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_debug_template_guidance.py`

- [ ] **Step 1: Update shared-template tests**

In `tests/test_project_map_hard_gate_guidance.py`, rename `test_ordinary_sp_workflows_use_shared_project_cognition_gate` to:

```python
def test_ordinary_sp_workflows_use_shared_project_cognition_advisory() -> None:
```

Replace the freshness assertions with:

```python
    assert "project cognition advisory index" in lowered_gate
    assert "map output is advisory" in lowered_gate
    assert "`missing` -> warn and continue with live repository evidence" in shared_gate
    assert "`stale` -> warn and continue with live repository evidence" in shared_gate
    assert "Do not treat handbook-first or layered project-map files as evidence" in shared_gate
```

In `tests/test_alignment_templates.py`, replace old runtime truth assertions around lines that check README, handbook, and passive skills:

```python
assert "default brownfield runtime truth surface" in lowered
assert "runtime truth surface" in lowered
assert "project cognition as the primary runtime truth surface" in lowered
```

with:

```python
assert "advisory project cognition index" in lowered
assert "map points, code proves" in lowered
assert "runtime truth surface" not in lowered
```

Keep assertions for map-specific validation commands in map-specific tests.

- [ ] **Step 2: Run shared-template tests and confirm failures**

Run:

```bash
pytest tests/test_project_map_hard_gate_guidance.py tests/test_alignment_templates.py tests/test_debug_template_guidance.py -q
```

Expected: failures from old hard-gate and runtime-truth wording.

- [ ] **Step 3: Rewrite `context-loading-gradient.md`**

Replace the opening hard rule in `templates/command-partials/common/context-loading-gradient.md` with:

```markdown
## Project Cognition Advisory

This command should treat the project cognition runtime as an advisory navigation index, not a mandatory pre-source gate.

### Advisory Rule

Use project cognition when available to find likely owners, affected paths, risks, verification routes, and minimal live reads. Do not treat map output as evidence by itself. Technical claims must be backed by live code, tests, scripts, configuration, or authoritative docs.
```

Replace the freshness section with:

```markdown
### Freshness

Treat runtime freshness as map-quality diagnostics:

- `fresh` -> use the returned task-local bundle as a first-pass navigation aid
- `missing` -> warn and continue with live repository evidence; recommend `sp-map-scan -> sp-map-build` as follow-up map maintenance
- `stale` -> warn and continue with live repository evidence; recommend `sp-map-update` as follow-up map maintenance
- `stale` with changed paths missing from `path_index` -> warn and continue with live repository evidence; recommend `sp-map-scan -> sp-map-build` only if the user wants map repair
- `support_drift` -> warn and continue with live repository evidence; recommend resolving or intentionally ignoring support-surface drift
- `partial_refresh` -> warn that refresh data was recorded but readiness did not pass; continue with live repository evidence
- `possibly_stale` -> inspect returned affected scope when useful, then continue with live repository evidence

Preserve the distinction between machine freshness and public guidance: `freshness` records map quality, while `recommended_next_action` is a map-maintenance recommendation.
```

Replace the primary read restriction ending with:

```markdown
Do not treat handbook-first or layered project-map files as evidence. If query-returned coverage is insufficient, inspect live repository surfaces directly and recommend `sp-map-update` or `sp-map-scan -> sp-map-build` as follow-up map maintenance when useful.
```

- [ ] **Step 4: Rewrite passive skill guidance**

In `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`, change:

```markdown
This passive skill is the brownfield hard gate, not the route selection layer.
```

to:

```markdown
This passive skill is the brownfield advisory navigation layer, not a hard workflow gate.
```

Replace the `## Hard Gate` heading with:

```markdown
## Advisory Navigation
```

Add this paragraph after the heading:

```markdown
Use project cognition as a first-pass map when it is available. If it is missing, stale, blocked, ambiguous, or incomplete, continue with live repository inspection and record a map-maintenance recommendation. Do not block ordinary planning, implementation, debugging, or review solely to refresh the map.
```

In the `Freshness State Guidance` section, replace route-through language with advisory language:

```markdown
- If the project cognition runtime is missing, continue from live repository evidence and recommend `{{invoke:map-scan}} -> {{invoke:map-build}}` as follow-up map maintenance.
- If the project cognition runtime is stale for a localized touched area, continue from live repository evidence and recommend `{{invoke:map-update}}` as follow-up map maintenance.
- If the freshness state is `support_drift`, warn that support-surface drift may affect the map and recommend resolving or intentionally ignoring the support change.
- If the freshness state is `partial_refresh`, warn that refresh data was recorded but readiness did not pass; treat the map as advisory.
- Treat `recommended_next_action` as map-maintenance guidance, not a command that supersedes the user's current task.
```

In `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`, replace:

```markdown
- Use `sp-map-update` before other workflow steps when project cognition runtime
  coverage is stale or too weak for a localized touched area.
- Use `sp-map-scan -> sp-map-build` before other workflow steps only when
  project cognition runtime context for an existing codebase is missing,
  unusable, schema-incompatible, explicitly being rebuilt, or invalidated by
  broad architecture replacement.
```

with:

```markdown
- Recommend `sp-map-update` as follow-up map maintenance when project cognition
  coverage is stale or too weak for a localized touched area.
- Recommend `sp-map-scan -> sp-map-build` as follow-up map maintenance when
  no usable project cognition baseline exists or the user explicitly asks to
  repair/rebuild the map.
```

- [ ] **Step 5: Update senior consequence partial**

In `templates/command-partials/common/senior-consequence-analysis-gate.md`, replace the first paragraph with:

```markdown
Project cognition readiness provides advisory routing context. If readiness is `ready` or `review`, use the returned task-local bundle and `minimal_live_reads` as first-pass navigation. If readiness is `ambiguous`, `needs_update`, `needs_rebuild`, or `blocked`, continue with live repository evidence and record a map-maintenance recommendation instead of blocking ordinary work. Carry relevant project cognition facts, returned `minimal_live_reads`, inference notes, and coverage gaps into the workflow's artifacts or durable state as advisory context.
```

- [ ] **Step 6: Run focused tests and commit**

Run:

```bash
pytest tests/test_project_map_hard_gate_guidance.py tests/test_alignment_templates.py tests/test_debug_template_guidance.py -q
```

Expected: all selected tests pass.

Commit:

```bash
git add templates/command-partials/common/context-loading-gradient.md templates/command-partials/common/senior-consequence-analysis-gate.md templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md templates/passive-skills/spec-kit-workflow-routing/SKILL.md tests/test_project_map_hard_gate_guidance.py tests/test_alignment_templates.py tests/test_debug_template_guidance.py
git commit -m "docs: make shared cognition guidance advisory"
```

---

### Task 6: Ordinary Workflow Templates Recommend Map Maintenance After Work

**Files:**
- Modify: `templates/commands/analyze.md`
- Modify: `templates/commands/checklist.md`
- Modify: `templates/commands/clarify.md`
- Modify: `templates/commands/debug.md`
- Modify: `templates/commands/deep-research.md`
- Modify: `templates/commands/fast.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/prd-scan.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/tasks.md`
- Keep map-maintenance validation in `templates/commands/map-scan.md`, `templates/commands/map-build.md`, and `templates/commands/map-update.md`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_quick_template_guidance.py`
- Modify: `tests/test_debug_template_guidance.py`
- Modify: `tests/test_map_runtime_template_guidance.py`

- [ ] **Step 1: Add negative guidance tests**

In `tests/test_alignment_templates.py`, add:

```python
def test_ordinary_workflows_treat_map_readiness_as_advisory():
    ordinary_templates = [
        "templates/commands/analyze.md",
        "templates/commands/checklist.md",
        "templates/commands/clarify.md",
        "templates/commands/debug.md",
        "templates/commands/deep-research.md",
        "templates/commands/fast.md",
        "templates/commands/implement.md",
        "templates/commands/plan.md",
        "templates/commands/prd-scan.md",
        "templates/commands/quick.md",
        "templates/commands/specify.md",
        "templates/commands/tasks.md",
    ]
    for rel_path in ordinary_templates:
        lowered = _read(rel_path).lower()
        assert "map output as advisory" in lowered or "project cognition advisory" in lowered, rel_path
        assert "`needs_update`: route through `{{invoke:map-update}}`" not in lowered, rel_path
        assert "`needs_rebuild`: route through `{{invoke:map-scan}}`, then `{{invoke:map-build}}`" not in lowered, rel_path
        assert "wait for that rebuild before continuing" not in lowered, rel_path
        assert "before continuing" not in lowered or "map-scan" not in lowered, rel_path
```

In `tests/test_map_runtime_template_guidance.py`, keep map-specific validation assertions for `map-build` and `map-update`, but change assertions that ordinary workflows must route on `needs_rebuild` to advisory assertions.

- [ ] **Step 2: Run ordinary template tests and confirm failures**

Run:

```bash
pytest tests/test_alignment_templates.py tests/test_quick_template_guidance.py tests/test_debug_template_guidance.py tests/test_map_runtime_template_guidance.py -q
```

Expected: failures from old route-through wording.

- [ ] **Step 3: Replace readiness route bullets in ordinary templates**

For every ordinary command listed in this task, replace readiness bullets of this form:

```markdown
- `needs_update`: route through `{{invoke:map-update}}`.
- `needs_rebuild`: route through `{{invoke:map-scan}}`, then `{{invoke:map-build}}`.
```

with:

```markdown
- `needs_update`: treat map output as advisory, continue with live repository evidence, and recommend `{{invoke:map-update}}` as follow-up map maintenance.
- `needs_rebuild`: treat map output as advisory, continue with live repository evidence, and recommend `{{invoke:map-scan}}`, then `{{invoke:map-build}}` only when the user wants map repair.
```

Replace sentence forms such as:

```markdown
stop and tell the user to run `{{invoke:map-scan}}`, then `{{invoke:map-build}}`; wait for that rebuild before continuing
```

with:

```markdown
warn that the map baseline is missing, continue with live repository evidence, and recommend `{{invoke:map-scan}}`, then `{{invoke:map-build}}` as follow-up map maintenance
```

- [ ] **Step 4: Replace completion-time forced refresh guidance**

In `templates/commands/fast.md`, `templates/commands/quick.md`, `templates/commands/debug.md`, and `templates/commands/implement.md`, replace completion guidance that says to refresh project cognition before marking work complete with:

```markdown
- If the completed work changed ownership, workflow names, integration contracts, verification entry points, runtime assumptions, generated-surface propagation, or other map-covered facts, report the changed paths and recommend `{{invoke:map-update}}` as follow-up map maintenance. Do not call `project-cognition mark-dirty`, `project-cognition validate-build`, `project-cognition complete-refresh`, `{{invoke:map-update}}`, or `{{invoke:map-scan}} -> {{invoke:map-build}}` as a completion requirement for this ordinary workflow unless the user explicitly requested map maintenance.
- The completion claim must be backed by live code, tests, scripts, configuration, or authoritative docs. Project cognition can support route selection but cannot be the sole evidence for completion.
```

- [ ] **Step 5: Preserve map-maintenance command validation**

Open `templates/commands/map-scan.md`, `templates/commands/map-build.md`, and `templates/commands/map-update.md`. Confirm the following semantics remain:

```markdown
map-scan validates scan artifacts before map-build handoff
map-build validates query-ready runtime before complete-refresh
map-update validates its own update records and may preserve partial refresh
```

Do not remove `project-cognition validate-scan --format json`, `project-cognition validate-build --format json`, or map-specific blocked behavior from these three files.

- [ ] **Step 6: Run focused tests and commit**

Run:

```bash
pytest tests/test_alignment_templates.py tests/test_quick_template_guidance.py tests/test_debug_template_guidance.py tests/test_map_runtime_template_guidance.py -q
```

Expected: all selected template tests pass.

Commit:

```bash
git add templates/commands tests/test_alignment_templates.py tests/test_quick_template_guidance.py tests/test_debug_template_guidance.py tests/test_map_runtime_template_guidance.py
git commit -m "docs: make ordinary workflows map-advisory"
```

---

### Task 7: Documentation And Constitution Wording Align With Advisory Map Policy

**Files:**
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `templates/constitution-template.md`
- Modify: `templates/constitution/profiles/product.yml`
- Modify: `tests/test_constitution_defaults.py`
- Modify: `tests/test_constitution_profiles_cli.py`
- Modify: `tests/test_project_handbook_templates.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_passive_skill_guidance.py`

- [ ] **Step 1: Update documentation tests**

Where tests currently assert:

```python
assert "default brownfield runtime truth surface" in content
assert "runtime truth surface" in content
assert "hard gate" in content
```

replace with:

```python
assert "advisory project cognition index" in content.lower()
assert "map points, code proves" in content.lower()
assert "runtime truth surface" not in content.lower()
assert "hard gate before source-level work" not in content.lower()
```

For constitution tests, use:

```python
assert "project cognition is an advisory navigation index" in content.lower()
assert "technical claims must be backed by live project evidence" in content.lower()
```

- [ ] **Step 2: Run documentation tests and confirm failures**

Run:

```bash
pytest tests/test_constitution_defaults.py tests/test_constitution_profiles_cli.py tests/test_project_handbook_templates.py tests/test_alignment_templates.py tests/test_passive_skill_guidance.py -q
```

Expected: failures from old public wording.

- [ ] **Step 3: Update README brownfield cognition sections**

In both repeated project cognition sections in `README.md`, replace "runtime truth surface" wording with:

```markdown
- Generated projects use `.specify/project-cognition/status.json` plus the agent-planned task-local project cognition query bundle as the advisory project cognition index. `.specify/project-cognition/project-cognition.db` is the canonical graph store for map queries, not evidence by itself.
- New generated workflows use `.specify/project-cognition/status.json`, `.specify/project-cognition/project-cognition.db`, `project-cognition lexicon`, and `project-cognition query --query-plan` as advisory navigation inputs. `specify project-map ...` remains a legacy CLI alias for existing projects, but new workflows should not read or require `.specify/project-map/**`.
- For the first brownfield cognition baseline, run `sp-map-scan` followed by `sp-map-build` when you want a map baseline. That pair is map-maintenance complete only when scan acceptance and build acceptance pass: `project-cognition validate-scan --format json` and `project-cognition validate-build --format json`. Ordinary workflows may continue from live repository evidence when the map is missing, stale, or blocked.
- After source/runtime work changes map-covered surfaces, recommend `sp-map-update` with the changed paths as follow-up map maintenance. Do not treat `needs_update`, `needs_rebuild`, `stale`, or `possibly_stale` as mandatory detours for ordinary work.
```

Replace the paragraph that says ordinary workflows should treat cognition freshness as a hard gate with:

```markdown
Generated projects track cognition freshness in `.specify/project-cognition/status.json`, so workflows can report whether the current map is `fresh`, `missing`, `stale`, `support_drift`, `partial_refresh`, or `possibly_stale`. Ordinary `sp-*` workflows should treat those states as map-quality diagnostics, not workflow blockers. Map points, code proves: technical claims must be backed by live code, tests, scripts, configuration, or authoritative docs.
```

- [ ] **Step 4: Update PROJECT-HANDBOOK**

In `PROJECT-HANDBOOK.md`, replace the brownfield cognition lifecycle bullet with a shorter advisory version:

```markdown
- **Brownfield cognition lifecycle**: Generated projects use `.specify/project-cognition/status.json` plus agent-planned `project-cognition query` task-local bundles as an advisory project cognition index, while `.specify/project-cognition/project-cognition.db` is the canonical graph store for map queries. Workflows first call `project-cognition lexicon`, have the agent translate raw user intent into a `query_plan` using returned map terms, then call `project-cognition query --query-plan` when the map is available. The map points; code proves. If the map is missing, stale, blocked, or likely incomplete, ordinary workflows continue with live repository evidence and recommend `sp-map-update` or `sp-map-scan -> sp-map-build` as follow-up map maintenance. Map-specific workflows and validation commands still validate their own artifacts.
```

Replace:

```markdown
- Treat project cognition as the primary runtime truth surface.
```

with:

```markdown
- Treat project cognition as an advisory navigation index. Code, tests, scripts, configuration, and authoritative docs are the evidence sources.
```

Replace:

```markdown
- Ordinary `sp-*` workflows should treat project cognition consumption as the hard gate before source-level work.
```

with:

```markdown
- Ordinary `sp-*` workflows should use project cognition when helpful, but should continue with live repository evidence when the map is missing, stale, blocked, or incomplete.
```

- [ ] **Step 5: Update generated constitution wording**

In `templates/constitution-template.md` and `templates/constitution/profiles/product.yml`, replace "default brownfield runtime truth surface" with:

```markdown
advisory project cognition index
```

Add this sentence near the cognition guidance:

```markdown
Map points, code proves: technical claims and completion claims must be backed by live project evidence, not by project cognition output alone.
```

- [ ] **Step 6: Run documentation tests and commit**

Run:

```bash
pytest tests/test_constitution_defaults.py tests/test_constitution_profiles_cli.py tests/test_project_handbook_templates.py tests/test_alignment_templates.py tests/test_passive_skill_guidance.py -q
```

Expected: all selected tests pass.

Commit:

```bash
git add README.md PROJECT-HANDBOOK.md templates/constitution-template.md templates/constitution/profiles/product.yml tests/test_constitution_defaults.py tests/test_constitution_profiles_cli.py tests/test_project_handbook_templates.py tests/test_alignment_templates.py tests/test_passive_skill_guidance.py
git commit -m "docs: align public cognition advisory policy"
```

---

### Task 8: Preserve Map-Specific Validation And Compatibility Payloads

**Files:**
- Modify only if needed: `tests/integrations/test_cli.py`
- Modify only if needed: `tests/contract/test_hook_cli_surface.py`
- No intended changes: `src/specify_cli/cognition/validation.py`
- No intended changes: `src/specify_cli/cognition/query.py`
- No intended changes: `src/specify_cli/cognition/update.py`

- [ ] **Step 1: Run map-specific validation tests**

Run:

```bash
pytest tests/integrations/test_cli.py::test_project_cognition_validate_build_blocks_empty_runtime_json tests/integrations/test_cli.py::test_project_cognition_validate_scan_blocks_empty_package_json tests/integrations/test_cli.py::test_project_cognition_complete_refresh_blocks_without_query_ready_runtime_json -q
```

Expected: tests pass. If they fail because a previous task accidentally weakened map-maintenance validation, revert that weakening and keep validation blocking inside map-specific commands.

- [ ] **Step 2: Run readiness payload compatibility tests**

Run:

```bash
pytest tests/integrations/test_cli.py -q -k "project_cognition_query or project_cognition_lexicon or needs_rebuild or needs_update"
```

Expected: tests pass or fail only on wording assertions. Do not remove `needs_update`, `needs_rebuild`, `recommended_next_action`, or readiness fields from payloads.

- [ ] **Step 3: Add a compatibility assertion if missing**

If no existing test asserts readiness fields remain, add this to `tests/integrations/test_cli.py` near the project cognition query tests:

```python
def test_project_cognition_query_keeps_readiness_payload_shape(tmp_path):
    project = tmp_path / "project-cognition-query-shape"
    project.mkdir()
    result = runner.invoke(app, ["project-cognition", "query", "--intent", "implement", "--query-plan", "{}", "--format", "json"])
    payload = json.loads(result.output)

    assert "readiness" in payload
    assert "recommended_next_action" in payload
```

Run the single new test:

```bash
pytest tests/integrations/test_cli.py::test_project_cognition_query_keeps_readiness_payload_shape -q
```

Expected: pass after importing or reusing the module's existing runner fixture pattern.

- [ ] **Step 4: Commit compatibility test updates if any**

If Task 8 changed tests, commit:

```bash
git add tests/integrations/test_cli.py tests/contract/test_hook_cli_surface.py
git commit -m "test: preserve cognition readiness payload compatibility"
```

If no files changed, skip this commit.

---

### Task 9: Full Verification And Cleanup

**Files:**
- Verify all changed files.
- Modify no files unless verification exposes missed references.

- [ ] **Step 1: Search for forbidden ordinary-workflow wording**

Run:

```bash
rg -n "runtime truth surface|mandatory pre-source|hard gate before source-level|treat this as a hard gate|needs_update`: route through|needs_rebuild`: route through|wait for that rebuild before continuing" templates src README.md PROJECT-HANDBOOK.md tests
```

Expected: no matches in ordinary workflow guidance. Matches are acceptable only when a test is asserting absence, a spec/design document describes the old behavior, or a map-maintenance command validates its own artifacts.

- [ ] **Step 2: Search for forced dirty/finalizer completion guidance**

Run:

```bash
rg -n "mark-dirty|complete-refresh|validate-build --format json" templates/commands src/specify_cli/integrations/base.py README.md PROJECT-HANDBOOK.md
```

Expected: matches remain in map-maintenance commands, CLI command docs, and explicit map-maintenance guidance. Ordinary completion guidance should recommend `sp-map-update` instead of requiring `mark-dirty`, `complete-refresh`, or `validate-build`.

- [ ] **Step 3: Run focused changed-area suite**

Run:

```bash
pytest tests/test_project_map_hard_gate_guidance.py tests/hooks/test_preflight_hooks.py tests/contract/test_codex_team_auto_dispatch_cli.py tests/debug/test_debug_cli_preflight.py tests/test_alignment_templates.py tests/test_debug_template_guidance.py tests/test_quick_template_guidance.py tests/test_map_runtime_template_guidance.py tests/test_constitution_defaults.py tests/test_constitution_profiles_cli.py tests/test_project_handbook_templates.py tests/test_passive_skill_guidance.py -q
```

Expected: pass.

- [ ] **Step 4: Run integration guidance suite**

Run:

```bash
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_codex.py -q
```

Expected: pass.

- [ ] **Step 5: Run broader regression suite**

Run:

```bash
pytest -q
```

Expected: pass. If runtime is too slow, run the focused suite plus all failed-test files from collection, then record the skipped broad run in the final handoff.

- [ ] **Step 6: Review git diff**

Run:

```bash
git diff --stat
git diff -- src templates tests README.md PROJECT-HANDBOOK.md
```

Expected:

- Runtime consumers warn on cognition freshness instead of blocking ordinary work.
- Map-specific validation commands still block/fail on invalid map artifacts.
- Generated guidance says project cognition is advisory.
- Docs say "map points, code proves".
- Readiness payload fields remain.

- [ ] **Step 7: Final commit**

If prior tasks made uncommitted cleanup changes, commit:

```bash
git add src templates tests README.md PROJECT-HANDBOOK.md
git commit -m "chore: finish advisory cognition map rollout"
```

If the worktree is clean because each task committed its changes, skip this commit.

---

## Implementation Notes

- Do not change the SQLite schema unless a test proves a schema bug unrelated to this policy.
- Do not remove readiness states from `project-cognition query` or `project-cognition lexicon` payloads.
- Do not weaken `project-cognition validate-scan`, `project-cognition validate-build`, `publish-runtime-metadata`, `complete-refresh`, or map-update validation inside map-maintenance flows.
- Do not rely on project cognition output as evidence in new wording. Use "navigation", "advisory", "map quality", and "follow-up map maintenance".
- Prefer "recommend `sp-map-update`" over "run `sp-map-update` before continuing" in ordinary workflows.
- Preserve true non-map blockers: invalid workflow state, active analyze gate, integrate readiness, missing result files, baseline build blocked, malformed team runtime state, invalid JSON, or explicit user-requested map repair.
