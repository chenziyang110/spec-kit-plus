# PRD Scan Build Reconstruction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the one-step `sp-prd` workflow with a canonical `sp-prd-scan -> sp-prd-build` flow, deprecate `sp-prd` as the primary reverse-PRD lane, and enforce reconstruction-grade scan/build contracts across templates, CLI helpers, validation, docs, and tests.

**Architecture:** Shared workflow templates remain the product truth source, so implementation starts by adding new command templates and helper-state contracts before changing routing or docs. The CLI and hook layers then grow explicit `prd-scan` and `prd-build` state semantics while keeping `prd` as a compatibility entrypoint. Validation closes the loop by blocking shallow build success, and only after those mechanics exist do docs and passive routing converge on the new canonical flow.

**Tech Stack:** Python 3.13, Typer CLI, pytest, Markdown command templates, shell/PowerShell helper scripts, Spec Kit integration generators, workflow validation hooks.

---

## Context

Read before editing:

- `docs/superpowers/specs/2026-05-04-prd-scan-build-reconstruction-design.md`
- `templates/commands/prd.md`
- `scripts/bash/prd-state.sh`
- `scripts/powershell/prd-state.ps1`
- `src/specify_cli/__init__.py`
- `src/specify_cli/hooks/artifact_validation.py`
- `src/specify_cli/hooks/state_validation.py`
- `src/specify_cli/hooks/checkpoint.py`
- `templates/passive-skills/project-to-prd/SKILL.md`
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- `tests/test_prd_template_guidance.py`
- `tests/test_prd_cli_helpers.py`
- `tests/contract/test_hook_cli_surface.py`

The working tree may already contain user changes. Do not reset or revert unrelated files. `AGENTS.md` is already dirty in the workspace; ignore it unless a task explicitly tells you to touch it.

## File Structure

Create:

- `templates/commands/prd-scan.md` - canonical scan workflow contract for reconstruction-first repository investigation.
- `templates/commands/prd-build.md` - canonical build workflow contract for scan validation, master-pack compilation, and reverse coverage closure.
- `tests/test_prd_scan_build_template_guidance.py` - focused template assertions for the new command pair and `prd` deprecation semantics.
- `docs/superpowers/specs/2026-05-04-prd-scan-build-reconstruction-design.md` already exists and is the implementation source of truth for this plan.

Modify:

- `templates/commands/prd.md` - deprecate the old one-step workflow and route operators to `sp-prd-scan -> sp-prd-build`.
- `templates/passive-skills/project-to-prd/SKILL.md` - route to the new canonical pair and explain `sp-prd` as compatibility-only.
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md` - update workflow routing and invocation examples.
- `scripts/bash/prd-state.sh` - add `prd-scan` / `prd-build` state contracts, new artifact surfaces, and compatibility handling for `prd`.
- `scripts/powershell/prd-state.ps1` - PowerShell parity for the helper behavior above.
- `src/specify_cli/__init__.py` - register `prd-scan` and `prd-build` commands, update helper wrappers, help text, routing summaries, and compatibility copy for `prd`.
- `src/specify_cli/hooks/state_validation.py` - accept the new workflow-state command names and phase modes.
- `src/specify_cli/hooks/checkpoint.py` - allow checkpoint parsing for `prd-scan` and `prd-build`.
- `src/specify_cli/hooks/artifact_validation.py` - validate the new artifact contracts and reject shallow `prd-build` outputs.
- `PROJECT-HANDBOOK.md` - update the workflow descriptions and maintenance guidance for PRD extraction.
- `README.md` - document the new canonical reverse-PRD flow and deprecate `prd` as the main entrypoint.
- `docs/quickstart.md` - update examples, support skill lists, and workflow guidance.
- `docs/installation.md` - update command examples and wording.
- `templates/project-map/WORKFLOWS.md` - reflect the canonical `prd-scan -> prd-build` pair.
- `templates/project-map/root/WORKFLOWS.md` - same as above for generated atlas content.
- `tests/test_prd_template_guidance.py` - convert old one-step expectations into `prd` deprecation checks or slim compatibility assertions.
- `tests/test_prd_cli_helpers.py` - assert the helper creates scan/build-ready workspaces and compatibility behavior for `prd`.
- `tests/contract/test_hook_cli_surface.py` - add validation and checkpoint cases for `prd-scan` / `prd-build`, plus compatibility handling for `prd`.
- Any integration or generated-skill tests that assert the old `sp-prd` command text, if they fail after the command-template update.

Delete later in the implementation if no longer needed:

- no file deletions are required in the first rollout; keep `templates/commands/prd.md` as a deprecated compatibility surface.

## Command Naming Rules

Use these replacements consistently:

- Canonical reverse-PRD workflow: `sp-prd-scan -> sp-prd-build`
- Slash form: `/sp-prd-scan -> /sp-prd-build`
- Codex skill form: `$sp-prd-scan -> $sp-prd-build`
- Generic workflow names: `prd-scan` and `prd-build`
- `sp-prd` / `prd` should be described as deprecated compatibility entrypoints, not as the primary workflow
- Scan outputs include `coverage-ledger.*`, `capability-ledger.json`, `artifact-contracts.json`, and `reconstruction-checklist.json`
- Build outputs include `master/master-pack.md`, `exports/prd.md`, `exports/reconstruction-appendix.md`, `exports/data-model.md`, `exports/integration-contracts.md`, and `exports/runtime-behaviors.md`

Do not leave user-facing guidance that still treats `sp-prd` as the main reverse-PRD path.

---

### Task 1: Add failing template tests for the new command pair

**Files:**
- Create: `tests/test_prd_scan_build_template_guidance.py`
- Modify: `tests/test_prd_template_guidance.py`

- [ ] **Step 1: Write the failing tests for `prd-scan`, `prd-build`, and deprecated `prd`**

Create `tests/test_prd_scan_build_template_guidance.py` with this content:

```python
from pathlib import Path

