# Project Map Retirement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retire `.specify/project-map/**` from new generated runtime workflows while preserving `specify project-map ...` as a legacy CLI alias and making generated cognition helper commands launcher-backed.

**Architecture:** Move the required runtime and workbench contract to `.specify/project-cognition/**`, update the Python CLI/freshness helpers so `project-cognition` status is canonical, and then sweep generated templates, integration addenda, scripts, docs, and tests so new projects no longer install, read, write, or require project-map assets. Keep compatibility alias command registration intact, but make all new guidance use `project-cognition` and `{{specify-subcmd:...}}`.

**Tech Stack:** Python Typer CLI in `src/specify_cli`, project cognition status helpers, Markdown workflow templates and passive skills, Bash/PowerShell generated helper scripts, integration installers, pytest integration/template/contract tests.

---

## File Structure

```text
MODIFY
  src/specify_cli/project_cognition_status.py
    Purpose: make cognition status paths canonical, keep legacy project-map read fallback, stop writing legacy project-map status for new status writes, and classify retired project-map paths as reference-only.

  src/specify_cli/__init__.py
    Purpose: seed `.specify/project-cognition/status.json` on init, stop requiring project-map artifacts for refresh finalizers, skip installing project-map template assets for new projects, and update user-facing command/help wording.

  src/specify_cli/integrations/base.py
    Purpose: render runtime cognition gate addenda with `{{specify-subcmd:project-cognition ...}}` instead of bare `specify ...` and remove project-map runtime wording from generated addenda.

  src/specify_cli/integrations/codex/__init__.py
  src/specify_cli/integrations/claude/templates/implement-teams.md
  src/specify_cli/integrations/{gemini,copilot,cursor_agent}/__init__.py
    Purpose: remove project-map compatibility/export read guidance from new generated integration text, except explicit legacy notes where necessary.

  templates/commands/*.md
  templates/command-partials/**/*.md
  templates/passive-skills/**/*.md
  templates/project-handbook-template.md
    Purpose: remove project-map runtime reads, migrate map workbench paths to `.specify/project-cognition/workbench/**`, and replace bare helper commands with launcher-backed `{{specify-subcmd:project-cognition ...}}`.

  scripts/bash/common.sh
  scripts/powershell/common.ps1
  scripts/bash/check-prerequisites.sh
  scripts/powershell/check-prerequisites.ps1
  scripts/bash/update-agent-context.sh
  scripts/powershell/update-agent-context.ps1
    Purpose: expose cognition status/helper paths instead of project-map status/helper paths in generated scripts and managed AGENTS blocks.

  pyproject.toml
    Purpose: stop force-including `templates/project-map` as a required generated template asset once init no longer installs it.

  README.md
  PROJECT-HANDBOOK.md
  docs/quickstart.md
  docs/upgrade.md
    Purpose: document `project-cognition` as the only new runtime path and `project-map` as legacy CLI compatibility only.

TESTS TO MODIFY
  tests/test_project_map_status.py
  tests/integrations/test_cli.py
  tests/integrations/test_integration_base_markdown.py
  tests/integrations/test_integration_base_skills.py
  tests/integrations/test_integration_base_toml.py
  tests/integrations/test_integration_codex.py
  tests/integrations/test_integration_claude.py
  tests/integrations/test_integration_copilot.py
  tests/integrations/test_integration_cursor_agent.py
  tests/integrations/test_integration_gemini.py
  tests/integrations/test_integration_generic.py
  tests/test_map_scan_build_template_guidance.py
  tests/test_map_runtime_template_guidance.py
  tests/test_alignment_templates.py
  tests/test_project_map_hard_gate_guidance.py
  tests/test_project_handbook_templates.py
  tests/test_command_surface_semantics.py
  tests/test_hook_template_guidance.py
  tests/test_agent_context_managed_block.py
  tests/test_passive_skill_guidance.py
  tests/test_graph_native_downstream_adoption.py
    Purpose: lock the new no-project-map runtime contract, launcher-backed helper rendering, and legacy alias compatibility.

LEAVE IN PLACE FOR COMPATIBILITY
  src/specify_cli/project_map_status.py
  src/specify_cli/hooks/project_map.py
  scripts/bash/project-map-freshness.sh
  scripts/powershell/project-map-freshness.ps1
  templates/project-map/**
    Purpose: keep legacy imports, hooks, scripts, and dormant template assets available for old projects during this phase. They must not be installed or required by new projects.
```

---

## Task 1: Lock Canonical Cognition Status With Failing CLI Tests

**Files:**
- Modify: `tests/test_project_map_status.py`
- Modify: `tests/integrations/test_cli.py`

- [ ] **Step 1: Add a status-path test that expects cognition status as canonical**

In `tests/test_project_map_status.py`, replace `test_project_map_status_round_trip` with two narrower tests:

```python
def test_project_cognition_status_round_trip_writes_canonical_status(tmp_path):
    mod = _load_module()
    _write_cognition_baseline(tmp_path)

    status = mod.ProjectMapStatus(
        version=2,
        global_freshness="fresh",
        global_last_refresh_commit="abc123",
        global_last_refresh_at="2026-04-21T00:00:00Z",
        global_stale_reasons=[],
        global_affected_root_docs=["WORKFLOWS.md"],
        modules={
            "specify-cli-core": {
                "freshness": "fresh",
                "deep_status": "deep_stale",
                "last_refresh_commit": "abc123",
                "coverage_fingerprint": "sha256:test",
                "stale_reasons": [],
                "affected_docs": ["WORKFLOWS.md"],
            }
        },
    )

    written = mod.write_project_map_status(tmp_path, status)
    loaded = mod.read_project_map_status(tmp_path)

    assert written == tmp_path / ".specify" / "project-cognition" / "status.json"
    assert not (tmp_path / ".specify" / "project-map" / "status.json").exists()
    assert not (tmp_path / ".specify" / "project-map" / "index" / "status.json").exists()
    assert loaded.version == 2
    assert loaded.global_last_refresh_commit == "abc123"
    assert loaded.global_freshness == "fresh"
    assert loaded.global_affected_root_docs == ["WORKFLOWS.md"]
    assert loaded.modules["specify-cli-core"]["deep_status"] == "deep_stale"
```

Add a legacy fallback test immediately after it:

```python
def test_read_project_cognition_status_preserves_legacy_project_map_fallback(tmp_path):
    mod = _load_module()
    legacy_path = tmp_path / ".specify" / "project-map" / "index" / "status.json"
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text(
        (
            '{"version": 2, "global_freshness": "fresh", '
            '"global_last_refresh_commit": "legacy123", '
            '"global_last_refresh_at": "2026-04-21T00:00:00Z"}\n'
        ),
        encoding="utf-8",
    )

    loaded = mod.read_project_map_status(tmp_path)

    assert loaded.version == 2
    assert loaded.global_last_refresh_commit == "legacy123"
    assert loaded.global_freshness == "fresh"
```

- [ ] **Step 2: Add init CLI assertions for no project-map runtime status**

In `tests/integrations/test_cli.py`, rename `test_project_map_status_and_check_commands_render_seeded_state` to `test_project_cognition_status_and_check_commands_render_seeded_state_without_project_map`. Change the command invocations and assertions to:

```python
status_result = runner.invoke(app, ["project-cognition", "status", "--format", "json"], catch_exceptions=False)
check_result = runner.invoke(app, ["project-cognition", "check", "--format", "json"], catch_exceptions=False)
```

and:

```python
assert (project / ".specify" / "project-cognition" / "status.json").exists()
assert not (project / ".specify" / "project-map" / "status.json").exists()
assert not (project / ".specify" / "project-map" / "index" / "status.json").exists()
assert status_payload["freshness"] == "missing"
assert status_payload["status_path"].replace("\\", "/").endswith(".specify/project-cognition/status.json")
assert check_payload["freshness"] == "possibly_stale"
assert check_payload["state"] == "runtime_stale"
assert check_payload["reasons"] == ["git baseline unavailable for project cognition freshness"]
```

Keep a separate alias compatibility test:

```python
def test_project_map_namespace_remains_legacy_alias_for_cognition_status(self, tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    project = tmp_path / "project-map-legacy-alias"
    project.mkdir()
    runner = CliRunner()

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        init_result = runner.invoke(
            app,
            [
                "init",
                "--here",
                "--ai",
                "claude",
                "--script",
                "sh",
                "--no-git",
                "--ignore-agent-tools",
            ],
            catch_exceptions=False,
        )
        alias_result = runner.invoke(app, ["project-map", "status", "--format", "json"], catch_exceptions=False)
    finally:
        os.chdir(old_cwd)

    assert init_result.exit_code == 0, init_result.output
    assert alias_result.exit_code == 0, alias_result.output
    payload = json.loads(alias_result.output)
    assert payload["status_path"].replace("\\", "/").endswith(".specify/project-cognition/status.json")
```

- [ ] **Step 3: Run the focused failing tests**

Run:

```powershell
pytest tests/test_project_map_status.py::test_project_cognition_status_round_trip_writes_canonical_status tests/test_project_map_status.py::test_read_project_cognition_status_preserves_legacy_project_map_fallback tests/integrations/test_cli.py::TestCLI::test_project_cognition_status_and_check_commands_render_seeded_state_without_project_map tests/integrations/test_cli.py::TestCLI::test_project_map_namespace_remains_legacy_alias_for_cognition_status -q
```

Expected: fail because writes still target `.specify/project-map/index/status.json`, init records legacy status paths, and the copy still says project-map freshness.

---

## Task 2: Make Cognition Status Canonical While Preserving Legacy Reads

**Files:**
- Modify: `src/specify_cli/project_cognition_status.py`
- Modify: `src/specify_cli/__init__.py`
- Modify: `tests/test_project_map_status.py`
- Modify: `tests/integrations/test_cli.py`

- [ ] **Step 1: Change canonical status path helpers**

In `src/specify_cli/project_cognition_status.py`, add these helpers near the existing `project_map_status_path` functions:

```python
def project_cognition_status_metadata_path(project_root: Path) -> Path:
    return cognition_status_path(project_root)


def legacy_project_map_status_paths(project_root: Path) -> tuple[Path, Path]:
    return (
        project_map_status_path(project_root),
        legacy_project_map_status_path(project_root),
    )
```

- [ ] **Step 2: Update read/write status functions**

Replace `read_project_map_status` and `write_project_map_status` with:

```python
def read_project_map_status(project_root: Path) -> ProjectMapStatus:
    canonical_path = project_cognition_status_metadata_path(project_root)
    if canonical_path.exists():
        shared_status = read_scan_status(canonical_path, status_family="project-cognition")
        if shared_status.raw_payload:
            return ProjectMapStatus.from_dict(shared_status.raw_payload)
    for status_path in legacy_project_map_status_paths(project_root):
        if not status_path.exists():
            continue
        shared_status = read_scan_status(status_path, status_family="project-map")
        if not shared_status.raw_payload:
            continue
        return ProjectMapStatus.from_dict(shared_status.raw_payload)
    return ProjectMapStatus()


def write_project_map_status(project_root: Path, status: ProjectMapStatus) -> Path:
    status_path = project_cognition_status_metadata_path(project_root)
    payload = status.to_dict()
    write_scan_payload(status_path, payload)
    _write_cognition_freshness_metadata(project_root, status)
    return status_path
```

- [ ] **Step 3: Preserve cognition runtime fields when writing freshness metadata**

In `_write_cognition_freshness_metadata`, keep current merge behavior but ensure these fields survive:

```python
graph_store_path=cognition_status.graph_store_path,
active_generation_id=cognition_status.active_generation_id,
query_contract_version=cognition_status.query_contract_version,
update_contract_version=cognition_status.update_contract_version,
```

Place them in the `CognitionStatus(...)` constructor alongside existing fields.

- [ ] **Step 4: Update init seeding and manifest recording**

In `src/specify_cli/__init__.py`, in the init seeding block, replace:

```python
status_path = project_map_status_path(project_path)
if not status_path.exists():
    write_project_map_status(project_path, ProjectMapStatus())
    manifest.record_existing(status_path.relative_to(project_path).as_posix())
    legacy_status_path = legacy_project_map_status_path(project_path)
    if legacy_status_path.exists():
        manifest.record_existing(legacy_status_path.relative_to(project_path).as_posix())
```

with:

```python
status_path = cognition_status_path(project_path)
if not status_path.exists():
    written_status = write_project_map_status(project_path, ProjectMapStatus())
    manifest.record_existing(written_status.relative_to(project_path).as_posix())
```

Add `cognition_status_path` to the import list from `specify_cli.cognition` if it is not already imported.

- [ ] **Step 5: Update no-git reason copy**

Find the reason string `git baseline unavailable for project-map compatibility/export freshness` in `src/specify_cli/project_cognition_status.py` and replace it with:

```python
"git baseline unavailable for project cognition freshness"
```

- [ ] **Step 6: Run focused status tests**

Run the same command from Task 1 Step 3.

Expected: pass.

- [ ] **Step 7: Commit**

```powershell
git add src/specify_cli/project_cognition_status.py src/specify_cli/__init__.py tests/test_project_map_status.py tests/integrations/test_cli.py
git commit -m "feat: make project cognition status canonical"
```

---

## Task 3: Stop Refresh Finalizers From Requiring Project-Map Artifacts

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Modify: `tests/integrations/test_cli.py`
- Modify: `tests/contract/test_hook_cli_surface.py`
- Modify: `src/specify_cli/hooks/project_cognition.py`

- [ ] **Step 1: Replace record-refresh and complete-refresh failure tests**

In `tests/integrations/test_cli.py`, replace `test_project_map_record_refresh_requires_canonical_outputs` with:

```python
def test_project_cognition_record_refresh_does_not_require_project_map_outputs(self, tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    project = tmp_path / "project-cognition-record-refresh"
    project.mkdir()
    runner = CliRunner()

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        init_result = runner.invoke(
            app,
            ["init", "--here", "--ai", "claude", "--script", "sh", "--no-git", "--ignore-agent-tools"],
            catch_exceptions=False,
        )
        result = runner.invoke(app, ["project-cognition", "record-refresh", "--reason", "manual", "--format", "json"])
    finally:
        os.chdir(old_cwd)

    assert init_result.exit_code == 0, init_result.output
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["freshness"] == "fresh"
    assert payload["status_path"].replace("\\", "/").endswith(".specify/project-cognition/status.json")
```

Replace `test_project_map_complete_refresh_records_map_build_reason` setup so it no longer writes `PROJECT-HANDBOOK.md` or `.specify/project-map/**`. Invoke:

```python
complete_result = runner.invoke(app, ["project-cognition", "complete-refresh", "--format", "json"])
status_result = runner.invoke(app, ["project-cognition", "status", "--format", "json"])
```

Assert:

```python
assert complete_payload["last_refresh_reason"] == "map-build"
assert status_payload["status_path"].replace("\\", "/").endswith(".specify/project-cognition/status.json")
assert not (project / ".specify" / "project-map").exists()
```

- [ ] **Step 2: Update hook complete-refresh wording test**

In `tests/contract/test_hook_cli_surface.py`, find assertions that expect `"project-map complete-refresh"` for git baseline errors. Change them to expect:

```python
"project-cognition complete-refresh"
```

and ensure the hook event remains `project_cognition.complete_refresh`.

- [ ] **Step 3: Remove project-map artifact checks from CLI finalizers**

In `src/specify_cli/__init__.py`, update these functions:

- `project_map_record_refresh`
- `project_map_complete_refresh`
- `project_map_refresh_topics_command`

Remove calls to `_ensure_project_map_artifacts_exist(project_root)`.

Change docstrings:

```python
"""Low-level/manual recovery path to record a fresh project cognition baseline at the current HEAD."""
```

and:

```python
"""Finalize a successful project cognition refresh by recording a fresh git baseline."""
```

Update `_ensure_project_map_artifacts_exist` error text only if the function remains for legacy internal callers; it should not be used by these finalizers.

- [ ] **Step 4: Update hook error text**

In `src/specify_cli/hooks/project_cognition.py`, change:

```python
errors=["git baseline unavailable for project-map complete-refresh"],
```

to:

```python
errors=["git baseline unavailable for project-cognition complete-refresh"],
```

- [ ] **Step 5: Run focused refresh tests**

Run:

```powershell
pytest tests/integrations/test_cli.py::TestCLI::test_project_cognition_record_refresh_does_not_require_project_map_outputs tests/integrations/test_cli.py::TestCLI::test_project_map_complete_refresh_records_map_build_reason tests/contract/test_hook_cli_surface.py::test_hook_complete_refresh_accepts_json_format_alias -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```powershell
git add src/specify_cli/__init__.py src/specify_cli/hooks/project_cognition.py tests/integrations/test_cli.py tests/contract/test_hook_cli_surface.py
git commit -m "fix: finalize cognition refresh without project-map outputs"
```

---

## Task 4: Migrate Map-Scan And Map-Build Workbench Paths

**Files:**
- Modify: `templates/commands/map-scan.md`
- Modify: `templates/commands/map-build.md`
- Modify: `templates/commands/map-update.md`
- Modify: `templates/command-partials/map-scan/shell.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `tests/test_map_scan_build_template_guidance.py`
- Modify: `tests/test_map_runtime_template_guidance.py`

- [ ] **Step 1: Update template tests to expect cognition workbench paths**

In `tests/test_map_scan_build_template_guidance.py`, update path assertions:

```python
assert ".specify/project-cognition/workbench/map-scan.md" in content
assert ".specify/project-cognition/workbench/coverage-ledger.md" in content
assert ".specify/project-cognition/workbench/coverage-ledger.json" in content
assert ".specify/project-cognition/workbench/scan-packets/lane-auth.md" in content
assert ".specify/project-cognition/workbench/map-state.md" in content
assert "MAP_STATE_FILE=.specify/project-cognition/workbench/map-state.md" in content
assert ".specify/project-map/" not in content
```

For build template assertions, replace:

```python
assert ".specify/project-map/worker-results/packet-auth-001.json" in content
```

with:

```python
assert ".specify/project-cognition/workbench/worker-results/packet-auth-001.json" in content
assert ".specify/project-map/" not in content
```

Replace truth ledger assertions:

```python
assert ".specify/project-cognition/workbench/repository-universe.json" in content
assert ".specify/project-cognition/workbench/capability-ledger.json" in content
assert ".specify/project-cognition/workbench/control-ledger.json" in content
```

- [ ] **Step 2: Remove handbook-output expectations**

In `test_map_build_template_requires_truth_layer_outputs`, replace handbook assertions:

```python
assert "DEBUG-HANDBOOK.md" not in content
assert "BUILD-HANDBOOK.md" not in content
assert "DEBUG-WORKFLOW-CONTRACT" not in content
assert "BUILD-WORKFLOW-CONTRACT" not in content
```

and add:

```python
assert ".specify/project-cognition/project-cognition.db" in content
assert "queryable task-oriented cognition bundles" in lowered
```

- [ ] **Step 3: Update map templates**

In `templates/commands/map-scan.md`, replace every `.specify/project-map/` workbench path with `.specify/project-cognition/workbench/`.

Remove required output references to:

- `.specify/project-map/QUICK-NAV.md`
- project-map root/module handbook outputs

Keep the command intent as scan evidence collection, not final truth publication.

In `templates/commands/map-build.md`, replace required inputs:

```markdown
- `.specify/project-map/coverage-ledger.json`
- `.specify/project-map/scan-packets/`
```

with:

```markdown
- `.specify/project-cognition/workbench/coverage-ledger.json`
- `.specify/project-cognition/workbench/scan-packets/`
```

Replace output:

```markdown
- `.specify/project-map/worker-results/packet-auth-001.json`
```

with:

```markdown
- `.specify/project-cognition/workbench/worker-results/packet-auth-001.json`
```

Remove the `Runtime Compatibility Outputs` section. In the completion rule, replace the finalizer with:

```markdown
- use `{{specify-subcmd:project-cognition complete-refresh --format json}}` once the query-ready baseline has been accepted
- confirm that `.specify/project-cognition/project-cognition.db` was written and can be queried through `{{specify-subcmd:project-cognition query --intent implement --query "$ARGUMENTS" --format json}}`
```

- [ ] **Step 4: Update map-update finalizer text**

In `templates/commands/map-update.md`, replace `specify project-map complete-refresh` references with:

```markdown
{{specify-subcmd:project-cognition complete-refresh --format json}}
```

Replace `compatibility finalizer` wording with `cognition refresh finalizer`.

- [ ] **Step 5: Run map template tests**

Run:

```powershell
pytest tests/test_map_scan_build_template_guidance.py tests/test_map_runtime_template_guidance.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```powershell
git add templates/commands/map-scan.md templates/commands/map-build.md templates/commands/map-update.md templates/command-partials/map-scan/shell.md templates/project-handbook-template.md tests/test_map_scan_build_template_guidance.py tests/test_map_runtime_template_guidance.py
git commit -m "refactor: move map workbench under project cognition"
```

---

## Task 5: Make Generated Helper Commands Launcher-Backed

**Files:**
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `templates/commands/{analyze,checklist,clarify,debug,deep-research,fast,implement,plan,prd-scan,quick,specify,tasks,test-build,test-scan}.md`
- Modify: `templates/command-partials/**/*.md`
- Modify: `templates/passive-skills/**/*.md`
- Modify: `src/specify_cli/integrations/claude/templates/implement-teams.md`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_project_map_hard_gate_guidance.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_base_toml.py`

