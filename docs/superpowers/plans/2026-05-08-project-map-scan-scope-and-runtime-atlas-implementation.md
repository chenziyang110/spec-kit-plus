# Project-Map Scan Scope and Runtime Atlas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `sp-map-scan` diff-first and live-surface-only, keep derived atlas artifacts out of scan scope, and require `sp-map-build` to reject derived-only evidence while rendering capability Mermaid diagrams into deep workflow pages.

**Architecture:** Add a shared project-map scope classifier in Python and align the Bash/PowerShell freshness helpers to the same semantics. Update the `map-scan` and `map-build` workflow contracts plus artifact validation so runtime atlas files are consumed by ordinary `sp-*` commands, refresh workbench artifacts stay internal to atlas refresh, and capability diagrams become first-class deep workflow outputs instead of JSON-only data.

**Tech Stack:** Python 3.13, Typer CLI helpers, Bash/PowerShell freshness scripts, Markdown command templates, JSON atlas indexes, pytest template/contract/integration tests.

---

## File Structure

```text
MODIFY
  src/specify_cli/project_map_status.py
    Purpose: classify project-map paths as live/reference/excluded, expose diff-first scan scope metadata, and stop treating atlas-derived changes as refresh-driving truth.
  src/specify_cli/hooks/project_map.py
    Purpose: keep refresh completion conservative and consume richer project-map freshness/scope results.
  src/specify_cli/hooks/artifact_validation.py
    Purpose: make map-build fail when worker evidence is derived-only and require deep workflow docs to carry capability Mermaid output.
  scripts/bash/project-map-freshness.sh
    Purpose: preserve shell parity for diff-first project-map scope classification and derived-surface handling.
  scripts/powershell/project-map-freshness.ps1
    Purpose: preserve PowerShell parity for diff-first project-map scope classification and derived-surface handling.
  templates/commands/map-scan.md
    Purpose: define diff-first, live-surface-only scan behavior and formalize reference-only atlas/workbench inputs.
  templates/commands/map-build.md
    Purpose: reject derived-only evidence and require diagram rendering into deep workflow pages.
  templates/command-partials/map-scan/shell.md
    Purpose: restate scan scope rules in the short objective/context entrypoint.
  templates/command-partials/map-build/shell.md
    Purpose: restate build-side evidence and runtime atlas output expectations.
  README.md
    Purpose: document that `fresh` still diff-checks and distinguish runtime atlas from refresh workbench artifacts.
  PROJECT-HANDBOOK.md
    Purpose: document runtime atlas consumption vs refresh workbench artifacts in brownfield guidance.

TESTS TO MODIFY
  tests/test_project_map_status.py
  tests/test_project_map_freshness_scripts.py
  tests/contract/test_hook_cli_surface.py
  tests/test_map_scan_build_template_guidance.py
  tests/integrations/test_integration_codex.py
  tests/test_alignment_templates.py
    Purpose: lock in scope classification, helper parity, derived-only build failure, deep workflow diagram requirements, and generated-skill wording.

NEW TESTS
  tests/test_project_map_scan_scope.py
    Purpose: lock the new Python scope-classification behavior independently from freshness severity wording.
```

---

## Task 1: Lock the new scan-scope model with failing tests

**Files:**
- Create: `tests/test_project_map_scan_scope.py`
- Modify: `tests/test_project_map_status.py`
- Modify: `tests/test_project_map_freshness_scripts.py`

- [ ] **Step 1: Create focused failing tests for scope classification**

Create `tests/test_project_map_scan_scope.py` with this content:

```python
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = PROJECT_ROOT / "src" / "specify_cli" / "project_map_status.py"


def _load_module():
    spec = spec_from_file_location("project_map_status_scope", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_project_map_scope_classifies_runtime_atlas_and_workbench_distinctly():
    mod = _load_module()

    assert mod.classify_scan_scope_path("src/specify_cli/project_map_status.py") == "live_surface"
    assert mod.classify_scan_scope_path("templates/commands/map-scan.md") == "live_surface"
    assert mod.classify_scan_scope_path(".specify/memory/project-rules.md") == "live_surface"
    assert mod.classify_scan_scope_path(".specify/templates/project-map/ARCHITECTURE.md") == "live_surface"
    assert mod.classify_scan_scope_path("PROJECT-HANDBOOK.md") == "reference_only"
    assert mod.classify_scan_scope_path(".specify/project-map/root/ARCHITECTURE.md") == "reference_only"
    assert mod.classify_scan_scope_path(".specify/project-map/index/capabilities.json") == "reference_only"
    assert mod.classify_scan_scope_path(".specify/project-map/scan-packets/SCAN-core.md") == "reference_only"
    assert mod.classify_scan_scope_path(".specify/project-map/worker-results/SCAN-core.json") == "reference_only"
    assert mod.classify_scan_scope_path(".pytest_cache/v/cache/nodeids") == "hard_excluded"


def test_project_map_scope_filter_drops_reference_only_and_keeps_live_candidates():
    mod = _load_module()

    filtered = mod.filter_scan_scope_candidates(
        [
            "src/specify_cli/project_map_status.py",
            ".specify/project-map/index/status.json",
            "PROJECT-HANDBOOK.md",
            ".specify/templates/project-map/ARCHITECTURE.md",
            ".pytest_cache/v/cache/nodeids",
        ]
    )

    assert filtered["live_candidates"] == [
        "src/specify_cli/project_map_status.py",
        ".specify/templates/project-map/ARCHITECTURE.md",
    ]
    assert filtered["reference_only"] == [
        ".specify/project-map/index/status.json",
        "PROJECT-HANDBOOK.md",
    ]
    assert filtered["hard_excluded"] == [".pytest_cache/v/cache/nodeids"]
```

- [ ] **Step 2: Add freshness-level expectations for derived project-map changes**

In `tests/test_project_map_status.py`, add these two tests near the existing classification coverage:

```python
def test_assess_project_map_freshness_ignores_reference_only_project_map_changes(tmp_path):
    mod = _load_module()

    mod.mark_project_map_refreshed(
        tmp_path,
        head_commit="base123",
        branch="main",
        reason="map-build",
        mapped_at="2026-05-08T00:00:00Z",
    )

    result = mod.assess_project_map_freshness(
        tmp_path,
        head_commit="head456",
        changed_files=[
            ".specify/project-map/index/status.json",
            ".specify/project-map/root/ARCHITECTURE.md",
            ".specify/project-map/worker-results/SCAN-core.json",
        ],
        has_git=True,
    )

    assert result["freshness"] == "fresh"
    assert result["reasons"] == []
    assert result["changed_files"] == [
        ".specify/project-map/index/status.json",
        ".specify/project-map/root/ARCHITECTURE.md",
        ".specify/project-map/worker-results/SCAN-core.json",
    ]


def test_classify_changed_path_treats_project_map_outputs_as_ignore_for_freshness():
    mod = _load_module()

    assert mod.classify_changed_path("PROJECT-HANDBOOK.md") == "ignore"
    assert mod.classify_changed_path(".specify/project-map/root/ARCHITECTURE.md") == "ignore"
    assert mod.classify_changed_path(".specify/project-map/index/capabilities.json") == "ignore"
```

- [ ] **Step 3: Add shell-helper parity coverage for reference-only project-map changes**

In `tests/test_project_map_freshness_scripts.py`, add a test that:

- initializes a git repo
- records a fresh project-map baseline
- modifies only `.specify/project-map/root/ARCHITECTURE.md`
- runs both the Bash and PowerShell helper `check` commands
- expects `freshness == "fresh"` from both helpers

Use this test body:

```python
def test_project_map_freshness_helpers_ignore_reference_only_atlas_changes(git_repo: Path):
    _write_canonical_map_outputs(git_repo)
    _run_bash_helper(git_repo, ["record-refresh", "map-build"])
    _run_pwsh_helper(git_repo, ["record-refresh", "map-build"])

    target = git_repo / ".specify" / "project-map" / "root" / "ARCHITECTURE.md"
    target.write_text("# changed atlas output\n", encoding="utf-8")
    subprocess.run(["git", "add", str(target.relative_to(git_repo))], cwd=git_repo, check=True)

    bash_result = _run_bash_helper(git_repo, ["check"])
    pwsh_result = _run_pwsh_helper(git_repo, ["check"])

    assert bash_result["freshness"] == "fresh"
    assert pwsh_result["freshness"] == "fresh"
```

- [ ] **Step 4: Run the focused red suite**

Run:

```powershell
pytest tests/test_project_map_scan_scope.py tests/test_project_map_status.py tests/test_project_map_freshness_scripts.py -q
```

Expected: FAIL because the scope-classification helper functions do not exist yet and freshness still treats project-map outputs as high-impact changes.

- [ ] **Step 5: Commit the failing tests**

Run:

```powershell
git add tests/test_project_map_scan_scope.py tests/test_project_map_status.py tests/test_project_map_freshness_scripts.py
git commit -m "test: define project-map scan scope contract"
```

Expected: commit contains only the new failing tests. If unrelated files stage accidentally, unstage them with `git restore --staged <path>`.

---

## Task 2: Implement shared scan-scope classification and freshness alignment

**Files:**
- Modify: `src/specify_cli/project_map_status.py`
- Modify: `tests/test_project_map_scan_scope.py`
- Modify: `tests/test_project_map_status.py`

- [ ] **Step 1: Add explicit scan-scope classifiers**

In `src/specify_cli/project_map_status.py`, add these constants below `DIRTY_REASON_ALIASES`:

```python
SCAN_SCOPE_RUNTIME_LIVE_PREFIXES = (
    "src/",
    "templates/",
    "scripts/",
    "tests/",
    ".github/workflows/",
    ".specify/memory/",
    ".specify/templates/",
)

SCAN_SCOPE_RUNTIME_LIVE_FILES = {
    "pyproject.toml",
    "readme.md",
    "agents.md",
}

SCAN_SCOPE_REFERENCE_ONLY_PREFIXES = (
    ".specify/project-map/",
    ".specify/prd-runs/",
    ".specify/testing/worker-results/",
)

SCAN_SCOPE_REFERENCE_ONLY_FILES = {
    "project-handbook.md",
}

SCAN_SCOPE_HARD_EXCLUDED_PREFIXES = (
    ".git/",
    ".venv/",
    ".pytest_cache/",
    ".ruff_cache/",
    "dist/",
    "build/",
)
```

- [ ] **Step 2: Add the new helper functions**

Still in `src/specify_cli/project_map_status.py`, add:

```python
def classify_scan_scope_path(path: str) -> str:
    lower = str(path or "").strip().replace("\\", "/").lower().strip("/")
    if not lower:
        return "hard_excluded"
    if lower in SCAN_SCOPE_REFERENCE_ONLY_FILES or lower.startswith(SCAN_SCOPE_REFERENCE_ONLY_PREFIXES):
        return "reference_only"
    if lower.startswith(SCAN_SCOPE_HARD_EXCLUDED_PREFIXES):
        return "hard_excluded"
    if lower in SCAN_SCOPE_RUNTIME_LIVE_FILES or lower.startswith(SCAN_SCOPE_RUNTIME_LIVE_PREFIXES):
        return "live_surface"
    return "hard_excluded"


def filter_scan_scope_candidates(paths: list[str]) -> dict[str, list[str]]:
    live_candidates: list[str] = []
    reference_only: list[str] = []
    hard_excluded: list[str] = []

    for path in paths:
        classification = classify_scan_scope_path(path)
        if classification == "live_surface":
            live_candidates.append(path)
        elif classification == "reference_only":
            reference_only.append(path)
        else:
            hard_excluded.append(path)

    return {
        "live_candidates": live_candidates,
        "reference_only": reference_only,
        "hard_excluded": hard_excluded,
    }
```