import yaml

from tests.template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _content(path: str) -> str:
    return read_template(path)


def _frontmatter(path: str) -> dict:
    parts = _content(path).split("---", 2)
    return yaml.safe_load(parts[1])


def test_prd_scan_template_defines_reconstruction_scan_contract() -> None:
    content = _content("templates/commands/prd-scan.md")
    frontmatter = _frontmatter("templates/commands/prd-scan.md")
    contract = frontmatter["workflow_contract"]
    lowered = content.lower()

    assert "sp-prd-scan" in content
    assert "sp-prd-build" in content
    assert ".specify/prd-runs/<run-id>/prd-scan.md" in contract["primary_outputs"]
    assert ".specify/prd-runs/<run-id>/artifact-contracts.json" in contract["primary_outputs"]
    assert ".specify/prd-runs/<run-id>/reconstruction-checklist.json" in contract["primary_outputs"]
    assert "read-only reconstruction investigation" in lowered
    assert "must not write `master/master-pack.md`" in content
    assert "must not write `exports/**`" in content
    assert "capability" in lowered
    assert "artifact" in lowered
    assert "boundary" in lowered
    assert "reconstruction-ready" in content
    assert "blocked-by-gap" in content
    assert "artifact-contracts.json" in content
    assert "reconstruction-checklist.json" in content


def test_prd_build_template_refuses_incomplete_scan_packages() -> None:
    content = _content("templates/commands/prd-build.md")
    frontmatter = _frontmatter("templates/commands/prd-build.md")
    contract = frontmatter["workflow_contract"]
    lowered = content.lower()

    assert "sp-prd-build" in content
    assert "sp-prd-scan" in content
    assert ".specify/prd-runs/<run-id>/exports/prd.md" in contract["primary_outputs"]
    assert ".specify/prd-runs/<run-id>/exports/reconstruction-appendix.md" in contract["primary_outputs"]
    assert "must not become a second repository scan" in lowered
    assert "must not silently fill critical evidence gaps" in lowered
    assert "No New Facts Gate" in content
    assert "Artifact Landing Gate" in content
    assert "Field-Level Coverage Gate" in content
    assert "Inference Ceiling Gate" in content
    assert "reverse coverage validation" in lowered


def test_prd_template_is_deprecated_and_routes_to_scan_build() -> None:
    content = _content("templates/commands/prd.md")
    lowered = content.lower()

    assert "deprecated" in lowered
    assert "sp-prd-scan" in content
    assert "sp-prd-build" in content
    assert "compatibility" in lowered
    assert "no longer" in lowered or "instead" in lowered
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```bash
pytest tests/test_prd_scan_build_template_guidance.py -q
```

Expected: FAIL because `templates/commands/prd-scan.md` and `templates/commands/prd-build.md` do not exist yet, and `templates/commands/prd.md` is not deprecated.

- [ ] **Step 3: Add a failing compatibility assertion to the old PRD template test file**