- [ ] **Step 1: Update source-template assertions for launcher placeholders**

In `tests/test_alignment_templates.py`, change assertions that require literal source strings like:

```python
assert "specify project-cognition query --intent plan" in content
```

to:

```python
assert "{{specify-subcmd:project-cognition query --intent plan" in content
```

Keep generated integration tests checking rendered output contains `project-cognition query` and does not contain `{{specify-subcmd:`.

- [ ] **Step 2: Add no bare helper command regression**

Add this helper to `tests/test_alignment_templates.py`:

```python
def test_generated_workflow_templates_use_launcher_backed_cognition_helpers() -> None:
    command_dir = PROJECT_ROOT / "templates" / "commands"
    offenders: list[str] = []
    for path in command_dir.glob("*.md"):
        content = path.read_text(encoding="utf-8")
        for bare in (
            "specify project-cognition query",
            "specify project-cognition complete-refresh",
            "specify project-cognition mark-dirty",
            "specify project-map complete-refresh",
            "specify project-map mark-dirty",
        ):
            if bare in content:
                offenders.append(f"{path.relative_to(PROJECT_ROOT)} contains {bare}")
    assert offenders == []
```

- [ ] **Step 3: Update integration base addendum**

In `src/specify_cli/integrations/base.py`, change `_project_cognition_query_gate_line` to:

```python
return (
    "**Crucial First Step**: You MUST query project cognition first with "
    f"`{{{{specify-subcmd:project-cognition query --intent {intent} --query \"$ARGUMENTS\" --format json}}}}` "
    f"{command_step}, then use the returned readiness, task-local bundle, and `minimal_live_reads`."
)
```

This keeps source/generated processing centralized.

- [ ] **Step 4: Replace bare query command blocks in command templates**

For each affected command template, replace command examples:

```markdown
specify project-cognition query --intent plan --query "$ARGUMENTS" --format json
```

with:

```markdown
{{specify-subcmd:project-cognition query --intent plan --query "$ARGUMENTS" --format json}}
```

Use these intent mappings:

- `specify`, `clarify`, `plan`, `tasks`, `checklist`: `plan`
- `implement`, `quick`, `fast`, `analyze`: `implement`
- `debug`: `debug`
- `deep-research`, `prd-scan`: `research`
- `test-scan`, `test-build`: `test`

- [ ] **Step 5: Replace refresh/dirty command examples**

Replace:

```markdown
specify project-map complete-refresh
specify project-map mark-dirty --reason "workflow contract changed"
```

with:

```markdown
{{specify-subcmd:project-cognition complete-refresh --format json}}
{{specify-subcmd:project-cognition mark-dirty --reason "workflow contract changed" --format json}}
```

Preserve optional origin arguments where present:

```markdown
{{specify-subcmd:project-cognition mark-dirty --reason "workflow contract changed" --origin-command implement --origin-feature-dir "$FEATURE_DIR" --origin-lane-id "$LANE_ID" --packet-file "$PACKET_FILE" --format json}}
```

- [ ] **Step 6: Run template and generated integration tests**

Run:

```powershell
pytest tests/test_alignment_templates.py tests/test_project_map_hard_gate_guidance.py tests/integrations/test_integration_codex.py::test_codex_generated_skills_render_launcher_backed_runtime_commands tests/integrations/test_integration_base_markdown.py::TestMarkdownIntegrationBase::test_runtime_commands_hard_gate_project_cognition_reads tests/integrations/test_integration_base_skills.py::TestSkillsIntegrationBase::test_runtime_commands_hard_gate_project_cognition_reads tests/integrations/test_integration_base_toml.py::TestTomlIntegrationBase::test_runtime_commands_hard_gate_project_cognition_reads -q
```

Expected: pass after source templates use placeholders and generated outputs render them.

- [ ] **Step 7: Commit**

```powershell
git add src/specify_cli/integrations/base.py templates/commands templates/command-partials templates/passive-skills src/specify_cli/integrations/claude/templates/implement-teams.md tests/test_alignment_templates.py tests/test_project_map_hard_gate_guidance.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py
git commit -m "fix: render cognition helpers through project launcher"
```

---

## Task 6: Stop Installing Project-Map Assets In New Projects

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Modify: `pyproject.toml`
- Modify: `tests/integrations/test_cli.py`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/integrations/test_integration_claude.py`
- Modify: `tests/integrations/test_integration_copilot.py`
- Modify: `tests/integrations/test_integration_generic.py`

- [ ] **Step 1: Update init inventory tests**

In integration inventory helpers, remove these expected files:

```python
files.append(".specify/project-map/status.json")
files.append(".specify/project-map/index/status.json")
```

and assert only:

```python
files.append(".specify/project-cognition/status.json")
```

For project template assets, remove assertions that these files exist in new projects:

```python
".specify/templates/project-map/QUICK-NAV.md"
".specify/templates/project-map/root/ARCHITECTURE.md"
".specify/templates/project-map/root/OPERATIONS.md"
```

Add assertions:

```python
assert not (project / ".specify" / "templates" / "project-map").exists()
assert not (project / ".specify" / "project-map").exists()
```

Apply this to the source checkout init tests and Codex/Claude/Copilot/Generic integration tests that currently expect project-map assets.

- [ ] **Step 2: Skip project-map while copying source templates**

In `src/specify_cli/__init__.py`, inside:

```python
for src_path in templates_src.rglob("*"):
```

after `rel_path = src_path.relative_to(templates_src)`, add:

```python
if rel_path.parts and rel_path.parts[0] == "project-map":
    continue
```

This prevents source-checkout init from copying `templates/project-map/**`.

- [ ] **Step 3: Stop mirroring wheel project-map extra template directory**

In the `extra_template_dirs` tuple, remove `"project-map"` so it becomes:

```python
extra_template_dirs = (
    "command-partials",
    "passive-skills",
    "worker-prompts",
)
```

- [ ] **Step 4: Remove project-map force include from package config**

In `pyproject.toml`, remove:

```toml
"templates/project-map" = "specify_cli/core_pack/project-map"
```

Leave `templates/project-map/**` in the repo for now.

- [ ] **Step 5: Run init inventory tests**

Run:

```powershell
pytest tests/integrations/test_cli.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_copilot.py tests/integrations/test_integration_generic.py -q
```

Expected: pass after expected inventory and init behavior align.

- [ ] **Step 6: Commit**

```powershell
git add src/specify_cli/__init__.py pyproject.toml tests/integrations
git commit -m "refactor: stop installing project-map runtime assets"
```

---

## Task 7: Update Generated Scripts And Managed AGENTS Blocks

**Files:**
- Modify: `scripts/bash/common.sh`
- Modify: `scripts/powershell/common.ps1`
- Modify: `scripts/bash/check-prerequisites.sh`
- Modify: `scripts/powershell/check-prerequisites.ps1`
- Modify: `scripts/bash/update-agent-context.sh`
- Modify: `scripts/powershell/update-agent-context.ps1`
- Modify: `tests/test_agent_context_managed_block.py`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_claude.py`
- Modify: `tests/integrations/test_integration_copilot.py`
- Modify: `tests/integrations/test_integration_generic.py`

- [ ] **Step 1: Add cognition path helpers to Bash common**

In `scripts/bash/common.sh`, add:

```bash
project_cognition_dir() {
    local repo_root="${1:-$(get_repo_root)}"
    echo "$repo_root/.specify/project-cognition"
}

project_cognition_status_path() {
    local repo_root="${1:-$(get_repo_root)}"
    echo "$(project_cognition_dir "$repo_root")/status.json"
}

project_cognition_helper_path() {
    local repo_root="${1:-$(get_repo_root)}"
    echo "$repo_root/.specify/scripts/bash/project-map-freshness.sh"
}
```

Keep old `project_map_*` helpers as compatibility wrappers, but have `project_map_status_path` return `project_cognition_status_path`:

```bash
project_map_status_path() {
    local repo_root="${1:-$(get_repo_root)}"
    project_cognition_status_path "$repo_root"
}
```

- [ ] **Step 2: Add cognition helpers to PowerShell common**

In `scripts/powershell/common.ps1`, add:

```powershell
function Get-ProjectCognitionDir {
    param([string]$RepoRoot = (Get-RepoRoot))
    return (Join-Path $RepoRoot ".specify/project-cognition")
}

function Get-ProjectCognitionStatusPath {
    param([string]$RepoRoot = (Get-RepoRoot))
    return (Join-Path (Get-ProjectCognitionDir -RepoRoot $RepoRoot) "status.json")
}

function Get-ProjectCognitionHelperPath {
    param([string]$RepoRoot = (Get-RepoRoot))
    return (Join-Path $RepoRoot ".specify/scripts/powershell/project-map-freshness.ps1")
}
```

If `Get-ProjectMapStatusPath` exists, make it return `Get-ProjectCognitionStatusPath`.

- [ ] **Step 3: Update check-prerequisites JSON keys**

In `scripts/bash/check-prerequisites.sh`, replace output keys:

```bash
PROJECT_MAP_STATUS
PROJECT_MAP_HELPER
```

with:

```bash
PROJECT_COGNITION_STATUS
PROJECT_COGNITION_HELPER
```

Use `project_cognition_status_path` and `project_cognition_helper_path`.

In `scripts/powershell/check-prerequisites.ps1`, use:

```powershell
PROJECT_COGNITION_STATUS = (Get-ProjectCognitionStatusPath -RepoRoot $paths.REPO_ROOT)
PROJECT_COGNITION_HELPER = (Get-ProjectCognitionHelperPath -RepoRoot $paths.REPO_ROOT)
```

Keep old keys only if existing tests require backwards compatibility; if kept, set them equal to the cognition values and mark them compatibility in text output.

- [ ] **Step 4: Update managed AGENTS block text**

In `scripts/bash/update-agent-context.sh` and `scripts/powershell/update-agent-context.ps1`, replace generated block bullets:

```text
specify project-cognition query ...
specify project-map complete-refresh
specify project-map mark-dirty
Supporting handbook/project-map artifacts under `.specify/project-map/`
```

with:

```text
{{specify-subcmd:project-cognition query --intent implement --query "$ARGUMENTS" --format json}}
{{specify-subcmd:project-cognition complete-refresh --format json}}
{{specify-subcmd:project-cognition mark-dirty --reason "workflow contract changed" --format json}}
Project cognition under `.specify/project-cognition/` is the runtime truth surface.
```

These scripts write final AGENTS text, not processed command templates, so do not literally leave `{{specify-subcmd:...}}` if the managed block is not passed through the launcher renderer. Use plain `specify project-cognition ...` only in AGENTS prose when no renderer is available. Add a sentence:

```text
When a project launcher is configured in `.specify/config.json`, use that launcher instead of PATH `specify`.
```

- [ ] **Step 5: Update managed block tests**

In `tests/test_agent_context_managed_block.py`, assert:

```python
assert ".specify/project-cognition/status.json" in lower
assert ".specify/project-map/" not in lower
assert "project-cognition complete-refresh" in lower
assert "project-cognition mark-dirty" in lower
```

- [ ] **Step 6: Run scripts/generated block tests**

Run:

```powershell
pytest tests/test_agent_context_managed_block.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_copilot.py tests/integrations/test_integration_generic.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```powershell
git add scripts/bash/common.sh scripts/powershell/common.ps1 scripts/bash/check-prerequisites.sh scripts/powershell/check-prerequisites.ps1 scripts/bash/update-agent-context.sh scripts/powershell/update-agent-context.ps1 tests/test_agent_context_managed_block.py tests/integrations
git commit -m "refactor: route generated scripts to project cognition"
```

---

## Task 8: Sweep Runtime Guidance, Passive Skills, And Docs

**Files:**
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `docs/quickstart.md`
- Modify: `docs/upgrade.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `templates/passive-skills/spec-kit-project-map-gate/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-project-learning/SKILL.md`
- Modify: `tests/test_project_handbook_templates.py`
- Modify: `tests/test_command_surface_semantics.py`
- Modify: `tests/test_hook_template_guidance.py`
- Modify: `tests/test_passive_skill_guidance.py`
- Modify: `tests/test_graph_native_downstream_adoption.py`

- [ ] **Step 1: Update documentation tests**

In `tests/test_command_surface_semantics.py`, replace project-map command shape assertions:

```python
assert "command shape: `specify project-map mark-dirty --reason " in readme
```

with:

```python
assert "command shape: `specify project-cognition mark-dirty --reason " in readme
assert "command shape: `specify project-map mark-dirty --reason " not in readme
```

In hook/template guidance tests, replace expectations for `specify project-map complete-refresh` and `specify project-map mark-dirty` with `project-cognition`.

In `tests/test_graph_native_downstream_adoption.py`, change `LEGACY_TOKENS` so `.specify/project-map/` is forbidden in new runtime templates but allowed in explicit legacy docs if the test supports allowlists.

- [ ] **Step 2: Rewrite README runtime sections**

In `README.md`, replace:

```markdown
`DEBUG-HANDBOOK.md`, `BUILD-HANDBOOK.md`, and `.specify/project-map/**` remain compatibility/export surfaces only during the migration window.
```

with:

```markdown
New generated workflows use `.specify/project-cognition/status.json`, `.specify/project-cognition/project-cognition.db`, and `project-cognition query` as the runtime truth surface. `specify project-map ...` remains a legacy CLI alias for existing projects, but new workflows should not read or require `.specify/project-map/**`.
```

Replace public command shapes so only `project-cognition` appears in the primary list. Add a short legacy note:

```markdown
Legacy alias: existing projects may still call `specify project-map ...`; it routes to the project cognition implementation and should not be used in new generated workflow guidance.
```

- [ ] **Step 3: Rewrite PROJECT-HANDBOOK runtime guidance**

In `PROJECT-HANDBOOK.md`, remove first-read references to `.specify/project-map/**`. Keep repository maintenance references to `templates/project-map/**` only as dormant legacy template assets if needed:

```markdown
`templates/project-map/**` is retained only for legacy compatibility review and must not be installed or required by new generated projects.
```

Update focused regression guidance to include the new retirement tests:

```markdown
pytest tests/test_map_scan_build_template_guidance.py tests/test_map_runtime_template_guidance.py tests/integrations/test_cli.py -q
```

- [ ] **Step 4: Update passive skill names only if necessary**

Keep the `spec-kit-project-map-gate` directory name for now to avoid a larger skill migration. Change its title/body to project cognition gate wording and add:

```markdown
This skill name is legacy; the runtime gate it describes is project cognition.
```

Remove `.specify/project-map/**` from default read guidance.

- [ ] **Step 5: Run docs/passive skill tests**

Run:

```powershell
pytest tests/test_project_handbook_templates.py tests/test_command_surface_semantics.py tests/test_hook_template_guidance.py tests/test_passive_skill_guidance.py tests/test_graph_native_downstream_adoption.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```powershell
git add README.md PROJECT-HANDBOOK.md docs/quickstart.md docs/upgrade.md templates/project-handbook-template.md templates/passive-skills tests/test_project_handbook_templates.py tests/test_command_surface_semantics.py tests/test_hook_template_guidance.py tests/test_passive_skill_guidance.py tests/test_graph_native_downstream_adoption.py
git commit -m "docs: retire project-map from runtime guidance"
```

---

## Task 9: Final Regression Sweep And Compatibility Audit

**Files:**
- Modify if needed: any file revealed by the searches or tests below.

- [ ] **Step 1: Search for forbidden new-runtime project-map references**

Run:

```powershell
rg -n "\.specify/project-map/|specify project-map|project-map complete-refresh|project-map mark-dirty" templates src scripts tests README.md PROJECT-HANDBOOK.md docs pyproject.toml
```

Expected remaining references only in:

- `templates/project-map/**`
- `src/specify_cli/project_map_status.py`
- `src/specify_cli/hooks/project_map.py`
- legacy alias tests
- docs sections explicitly saying `project-map` is a legacy alias
- dormant script filenames such as `project-map-freshness.sh`

Move any unexpected runtime guidance to `project-cognition`.

- [ ] **Step 2: Search for bare cognition helper commands in templates**

Run:

```powershell
rg -n "specify project-cognition (query|complete-refresh|mark-dirty|record-refresh|update)" templates src/specify_cli/integrations
```

Expected: no generated workflow template occurrences where `{{specify-subcmd:...}}` can be used. Plain docs or hook adapter internals can remain only if they are not generated workflow instructions.

- [ ] **Step 3: Run focused test suite**

Run:

```powershell
pytest tests/test_project_map_status.py tests/integrations/test_cli.py tests/test_map_scan_build_template_guidance.py tests/test_map_runtime_template_guidance.py tests/test_alignment_templates.py tests/test_project_map_hard_gate_guidance.py tests/test_agent_context_managed_block.py tests/test_command_surface_semantics.py tests/test_project_handbook_templates.py tests/test_passive_skill_guidance.py -q
```

Expected: pass.

- [ ] **Step 4: Run broad integration/template tests**

Run:

```powershell
pytest tests/integrations tests/contract/test_hook_cli_surface.py tests/hooks -q
```

Expected: pass. If failures are only stale expected path strings, update assertions to the new cognition path. If failures show real legacy behavior still required by new projects, fix implementation instead of weakening tests.

- [ ] **Step 5: Run full tests if time allows**

Run:

```powershell
pytest -q
```

Expected: pass. If the full suite is too slow or fails on unrelated environment prerequisites, record the exact failure and the focused green suites in the final handoff.

- [ ] **Step 6: Commit final fixes**

```powershell
git status --short
git add templates src scripts tests README.md PROJECT-HANDBOOK.md docs pyproject.toml
git commit -m "test: align project-map retirement regressions"
```

Skip the commit if there are no remaining changes.

---

## Implementation Notes

- Keep `project-map` CLI alias command registration in `src/specify_cli/__init__.py`.
- Keep `src/specify_cli/project_map_status.py` as an import shim.
- Keep `scripts/*/project-map-freshness.*` filenames in this phase unless changing them becomes necessary. Generated text should call them cognition helpers or hide them behind status/helper path variables.
- Do not delete `templates/project-map/**` in this pass. Stop installing and requiring it first; deletion can be a follow-up once compatibility evidence is clear.
- Do not weaken `project-cognition query` readiness semantics. This work changes command routing and runtime surfaces, not the query result model.
- Favor exact source-template placeholders for generated workflow command instructions. Use plain `specify project-cognition ...` only in docs or scripts that are not passed through `render_project_launcher_placeholders`.