- [ ] **Step 3: Reclassify derived atlas outputs for freshness**

In `classify_changed_path()`, replace the current special handling for project-map files with:

```python
    scan_scope_class = classify_scan_scope_path(path)
    if scan_scope_class in {"reference_only", "hard_excluded"}:
        return "ignore"
```

Then keep the existing stale / possibly_stale logic for live-source paths only.

- [ ] **Step 4: Preserve template and memory source-of-truth behavior**

In the same file, make sure `.specify/templates/**` and `.specify/memory/**` remain treated as live/high-impact surfaces by the rest of `classify_changed_path()` and `refresh_plan_for_changed_path()`.

Use this targeted assertion-driven guard in `tests/test_project_map_status.py`:

```python
def test_classify_changed_path_keeps_memory_and_template_truth_surfaces_live():
    mod = _load_module()

    assert mod.classify_changed_path(".specify/memory/constitution.md") == "stale"
    assert mod.classify_changed_path(".specify/templates/project-map/ARCHITECTURE.md") == "stale"
```

- [ ] **Step 5: Run the Python status/scope tests**

Run:

```powershell
pytest tests/test_project_map_scan_scope.py tests/test_project_map_status.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit the scope helper implementation**

Run:

```powershell
git add src/specify_cli/project_map_status.py tests/test_project_map_scan_scope.py tests/test_project_map_status.py
git commit -m "feat: classify project-map scan scope"
```

---

## Task 3: Keep Bash and PowerShell freshness helpers in parity

**Files:**
- Modify: `scripts/bash/project-map-freshness.sh`
- Modify: `scripts/powershell/project-map-freshness.ps1`
- Modify: `tests/test_project_map_freshness_scripts.py`

- [ ] **Step 1: Add runtime/live/reference constants to Bash helper**

In `scripts/bash/project-map-freshness.sh`, add shell arrays near `CANONICAL_MAP_FILES`:

```bash
SCAN_SCOPE_RUNTIME_LIVE_PREFIXES=(
  "src/"
  "templates/"
  "scripts/"
  "tests/"
  ".github/workflows/"
  ".specify/memory/"
  ".specify/templates/"
)
SCAN_SCOPE_REFERENCE_ONLY_PREFIXES=(
  ".specify/project-map/"
  ".specify/prd-runs/"
  ".specify/testing/worker-results/"
)
SCAN_SCOPE_HARD_EXCLUDED_PREFIXES=(
  ".git/"
  ".venv/"
  ".pytest_cache/"
  ".ruff_cache/"
  "dist/"
  "build/"
)
```

- [ ] **Step 2: Rework Bash `classify_path()` to ignore reference-only atlas outputs**

Replace the top of `classify_path()` with logic that:

- returns `ignore` for `project-handbook.md`
- returns `ignore` for any `.specify/project-map/**`
- returns `ignore` for `.specify/prd-runs/**` and `.specify/testing/worker-results/**`
- returns `ignore` for hard-excluded prefixes
- then applies the existing stale / possibly_stale logic for live-source paths

Use this exact shell block:

```bash
    case "$lower" in
        project-handbook.md|\
        .specify/project-map/*|\
        .specify/prd-runs/*|\
        .specify/testing/worker-results/*|\
        .git/*|\
        .venv/*|\
        .pytest_cache/*|\
        .ruff_cache/*|\
        dist/*|\
        build/*)
            echo "ignore"
            return 0
            ;;
    esac
```

- [ ] **Step 3: Mirror the same logic in PowerShell**

In `scripts/powershell/project-map-freshness.ps1`, update `Classify-Path` to return `"ignore"` for:

- `project-handbook.md`
- `.specify/project-map/`
- `.specify/prd-runs/`
- `.specify/testing/worker-results/`
- `.git/`, `.venv/`, `.pytest_cache/`, `.ruff_cache/`, `dist/`, `build/`

Keep `.specify/templates/` and `.specify/memory/` out of the ignore set.

- [ ] **Step 4: Run script parity tests**

Run:

```powershell
pytest tests/test_project_map_freshness_scripts.py -q
```

Expected: PASS for both Bash and PowerShell helper behavior.

- [ ] **Step 5: Commit helper parity**

Run:

```powershell
git add scripts/bash/project-map-freshness.sh scripts/powershell/project-map-freshness.ps1 tests/test_project_map_freshness_scripts.py
git commit -m "fix: ignore derived atlas outputs in freshness helpers"
```

---

## Task 4: Tighten `map-scan` and `map-build` template contracts

**Files:**
- Modify: `templates/commands/map-scan.md`
- Modify: `templates/commands/map-build.md`
- Modify: `templates/command-partials/map-scan/shell.md`
- Modify: `templates/command-partials/map-build/shell.md`
- Modify: `tests/test_map_scan_build_template_guidance.py`
- Modify: `tests/integrations/test_integration_codex.py`

- [ ] **Step 1: Add failing wording assertions for diff-first scan and reference-only artifacts**

In `tests/test_map_scan_build_template_guidance.py`, extend `test_map_scan_template_defines_complete_scan_package_contract()` with:

```python
    assert "even when freshness is `fresh`" in lowered
    assert "git baseline diff" in lowered
    assert "reference-only" in lowered
    assert "live surface" in lowered
    assert "must not become a scan target" in lowered
```

Extend `test_map_build_template_refuses_incomplete_scan_packages()` with:

```python
    assert "derived-only evidence" in lowered
    assert "deep workflow documentation pages" in lowered
    assert "required_reads contain only reference-only" in lowered or "reference-only or hard-excluded" in lowered
```

- [ ] **Step 2: Update the map-scan shell partial**

Replace the `## Context` bullets in `templates/command-partials/map-scan/shell.md` with:

```markdown
- Primary inputs: git-baseline diff data when available, live repository surfaces, existing atlas/reference artifacts, passive learning files, and optional focus hints from `$ARGUMENTS`.
- This command owns scan-package outputs only; it must not write final atlas truth.
- Derived atlas/workbench artifacts such as `PROJECT-HANDBOOK.md` and `.specify/project-map/**` may be read as reference inputs but must not become scan targets.
- The resulting scan package must let `sp-map-build` construct the handbook/project-map atlas from live-surface evidence without inventing scan scope.
- Maintain `.specify/project-map/map-state.md` as the resumable scan/build state surface.
```

- [ ] **Step 3: Update the map-build shell partial**

Replace the `## Context` bullets in `templates/command-partials/map-build/shell.md` with:

```markdown
- Primary inputs: `.specify/project-map/map-scan.md`, `.specify/project-map/coverage-ledger.json`, `.specify/project-map/coverage-ledger.md`, `.specify/project-map/scan-packets/*.md`, `.specify/project-map/map-state.md`, and live repository evidence.
- This command owns final atlas outputs and freshness metadata.
- If the scan package is incomplete or the available worker evidence is derived-only, produce a scan gap report and return to `sp-map-scan` instead of writing a shallow atlas.
- Record accepted/rejected packet evidence in `.specify/project-map/map-state.md` and `.specify/project-map/worker-results/*.json`.
```

- [ ] **Step 4: Update the full command templates**

In `templates/commands/map-scan.md`, add these exact ideas to the process and guardrail sections:

- `fresh` still requires a git-baseline diff before scope selection
- classify candidates into `hard_excluded`, `reference_only`, and `live_surface`
- atlas outputs and workbench artifacts are `reference_only`
- only `live_surface` paths may enter `coverage-ledger.json` or `scan-packets/*.md`

In `templates/commands/map-build.md`, add these exact ideas to readiness and reverse-validation sections:

- derived-only worker evidence must be rejected
- deep workflow documentation pages must carry lifecycle and flow Mermaid output
- JSON indexes may retain diagram fields, but they are not the primary human-consumed diagram surface

- [ ] **Step 5: Update Codex integration expectations**

In `tests/integrations/test_integration_codex.py`, extend `test_codex_generated_sp_map_scan_build_include_native_mapping_guidance()` with:

```python
    assert "reference-only" in scan_content
    assert "live surface" in scan_content
    assert "git baseline diff" in scan_content
    assert "derived-only evidence" in build_content
    assert "deep workflow documentation pages" in build_content
```

- [ ] **Step 6: Run the template and Codex integration tests**

Run:

```powershell
pytest tests/test_map_scan_build_template_guidance.py tests/integrations/test_integration_codex.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit the contract updates**

Run:

```powershell
git add templates/commands/map-scan.md templates/commands/map-build.md templates/command-partials/map-scan/shell.md templates/command-partials/map-build/shell.md tests/test_map_scan_build_template_guidance.py tests/integrations/test_integration_codex.py
git commit -m "feat: tighten project-map scan and build contracts"
```

---

## Task 5: Make artifact validation reject derived-only build evidence

**Files:**
- Modify: `src/specify_cli/hooks/artifact_validation.py`
- Modify: `tests/contract/test_hook_cli_surface.py`

- [ ] **Step 1: Add failing map-build validation tests**

In `tests/contract/test_hook_cli_surface.py`, add this test:

```python
def test_hook_validate_artifacts_blocks_map_build_when_worker_results_are_derived_only(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-map"
    index_dir = run_dir / "index"
    root_dir = run_dir / "root"
    workflow_dir = run_dir / "modules" / "core" / "deep" / "workflows"
    index_dir.mkdir(parents=True, exist_ok=True)
    root_dir.mkdir(parents=True, exist_ok=True)
    workflow_dir.mkdir(parents=True, exist_ok=True)

    for relative, content in {
        "map-state.md": "# Map State\n",
        "map-scan.md": "# Map Scan\n",
        "repository-universe.json": "{\"files\": []}\n",
        "coverage-ledger.json": "{\"version\": 1, \"rows\": [{\"id\": \"SURF-001\"}]}\n",
        "capability-ledger.json": "{\"capabilities\": [{\"id\": \"CAP-001\"}]}\n",
        "control-ledger.json": "{\"control_nodes\": [{\"id\": \"CTRL-001\"}]}\n",
        "index/atlas-index.json": "{}\n",
        "index/modules.json": "{\"modules\": []}\n",
        "index/relations.json": "{\"relations\": []}\n",
        "index/capabilities.json": "{\"capabilities\": [{\"id\": \"CAP-001\", \"lifecycle_mermaid\": \"graph TD\\nA-->B\", \"flow_mermaid\": \"sequenceDiagram\\nA->>B: x\"}]}\n",
        "index/symptoms.json": "{\"symptoms\": []}\n",
        "root/ARCHITECTURE.md": "# Architecture\n",
        "root/STRUCTURE.md": "# Structure\n",
        "root/CONVENTIONS.md": "# Conventions\n",
        "root/INTEGRATIONS.md": "# Integrations\n",
        "root/WORKFLOWS.md": "# Workflows\n",
        "root/TESTING.md": "# Testing\n",
        "root/OPERATIONS.md": "# Operations\n",
        "modules/core/deep/workflows/cap-001.md": "# CAP-001\n",
    }.items():
        target = run_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    (run_dir / "scan-packets").mkdir()
    (run_dir / "scan-packets" / "lane-a.md").write_text("# Packet\n", encoding="utf-8")
    (run_dir / "worker-results").mkdir()
    (run_dir / "worker-results" / "lane-a.json").write_text(
        json.dumps(
            {
                "lane_id": "lane-a",
                "paths_read": [
                    ".specify/project-map/index/capabilities.json",
                    ".specify/project-map/root/ARCHITECTURE.md",
                ],
                "unknowns": [],
                "confidence": "Verified",
                "recommended_atlas_updates": [],
            }
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("derived-only" in message.lower() for message in payload["errors"])
```

- [ ] **Step 2: Add failing test for missing Mermaid render in deep workflow page**

In the same file, add:

```python
def test_hook_validate_artifacts_blocks_map_build_when_deep_workflow_page_lacks_mermaid(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-map"
    index_dir = run_dir / "index"
    workflow_dir = run_dir / "modules" / "core" / "deep" / "workflows"
    index_dir.mkdir(parents=True, exist_ok=True)
    workflow_dir.mkdir(parents=True, exist_ok=True)

    for relative, content in {
        "map-state.md": "# Map State\n",
        "map-scan.md": "# Map Scan\n",
        "repository-universe.json": "{\"files\": []}\n",
        "coverage-ledger.json": "{\"version\": 1, \"rows\": [{\"id\": \"SURF-001\"}]}\n",
        "capability-ledger.json": "{\"capabilities\": [{\"id\": \"CAP-001\"}]}\n",
        "control-ledger.json": "{\"control_nodes\": [{\"id\": \"CTRL-001\"}]}\n",
        "index/atlas-index.json": "{}\n",
        "index/modules.json": "{\"modules\": []}\n",
        "index/relations.json": "{\"relations\": []}\n",
        "index/capabilities.json": "{\"capabilities\": [{\"id\": \"CAP-001\", \"deep_workflow\": \".specify/project-map/modules/core/deep/workflows/cap-001.md\", \"lifecycle_mermaid\": \"graph TD\\nA-->B\", \"flow_mermaid\": \"sequenceDiagram\\nA->>B: x\"}]}\n",
        "index/symptoms.json": "{\"symptoms\": []}\n",
        "modules/core/deep/workflows/cap-001.md": "# CAP-001\n\nNo diagram here.\n",
    }.items():
        target = run_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    (run_dir / "scan-packets").mkdir()
    (run_dir / "scan-packets" / "lane-a.md").write_text("# Packet\n", encoding="utf-8")
    (run_dir / "worker-results").mkdir()
    (run_dir / "worker-results" / "lane-a.json").write_text(
        json.dumps(
            {
                "lane_id": "lane-a",
                "paths_read": ["src/app.py"],
                "unknowns": [],
                "confidence": "Verified",
                "recommended_atlas_updates": [],
            }
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("mermaid" in message.lower() and "deep/workflows" in message.lower() for message in payload["errors"])
```

- [ ] **Step 3: Implement map-build worker-result validation**

In `src/specify_cli/hooks/artifact_validation.py`, add:

```python
MAP_BUILD_WORKER_RESULT_REQUIRED_KEYS = frozenset(
    {
        "paths_read",
        "unknowns",
        "confidence",
        "recommended_atlas_updates",
    }
)


def _is_reference_only_map_build_path(path: str) -> bool:
    normalized = str(path or "").strip().replace("\\", "/").lower().strip("/")
    return (
        normalized == "project-handbook.md"
        or normalized.startswith(".specify/project-map/")
        or normalized.startswith(".specify/prd-runs/")
        or normalized.startswith(".specify/testing/worker-results/")
    )
```

Then add a `_validate_map_build_worker_results(feature_dir: Path) -> list[str]` helper modeled after `_validate_prd_worker_results()` that:

- requires the four keys above
- blocks when `paths_read` is empty
- blocks when every path in `paths_read` is reference-only

- [ ] **Step 4: Implement Mermaid render validation for deep workflow pages**

In `src/specify_cli/hooks/artifact_validation.py`, add `_validate_map_build_capability_diagrams(feature_dir: Path) -> list[str]` that:

- loads `index/capabilities.json`
- walks each capability entry
- if it has `lifecycle_mermaid` or `flow_mermaid`, resolves the deep workflow page path from:
  - `deep_workflow`
  - or `deep_workflow_path`
- blocks if the deep workflow file is missing
- blocks if the deep workflow file content lacks ```` ```mermaid ```` when the capability carries Mermaid data

- [ ] **Step 5: Wire the new validations into `validate_artifacts_hook()`**

In the `command_name == "map-build"` path, extend the existing validation list with:

```python
    errors.extend(_validate_map_build_worker_results(feature_dir))
    errors.extend(_validate_map_build_capability_diagrams(feature_dir))
```

- [ ] **Step 6: Run the contract test slice**

Run:

```powershell
pytest tests/contract/test_hook_cli_surface.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit build validation hardening**

Run:

```powershell
git add src/specify_cli/hooks/artifact_validation.py tests/contract/test_hook_cli_surface.py
git commit -m "feat: harden map build artifact validation"
```

---

## Task 6: Align docs and generated-surface wording

**Files:**
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Update README atlas refresh wording**

In `README.md`, update the project-map refresh guidance so it says:

- `fresh` means the last atlas refresh completed against a known git baseline
- `sp-map-scan` still performs diff-based scope selection when entered
- ordinary runtime atlas consumption should prefer:
  - `QUICK-NAV.md`
  - `index/status.json`
  - `index/atlas-index.json`
  - `index/capabilities.json`
  - `index/symptoms.json`
  - `root/*.md`
  - `modules/*/deep/workflows/*.md`
- refresh workbench artifacts are internal to `map-scan` / `map-build`

- [ ] **Step 2: Update PROJECT-HANDBOOK runtime-atlas wording**

In `PROJECT-HANDBOOK.md`, update the brownfield atlas lifecycle and topic map sections to distinguish:

- runtime atlas
- refresh workbench

Use the same terminology as the approved spec:

- `runtime atlas`
- `refresh workbench`
- `reference-only`

- [ ] **Step 3: Add wording assertions**

In `tests/test_alignment_templates.py`, add assertions that:

```python
    assert "runtime atlas" in handbook.lower()
    assert "refresh workbench" in handbook.lower()
    assert "reference-only" in handbook.lower()
```

and similarly for the README content block that documents map refresh.

- [ ] **Step 4: Run the doc/wording tests**

Run:

```powershell
pytest tests/test_alignment_templates.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the doc alignment**

Run:

```powershell
git add README.md PROJECT-HANDBOOK.md tests/test_alignment_templates.py
git commit -m "docs: clarify runtime atlas and refresh workbench"
```

---

## Task 7: Run the full verification pass

**Files:**
- No code changes

- [ ] **Step 1: Run the focused project-map suite**

Run:

```powershell
pytest tests/test_project_map_scan_scope.py tests/test_project_map_status.py tests/test_project_map_freshness_scripts.py tests/test_map_scan_build_template_guidance.py tests/contract/test_hook_cli_surface.py tests/integrations/test_integration_codex.py tests/test_alignment_templates.py -q
```

Expected: PASS.

- [ ] **Step 2: Run the broader map-related regression suite**

Run:

```powershell
pytest tests/test_project_map_* tests/hooks/test_project_map_hooks.py tests/test_map_scan_build_template_guidance.py tests/contract/test_hook_cli_surface.py -q
```

Expected: PASS.

- [ ] **Step 3: Review the final diff**

Run:

```powershell
git diff --stat HEAD~6..HEAD
git diff -- src/specify_cli/project_map_status.py src/specify_cli/hooks/artifact_validation.py scripts/bash/project-map-freshness.sh scripts/powershell/project-map-freshness.ps1 templates/commands/map-scan.md templates/commands/map-build.md README.md PROJECT-HANDBOOK.md
```

Expected: diff shows only project-map scope, build validation, template, and doc changes described by the plan.

- [ ] **Step 4: Create the final integration commit if any verification fixups were needed**

Run only if Step 1 or Step 2 required additional edits:

```powershell
git add <verified-fixup-paths>
git commit -m "test: finalize project-map scan scope verification"
```

- [ ] **Step 5: Stop for integration choice**

Do not continue into implementation automatically from this plan file. Hand off with verification evidence and let the execution mode choose subagent-driven or inline execution.