Append this test to `tests/test_prd_template_guidance.py`:

```python
def test_prd_template_is_compatibility_only_not_primary_reverse_prd_lane() -> None:
    content = _content()
    lowered = content.lower()

    assert "deprecated" in lowered
    assert "compatibility" in lowered
    assert "sp-prd-scan" in content
    assert "sp-prd-build" in content
```

- [ ] **Step 4: Run the combined template tests to verify the old expectations now fail**

Run:

```bash
pytest tests/test_prd_template_guidance.py tests/test_prd_scan_build_template_guidance.py -q
```

Expected: FAIL because the current `prd.md` still describes the one-step workflow and the new template files are absent.

- [ ] **Step 5: Commit**

```bash
git add tests/test_prd_template_guidance.py tests/test_prd_scan_build_template_guidance.py
git commit -m "test: add failing prd scan build template contract checks"
```

### Task 2: Add the new command templates and deprecate `prd`

**Files:**
- Create: `templates/commands/prd-scan.md`
- Create: `templates/commands/prd-build.md`
- Modify: `templates/commands/prd.md`

- [ ] **Step 1: Write the minimal `prd-scan` template that satisfies the new contract tests**

Create `templates/commands/prd-scan.md` with a frontmatter and body shaped like:

```md
---
description: Use when an existing repository needs reconstruction-grade scan outputs before a PRD suite can be compiled.
workflow_contract:
  when_to_use: Use for an existing repository that needs read-only reconstruction investigation before final PRD synthesis.
  primary_objective: Produce a reconstruction-grade scan package that captures capability, artifact, and boundary truth strongly enough for `sp-prd-build`.
  primary_outputs: '`.specify/prd-runs/<run-id>/workflow-state.md`, `.specify/prd-runs/<run-id>/prd-scan.md`, `.specify/prd-runs/<run-id>/coverage-ledger.md`, `.specify/prd-runs/<run-id>/coverage-ledger.json`, `.specify/prd-runs/<run-id>/capability-ledger.json`, `.specify/prd-runs/<run-id>/artifact-contracts.json`, `.specify/prd-runs/<run-id>/reconstruction-checklist.json`, `.specify/prd-runs/<run-id>/scan-packets/<lane-id>.md`, `.specify/prd-runs/<run-id>/evidence/**`, and `.specify/prd-runs/<run-id>/worker-results/**`.'
  default_handoff: /sp-prd-build after the scan package passes reconstruction readiness checks.
---

# `/sp.prd-scan` Reconstruction Scan

## Workflow Contract Summary

- Use `sp-prd-scan` for read-only reconstruction investigation.
- Primary truth source: current repository reality plus `PROJECT-HANDBOOK.md` and project-map evidence when present.
- Primary terminal state: completed scan package under `.specify/prd-runs/<run-id>/`.
- Default handoff: `/sp-prd-build`.

## Hard Boundary

- `sp-prd-scan` must not write `master/master-pack.md`.
- `sp-prd-scan` must not write `exports/**`.

## Process

1. Route and initialize the PRD run.
2. Load brownfield context.
3. Triage `capability`, `artifact`, and `boundary` objects.
4. Build `artifact-contracts.json` and `reconstruction-checklist.json`.
5. Generate scan packets.
6. Refuse handoff if any `critical` area is not `reconstruction-ready`.
```

- [ ] **Step 2: Write the minimal `prd-build` template that satisfies the new contract tests**

Create `templates/commands/prd-build.md` with a frontmatter and body shaped like:

```md
---
description: Use when `sp-prd-scan` has produced a complete reconstruction package and the final PRD suite must be compiled from it.
workflow_contract:
  when_to_use: Use when a validated PRD scan package exists and final PRD documents must be compiled without ad hoc repository rereads.
  primary_objective: Validate the scan package, compile the master pack, render final exports, and prove reverse coverage closure.
  primary_outputs: '`.specify/prd-runs/<run-id>/workflow-state.md`, `.specify/prd-runs/<run-id>/master/master-pack.md`, `.specify/prd-runs/<run-id>/exports/prd.md`, `.specify/prd-runs/<run-id>/exports/reconstruction-appendix.md`, `.specify/prd-runs/<run-id>/exports/data-model.md`, `.specify/prd-runs/<run-id>/exports/integration-contracts.md`, and `.specify/prd-runs/<run-id>/exports/runtime-behaviors.md`.'
  default_handoff: Completed PRD suite export. No automatic handoff into implementation planning.
---

# `/sp.prd-build` Reconstruction Build

## Workflow Contract Summary

- Use `sp-prd-build` only after `sp-prd-scan`.
- Readiness comes before writing.

## Hard Boundary

- `sp-prd-build` must not become a second repository scan.
- `sp-prd-build` must not silently fill critical evidence gaps.

## Quality Gates

- **No New Facts Gate**
- **Artifact Landing Gate**
- **Field-Level Coverage Gate**
- **Inference Ceiling Gate**

## Process

1. Validate the scan package.
2. Compile `master/master-pack.md`.
3. Render the final exports.
4. Run reverse coverage validation.
5. Route back to `/sp-prd-scan` if readiness fails.
```

- [ ] **Step 3: Rewrite `templates/commands/prd.md` as a deprecated compatibility entrypoint**

Replace the current body of `templates/commands/prd.md` with a short compatibility contract that:

- marks the workflow as deprecated
- explains that the canonical path is `sp-prd-scan -> sp-prd-build`
- preserves “existing repository reverse PRD extraction” semantics
- explicitly says `sp-prd` is compatibility-only
- does not keep the full old one-step process text

Use this body structure:

```md
---
description: Deprecated compatibility entrypoint for existing-project PRD extraction. Prefer `sp-prd-scan` followed by `sp-prd-build`.
workflow_contract:
  when_to_use: Use only when a compatibility surface still invokes `prd`; the canonical reverse-PRD path is `prd-scan -> prd-build`.
  primary_objective: Redirect operators from the deprecated one-step PRD command to the canonical two-step reconstruction workflow.
  primary_outputs: 'Deprecated compatibility guidance only. Use `.specify/prd-runs/<run-id>/` outputs from `prd-scan` and `prd-build`.'
  default_handoff: `/sp-prd-scan`, then `/sp-prd-build`.
---

# `/sp.prd` Deprecated Compatibility Entry

`sp-prd` is deprecated as the primary reverse-PRD workflow.

Use:

```text
sp-prd-scan -> sp-prd-build
```

This compatibility entrypoint exists only to redirect older habits and generated surfaces.
```

- [ ] **Step 4: Run the template tests to verify the new command surfaces pass**

Run:

```bash
pytest tests/test_prd_template_guidance.py tests/test_prd_scan_build_template_guidance.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/commands/prd.md templates/commands/prd-scan.md templates/commands/prd-build.md tests/test_prd_template_guidance.py tests/test_prd_scan_build_template_guidance.py
git commit -m "feat: introduce prd scan build workflow templates"
```

### Task 3: Extend the PRD state helpers for scan/build lifecycle

**Files:**
- Modify: `scripts/bash/prd-state.sh`
- Modify: `scripts/powershell/prd-state.ps1`
- Modify: `tests/test_prd_cli_helpers.py`

- [ ] **Step 1: Add failing helper tests for `prd-scan` and `prd-build` workspace surfaces**

Append these tests to `tests/test_prd_cli_helpers.py`:

```python
def test_python_prd_helper_wrapper_supports_prd_scan_mode(tmp_path, monkeypatch):
    project = _setup_project(tmp_path)
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        payload = specify_cli._run_prd_helper("init-scan", run_slug="Proxy Audit")
    finally:
        os.chdir(old_cwd)

    assert payload["mode"] == "init-scan"
    assert payload["surfaces"]["prd_scan"] is True
    assert payload["surfaces"]["coverage_ledger_json"] is True
    assert payload["surfaces"]["capability_ledger_json"] is True
    assert payload["surfaces"]["artifact_contracts_json"] is True
    assert payload["surfaces"]["reconstruction_checklist_json"] is True
    state = (Path(payload["workspace_path"]) / "workflow-state.md").read_text(encoding="utf-8")
    assert "- active_command: `sp-prd-scan`" in state
    assert "- phase_mode: `analysis-only`" in state


def test_python_prd_helper_wrapper_supports_prd_build_status(tmp_path, monkeypatch):
    project = _setup_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-proxy-audit"
    (run_dir / "master").mkdir(parents=True)
    (run_dir / "exports").mkdir()
    (run_dir / "master" / "master-pack.md").write_text("# Master Pack\n", encoding="utf-8")
    (run_dir / "exports" / "prd.md").write_text("# PRD\n", encoding="utf-8")
    (run_dir / "workflow-state.md").write_text("- active_command: `sp-prd-build`\n", encoding="utf-8")

    payload = _run_json(["bash", str(BASH_HELPER), str(project), "status-build", "260504-proxy-audit"])

    assert payload["mode"] == "status-build"
    assert payload["surfaces"]["master_pack"] is True
    assert payload["surfaces"]["prd_export"] is True
```

- [ ] **Step 2: Run the helper tests to verify they fail**

Run:

```bash
pytest tests/test_prd_cli_helpers.py -q
```

Expected: FAIL because the helper only knows `init` and `status`, and its surface map still assumes the old one-step artifact set.

- [ ] **Step 3: Refactor both helper scripts to support scan/build-specific modes and surfaces**

In both `scripts/bash/prd-state.sh` and `scripts/powershell/prd-state.ps1`:

- add modes:
  - `init-scan`
  - `status-scan`
  - `status-build`
  - keep `init` and `status` as compatibility aliases
- create new scan surfaces:
  - `prd_scan`
  - `coverage_ledger`
  - `coverage_ledger_json`
  - `capability_ledger_json`
  - `artifact_contracts_json`
  - `reconstruction_checklist_json`
  - `scan_packets`
  - `worker_results`
- create build surfaces:
  - `master_pack`
  - `prd_export`
  - `reconstruction_appendix`
  - `data_model`
  - `integration_contracts`
  - `runtime_behaviors`
- write `workflow-state.md` with `sp-prd-scan` for scan init
- keep `sp-prd` only when compatibility mode is explicitly used

Use this `EXPECTED_SURFACES` shape in both helpers:

```python
EXPECTED_SURFACES = {
    "workspace": ".",
    "evidence": "evidence",
    "scan_packets": "scan-packets",
    "worker_results": "worker-results",
    "master": "master",
    "exports": "exports",
    "workflow_state": "workflow-state.md",
    "prd_scan": "prd-scan.md",
    "coverage_ledger": "coverage-ledger.md",
    "coverage_ledger_json": "coverage-ledger.json",
    "capability_ledger_json": "capability-ledger.json",
    "artifact_contracts_json": "artifact-contracts.json",
    "reconstruction_checklist_json": "reconstruction-checklist.json",
    "master_pack": "master/master-pack.md",
    "prd_export": "exports/prd.md",
    "reconstruction_appendix": "exports/reconstruction-appendix.md",
    "data_model": "exports/data-model.md",
    "integration_contracts": "exports/integration-contracts.md",
    "runtime_behaviors": "exports/runtime-behaviors.md",
}
```

- [ ] **Step 4: Re-run the helper tests**

Run:

```bash
pytest tests/test_prd_cli_helpers.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/bash/prd-state.sh scripts/powershell/prd-state.ps1 tests/test_prd_cli_helpers.py
git commit -m "feat: extend prd helpers for scan build state surfaces"
```

### Task 4: Register `prd-scan` and `prd-build` in the CLI and hook state surfaces

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Modify: `src/specify_cli/hooks/state_validation.py`
- Modify: `src/specify_cli/hooks/checkpoint.py`
- Modify: `tests/contract/test_hook_cli_surface.py`

- [ ] **Step 1: Add failing CLI and hook contract tests for the new commands**

Append these tests to `tests/contract/test_hook_cli_surface.py`:

```python
def test_hook_validate_state_supports_prd_scan_command(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-demo-prd-scan"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo PRD Scan",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-prd-scan`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `analysis-only`",
                "- summary: reconstruction scan",
                "",
                "## Allowed Artifact Writes",
                "",
                "- prd-scan.md",
                "- coverage-ledger.json",
                "- artifact-contracts.json",
                "",
                "## Forbidden Actions",
                "",
                "- write exports",
                "",
                "## Authoritative Files",
                "",
                "- workflow-state.md",
                "- prd-scan.md",
                "- artifact-contracts.json",
                "",
                "## Next Command",
                "",
                "- `/sp.prd-build`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-state", "--command", "prd-scan", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "ok"
    assert payload["data"]["checkpoint"]["active_command"] == "sp-prd-scan"


def test_hook_checkpoint_supports_prd_build_command(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-demo-prd-build"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo PRD Build",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-prd-build`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `analysis-only`",
                "- summary: reconstruction build",
                "",
                "## Allowed Artifact Writes",
                "",
                "- master/master-pack.md",
                "- exports/prd.md",
                "",
                "## Forbidden Actions",
                "",
                "- rescan repository ad hoc",
                "",
                "## Authoritative Files",
                "",
                "- workflow-state.md",
                "- master/master-pack.md",
                "- exports/prd.md",
                "",
                "## Next Command",
                "",
                "- `/sp.prd-build`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "checkpoint", "--command", "prd-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "ok"
    assert payload["data"]["checkpoint"]["active_command"] == "sp-prd-build"
```

- [ ] **Step 2: Run the hook contract tests to verify they fail**

Run:

```bash
pytest tests/contract/test_hook_cli_surface.py -q -k "prd_scan_command or prd_build_command"
```

Expected: FAIL because the CLI hook surfaces only understand `prd`.

- [ ] **Step 3: Add the new commands and command-name handling**

In `src/specify_cli/__init__.py`:

- add `@app.command("prd-scan")`
- add `@app.command("prd-build")`
- wire both through `_run_prd_helper(...)`
- update helper modes:
  - `prd-scan` should call `init-scan` or `status-scan`
  - `prd-build` should call `status-build`
- keep `@app.command("prd")` as compatibility entrypoint with wording that points to the new commands
- update workflow routing text blocks, help summaries, and `COMMAND_GUIDANCE` entries so `prd-scan` and `prd-build` are canonical and `prd` is deprecated

Add these guidance entries:

```python
"prd-scan": "Use when an existing repository needs read-only reconstruction scan outputs before final PRD synthesis.",
"prd-build": "Use when a validated PRD scan package exists and the final PRD suite must be compiled from it.",
"prd": "Deprecated compatibility entrypoint for reverse-PRD work; prefer prd-scan followed by prd-build.",
```

In `src/specify_cli/hooks/state_validation.py`:

- extend `EXPECTED_WORKFLOW_STATE` with:

```python
"prd-scan": ("sp-prd-scan", "analysis-only"),
"prd-build": ("sp-prd-build", "analysis-only"),
```

In `src/specify_cli/hooks/checkpoint.py`:

- add `prd-scan` and `prd-build` to the workflow-state command set

- [ ] **Step 4: Re-run the hook tests**

Run:

```bash
pytest tests/contract/test_hook_cli_surface.py -q -k "prd_scan_command or prd_build_command or prd"
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/__init__.py src/specify_cli/hooks/state_validation.py src/specify_cli/hooks/checkpoint.py tests/contract/test_hook_cli_surface.py
git commit -m "feat: register prd scan build cli and hook state surfaces"
```

### Task 5: Enforce scan/build artifact validation and build refusal

**Files:**
- Modify: `src/specify_cli/hooks/artifact_validation.py`
- Modify: `tests/contract/test_hook_cli_surface.py`

- [ ] **Step 1: Add failing artifact-validation tests for `prd-scan` and `prd-build`**

Append these tests to `tests/contract/test_hook_cli_surface.py`:

```python
def test_hook_validate_artifacts_supports_prd_scan_command(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-demo-prd-scan"
    run_dir.mkdir(parents=True, exist_ok=True)
    for relative, content in {
        "workflow-state.md": "# Workflow State\n",
        "prd-scan.md": "# PRD Scan\n",
        "coverage-ledger.md": "# Coverage Ledger\n",
        "coverage-ledger.json": "{\"version\": 1, \"rows\": []}\n",
        "capability-ledger.json": "{\"capabilities\": []}\n",
        "artifact-contracts.json": "{\"artifacts\": []}\n",
        "reconstruction-checklist.json": "{\"checks\": []}\n",
    }.items():
        path = run_dir / relative
        path.write_text(content, encoding="utf-8")
    (run_dir / "scan-packets").mkdir()
    (run_dir / "evidence").mkdir()
    (run_dir / "worker-results").mkdir()

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "prd-scan", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "ok"


def test_hook_validate_artifacts_blocks_shallow_prd_build(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-demo-prd-build"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (run_dir / "capability-ledger.json").write_text("{\"capabilities\": [{\"id\": \"CAP-001\", \"tier\": \"critical\", \"status\": \"surface-only\"}]}\n", encoding="utf-8")
    (run_dir / "artifact-contracts.json").write_text("{\"artifacts\": []}\n", encoding="utf-8")
    master_dir = run_dir / "master"
    master_dir.mkdir()
    (master_dir / "master-pack.md").write_text("# Master Pack\n", encoding="utf-8")
    exports_dir = run_dir / "exports"
    exports_dir.mkdir()
    (exports_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "prd-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("critical" in message.lower() or "artifact" in message.lower() for message in payload["errors"])
```

- [ ] **Step 2: Run the artifact tests to verify they fail**

Run:

```bash
pytest tests/contract/test_hook_cli_surface.py -q -k "prd_scan or prd_build"
```

Expected: FAIL because `REQUIRED_ARTIFACTS` and `_validate_prd_artifacts` only know the old `prd` artifact set.

- [ ] **Step 3: Add `prd-scan` and `prd-build` required artifact contracts**

In `src/specify_cli/hooks/artifact_validation.py`:

- extend `REQUIRED_ARTIFACTS` with:

```python
"prd-scan": (
    "workflow-state.md",
    "prd-scan.md",
    "coverage-ledger.md",
    "coverage-ledger.json",
    "capability-ledger.json",
    "artifact-contracts.json",
    "reconstruction-checklist.json",
    "scan-packets",
    "evidence",
    "worker-results",
),
"prd-build": (
    "workflow-state.md",
    "capability-ledger.json",
    "artifact-contracts.json",
    "master/master-pack.md",
    "exports/prd.md",
),
```

- split the current `_validate_prd_artifacts` into:
  - `_validate_prd_scan_artifacts`
  - `_validate_prd_build_artifacts`
- for `prd-build`, require:
  - `exports/reconstruction-appendix.md`
  - `exports/data-model.md`
  - `exports/integration-contracts.md`
  - `exports/runtime-behaviors.md`
  - at least one `critical` capability in `capability-ledger.json` must not be `surface-only`

Use a simple parser for the new JSON checks:

```python
import json


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))
```

- [ ] **Step 4: Re-run the artifact validation tests**

Run:

```bash
pytest tests/contract/test_hook_cli_surface.py -q -k "prd_scan or prd_build or validate_artifacts_supports_prd_command"
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/hooks/artifact_validation.py tests/contract/test_hook_cli_surface.py
git commit -m "feat: validate prd scan build artifact contracts"
```

### Task 6: Update passive routing and generated workflow docs

**Files:**
- Modify: `templates/passive-skills/project-to-prd/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Modify: `docs/installation.md`
- Modify: `templates/project-map/WORKFLOWS.md`
- Modify: `templates/project-map/root/WORKFLOWS.md`

- [ ] **Step 1: Write a small failing routing/doc assertion test**

Append this test to `tests/test_passive_skill_guidance.py`:

```python
def test_project_to_prd_skill_routes_to_prd_scan_then_prd_build() -> None:
    content = _read("templates/passive-skills/project-to-prd/SKILL.md")
    lowered = content.lower()

    assert "sp-prd-scan" in content
    assert "sp-prd-build" in content
    assert "deprecated" in lowered
```

- [ ] **Step 2: Run the passive skill test to verify it fails**

Run:

```bash
pytest tests/test_passive_skill_guidance.py -q -k "project_to_prd"
```

Expected: FAIL because the passive skill still routes directly to `sp-prd`.

- [ ] **Step 3: Update routing docs and skills to the new canonical flow**

Make these exact wording shifts:

- In `templates/passive-skills/project-to-prd/SKILL.md`:
  - replace “route it to the active `sp-prd` workflow” with “route it to `sp-prd-scan`, then `sp-prd-build`”
  - describe `sp-prd` as deprecated compatibility-only
- In `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`:
  - replace the `sp-prd` rule with `sp-prd-scan` and `sp-prd-build`
  - change “Existing-project PRD extraction: `{{invoke:prd}}`” to `{{invoke:prd-scan}} -> {{invoke:prd-build}}`
- In `README.md`, `docs/quickstart.md`, `docs/installation.md`, and `PROJECT-HANDBOOK.md`:
  - document the canonical reverse-PRD flow as `prd-scan -> prd-build`
  - mark `prd` as deprecated compatibility entrypoint
- In `templates/project-map/WORKFLOWS.md` and `templates/project-map/root/WORKFLOWS.md`:
  - update generated workflow descriptions so downstream handbooks stop calling `sp-prd` the primary workflow

- [ ] **Step 4: Re-run the routing and template tests**

Run:

```bash
pytest tests/test_passive_skill_guidance.py tests/test_prd_template_guidance.py tests/test_prd_scan_build_template_guidance.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/passive-skills/project-to-prd/SKILL.md templates/passive-skills/spec-kit-workflow-routing/SKILL.md PROJECT-HANDBOOK.md README.md docs/quickstart.md docs/installation.md templates/project-map/WORKFLOWS.md templates/project-map/root/WORKFLOWS.md tests/test_passive_skill_guidance.py
git commit -m "docs: route reverse prd work through prd scan build"
```

### Task 7: Run full regression checks and reconcile compatibility behavior

**Files:**
- Modify as needed based on failing tests from prior tasks.

- [ ] **Step 1: Run the focused regression suite**

Run:

```bash
pytest tests/test_prd_template_guidance.py tests/test_prd_scan_build_template_guidance.py tests/test_prd_cli_helpers.py tests/test_passive_skill_guidance.py tests/contract/test_hook_cli_surface.py -q
```

Expected: PASS.

- [ ] **Step 2: Run integration or generated-skill tests that mention `sp-prd` if previous commands exposed failures**

Run:

```bash
pytest tests/integrations -q -k "prd"
```

Expected: PASS, or zero selected tests if no integration test keys match.

- [ ] **Step 3: Inspect the diff for any remaining one-step `sp-prd` primary-language leaks**

Run:

```bash
rg -n "primary reverse PRD|current-state PRD suite|\\$sp-prd|/sp-prd|sp-prd` is a peer|Existing-project PRD extraction: `\\{\\{invoke:prd\\}\\}`" README.md PROJECT-HANDBOOK.md docs templates src tests
```

Expected: only compatibility wording for `prd`, plus canonical wording for `prd-scan` and `prd-build`.

- [ ] **Step 4: Review the final staged diff**

Run:

```bash
git diff -- templates/commands/prd.md templates/commands/prd-scan.md templates/commands/prd-build.md templates/passive-skills/project-to-prd/SKILL.md templates/passive-skills/spec-kit-workflow-routing/SKILL.md scripts/bash/prd-state.sh scripts/powershell/prd-state.ps1 src/specify_cli/__init__.py src/specify_cli/hooks/state_validation.py src/specify_cli/hooks/checkpoint.py src/specify_cli/hooks/artifact_validation.py PROJECT-HANDBOOK.md README.md docs/quickstart.md docs/installation.md templates/project-map/WORKFLOWS.md templates/project-map/root/WORKFLOWS.md tests/test_prd_template_guidance.py tests/test_prd_scan_build_template_guidance.py tests/test_prd_cli_helpers.py tests/test_passive_skill_guidance.py tests/contract/test_hook_cli_surface.py
```

Expected: the diff shows a coherent scan/build migration with `prd` preserved only as a deprecated compatibility surface.

- [ ] **Step 5: Commit**

```bash
git add templates/commands/prd.md templates/commands/prd-scan.md templates/commands/prd-build.md templates/passive-skills/project-to-prd/SKILL.md templates/passive-skills/spec-kit-workflow-routing/SKILL.md scripts/bash/prd-state.sh scripts/powershell/prd-state.ps1 src/specify_cli/__init__.py src/specify_cli/hooks/state_validation.py src/specify_cli/hooks/checkpoint.py src/specify_cli/hooks/artifact_validation.py PROJECT-HANDBOOK.md README.md docs/quickstart.md docs/installation.md templates/project-map/WORKFLOWS.md templates/project-map/root/WORKFLOWS.md tests/test_prd_template_guidance.py tests/test_prd_scan_build_template_guidance.py tests/test_prd_cli_helpers.py tests/test_passive_skill_guidance.py tests/contract/test_hook_cli_surface.py
git commit -m "feat: migrate reverse prd workflow to prd scan build"
```

## Spec Coverage Check

This plan covers every approved requirement from `docs/superpowers/specs/2026-05-04-prd-scan-build-reconstruction-design.md`:

- two-step workflow replacement: Tasks 1, 2, 4, 6
- deprecated `sp-prd` compatibility entrypoint: Tasks 2, 4, 6, 7
- scan/build state helper changes: Task 3
- CLI routing and command registration: Task 4
- scan/build validation and refusal behavior: Task 5
- passive skill and workflow routing convergence: Task 6
- docs/test/help-text convergence: Tasks 4, 6, 7

## Self-Review

- No placeholder phrases such as `TODO` or `implement later` remain in this plan.
- Every task names exact files and commands.
- Test-first flow exists for templates, helpers, hooks, and routing changes.
- `prd` remains compatibility-only in every task; no later task re-promotes it accidentally.
