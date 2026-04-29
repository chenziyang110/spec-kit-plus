# Map Scan / Map Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the one-step `sp-map-codebase` workflow with a breaking two-step `sp-map-scan -> sp-map-build` flow that produces a complete scan package before atlas construction.

**Architecture:** Shared command templates remain the source of truth, so the first implementation slice adds new template tests and command templates. Integration-specific code then follows the shared template inventory, with Codex receiving explicit native multi-agent augmentation for both new commands. Routing, docs, learning hooks, freshness messages, and generated-surface tests are updated in one pass so no user-facing path still treats `sp-map-codebase` as the brownfield gate.

**Tech Stack:** Python 3.13, Typer CLI, pytest, Markdown/TOML command templates, Spec Kit integration generators, shell/PowerShell helper scripts.

---

## Context

Read before editing:

- `docs/superpowers/specs/2026-04-29-map-scan-build-design.md`
- `templates/commands/map-codebase.md`
- `templates/commands/plan.md`
- `templates/commands/tasks.md`
- `templates/commands/implement.md`
- `src/specify_cli/integrations/base.py`
- `src/specify_cli/integrations/codex/__init__.py`
- `PROJECT-HANDBOOK.md`

The working tree may already contain user changes. Do not reset or revert unrelated files. When a task touches a dirty file, inspect its current content and patch only the relevant lines.

## File Structure

Create:

- `templates/commands/map-scan.md` - shared command template for full project-relevant inventory, coverage ledger creation, and scan packet generation.
- `templates/commands/map-build.md` - shared command template for validating scan packages, dispatching explorer packets, writing the atlas, and reverse coverage validation.
- `templates/command-partials/map-scan/shell.md` - short objective/context partial for `sp-map-scan`.
- `templates/command-partials/map-build/shell.md` - short objective/context partial for `sp-map-build`.
- `tests/test_map_scan_build_template_guidance.py` - focused assertions for the new two-command contract.

Delete:

- `templates/commands/map-codebase.md`
- `templates/command-partials/map-codebase/shell.md`
- `tests/test_map_codebase_template_guidance.py`

Modify:

- `templates/commands/analyze.md`
- `templates/commands/checklist.md`
- `templates/commands/clarify.md`
- `templates/commands/constitution.md`
- `templates/commands/debug.md`
- `templates/commands/fast.md`
- `templates/commands/implement.md`
- `templates/commands/plan.md`
- `templates/commands/quick.md`
- `templates/commands/specify.md`
- `templates/commands/tasks.md`
- `templates/constitution-template.md`
- `templates/command-partials/constitution/shell.md`
- `templates/passive-skills/spec-kit-project-map-gate/SKILL.md`
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- `src/specify_cli/__init__.py`
- `src/specify_cli/extensions.py`
- `src/specify_cli/learnings.py`
- `src/specify_cli/project_map_status.py`
- `src/specify_cli/codex_team/api_surface.py`
- `src/specify_cli/hooks/learning.py`
- `src/specify_cli/integrations/claude/__init__.py`
- `src/specify_cli/integrations/claude/hooks/claude-hook-dispatch.py`
- `src/specify_cli/integrations/codex/__init__.py`
- `src/specify_cli/integrations/gemini/hooks/gemini-hook-dispatch.py`
- `scripts/bash/update-agent-context.sh`
- `scripts/bash/project-map-freshness.sh`
- `scripts/powershell/update-agent-context.ps1`
- `scripts/powershell/project-map-freshness.ps1`
- `AGENTS.md`
- `README.md`
- `docs/quickstart.md`
- template and integration tests that currently assert `map-codebase`

## Command Naming Rules

Use these replacements consistently:

- User-facing brownfield gate: `sp-map-scan -> sp-map-build`
- Slash form: `/sp-map-scan -> /sp-map-build`
- Codex skill form: `$sp-map-scan -> $sp-map-build`
- Generic workflow names: `map-scan` and `map-build`
- Freshness completion reason: `map-build`
- Learning command names: `map-scan` for scan-package problems, `map-build` for atlas build problems

Do not keep `sp-map-codebase` as a generated command, skill, or primary guidance string.

---

### Task 1: Add Failing Template Contract Tests

**Files:**
- Create: `tests/test_map_scan_build_template_guidance.py`
- Modify: `tests/test_alignment_templates.py`
- Delete later: `tests/test_map_codebase_template_guidance.py`

- [ ] **Step 1: Create focused failing tests for `map-scan` and `map-build`**

Create `tests/test_map_scan_build_template_guidance.py` with this content:

```python
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_map_scan_template_defines_complete_scan_package_contract() -> None:
    content = _read("templates/commands/map-scan.md")
    lowered = content.lower()

    assert "sp-map-scan" in content
    assert "sp-map-build" in content
    assert ".specify/project-map/map-scan.md" in content
    assert ".specify/project-map/coverage-ledger.md" in content
    assert ".specify/project-map/coverage-ledger.json" in content
    assert ".specify/project-map/scan-packets/<lane-id>.md" in content
    assert "full project-relevant inventory" in lowered
    assert "nested directories" in lowered
    assert "rg --files" in content
    assert "Git-tracked files" in content
    assert "excluded_from_deep_read" in content
    assert "vendor-cache-build-output" in content
    assert "`unknown` is a scan failure" in content
    assert "`inventory`" in content
    assert "`sampled`" in content
    assert "`deep-read`" in content
    assert "`critical`" in content
    assert "`important`" in content
    assert "`low-risk`" in content
    assert "scan-packets/<lane-id>.md" in content
    assert "Coverage Classification" in content
    assert "Criticality Scoring" in content


def test_map_scan_template_preserves_required_scan_dimensions() -> None:
    content = _read("templates/commands/map-scan.md")
    lowered = content.lower()

    required_phrases = [
        "project shape and stack",
        "architecture overview",
        "directory ownership",
        "module dependency graph",
        "core code elements",
        "entry and api surfaces",
        "data and state flows",
        "user and maintainer workflows",
        "integrations and protocol boundaries",
        "build, release, and runtime",
        "testing and verification",
        "risk, security, observability, and evolution",
        "template and generated-surface propagation",
        "coverage reverse index",
    ]

    for phrase in required_phrases:
        assert phrase in lowered


def test_map_build_template_refuses_incomplete_scan_packages() -> None:
    content = _read("templates/commands/map-build.md")
    lowered = content.lower()

    assert "sp-map-build" in content
    assert "sp-map-scan" in content
    assert "coverage-ledger.json" in content
    assert "scan-packets" in content
    assert "begins with validation, not writing" in lowered
    assert "must not guess and continue" in lowered
    assert "scan gap report" in lowered
    assert "packet results without paths read" in lowered
    assert "packet results that only summarize without evidence" in lowered
    assert "unresolved critical rows" in lowered
    assert "reverse coverage validation" in lowered
    assert "complete-refresh" in content
    assert "PROJECT-HANDBOOK.md" in content
    assert ".specify/project-map/index/*.json" in content
    assert ".specify/project-map/root/*.md" in content
    assert ".specify/project-map/modules/<module-id>/*.md" in content


def test_map_build_template_requires_reverse_coverage_closure() -> None:
    content = _read("templates/commands/map-build.md")
    lowered = content.lower()

    required_phrases = [
        "every `critical` row appears in at least one final atlas target",
        "every `important` row appears in a final atlas target",
        "every scan packet is consumed",
        "every accepted packet result has paths read and confidence",
        "owner, consumer, change propagation, and verification",
        "known unknowns",
        "low-confidence areas",
        "deep_stale",
        "excluded bucket has a reason and revisit condition",
    ]

    for phrase in required_phrases:
        assert phrase in lowered
```

- [ ] **Step 2: Update the command-template inventory assertion**

In `tests/test_alignment_templates.py`, update `test_new_analysis_workflow_command_templates_exist` so it asserts the new templates and no old map template:

```python
def test_new_analysis_workflow_command_templates_exist():
    command_dir = PROJECT_ROOT / "templates" / "commands"
    template_stems = {path.stem for path in command_dir.glob("*.md")}

    assert "map-scan" in template_stems
    assert "map-build" in template_stems
    assert "map-codebase" not in template_stems
    assert "clarify" in template_stems
    assert "deep-research" in template_stems
    assert "explain" in template_stems
    assert "spec-extend" not in template_stems
```

- [ ] **Step 3: Add both new commands to the learning-template coverage map**

In `tests/test_alignment_templates.py`, update the `command_templates` dictionary in `test_command_templates_use_first_party_learning_hooks` by replacing the `map-codebase` row with:

```python
        "map-scan": "templates/commands/map-scan.md",
        "map-build": "templates/commands/map-build.md",
```

- [ ] **Step 4: Run the focused tests and verify the expected RED state**

Run:

```powershell
pytest tests/test_map_scan_build_template_guidance.py tests/test_alignment_templates.py -q
```

Expected: fails because `templates/commands/map-scan.md` and `templates/commands/map-build.md` do not exist yet, and old `map-codebase` assertions still exist in nearby tests.

- [ ] **Step 5: Commit the RED tests**

Run:

```powershell
git add tests/test_map_scan_build_template_guidance.py tests/test_alignment_templates.py
git commit -m "test: define map scan build workflow contract"
```

Expected: commit includes only the new/updated tests. If unrelated dirty files appear, unstage them with `git restore --staged <path>` and leave their worktree content untouched.

---

### Task 2: Create `map-scan` and `map-build` Templates

**Files:**
- Create: `templates/commands/map-scan.md`
- Create: `templates/commands/map-build.md`
- Create: `templates/command-partials/map-scan/shell.md`
- Create: `templates/command-partials/map-build/shell.md`
- Delete: `templates/commands/map-codebase.md`
- Delete: `templates/command-partials/map-codebase/shell.md`
- Delete: `tests/test_map_codebase_template_guidance.py`

- [ ] **Step 1: Create the `map-scan` shell partial**

Create `templates/command-partials/map-scan/shell.md`:

```markdown
{{spec-kit-include: ../common/user-input.md}}

## Objective

Generate a complete project-relevant scan package for the current codebase.

## Context

- Primary inputs: the live repository tree, any existing handbook/project-map artifacts, passive learning files, and optional focus hints from `$ARGUMENTS`.
- This command owns scan-package outputs only; it must not write final atlas truth.
- The resulting scan package must let `sp-map-build` construct the handbook/project-map atlas without inventing scan scope.
```

- [ ] **Step 2: Create the `map-build` shell partial**

Create `templates/command-partials/map-build/shell.md`:

```markdown
{{spec-kit-include: ../common/user-input.md}}

## Objective

Build or refresh the canonical handbook/project-map atlas from a completed scan package.

## Context

- Primary inputs: `.specify/project-map/map-scan.md`, `.specify/project-map/coverage-ledger.json`, `.specify/project-map/coverage-ledger.md`, `.specify/project-map/scan-packets/*.md`, and the live repository.
- This command owns final atlas outputs and freshness metadata.
- If the scan package is incomplete, produce a scan gap report and return to `sp-map-scan` instead of writing a shallow atlas.
```

- [ ] **Step 3: Create `templates/commands/map-scan.md`**

Create `templates/commands/map-scan.md` by adapting the scan side of `docs/superpowers/specs/2026-04-29-map-scan-build-design.md`. Include these exact anchors so tests and generated skills can rely on them:

```markdown
---
description: Use when handbook/project-map coverage is missing, stale, or insufficient and you need to generate the complete scan package required before atlas construction.
workflow_contract:
  when_to_use: A workflow needs reliable handbook/project-map coverage and the current navigation artifacts are missing, stale, or too weak for the touched area.
  primary_objective: Generate a complete project-relevant inventory, coverage ledger, and scan packet set for `sp-map-build`.
  primary_outputs: '`.specify/project-map/map-scan.md`, `.specify/project-map/coverage-ledger.md`, `.specify/project-map/coverage-ledger.json`, and `.specify/project-map/scan-packets/*.md`.'
  default_handoff: /sp-map-build after the scan package passes readiness checks.
---

{{spec-kit-include: ../command-partials/map-scan/shell.md}}

This workflow is the explicit brownfield scan entrypoint. When another workflow needs fresh navigation coverage, it should run `/sp-map-scan` first and then `/sp-map-build`.

## Hard Boundary

- `sp-map-scan` must not write final atlas truth.
- `sp-map-scan` must not edit `PROJECT-HANDBOOK.md`, `.specify/project-map/index/*.json`, `.specify/project-map/root/*.md`, or `.specify/project-map/modules/**`.
- `sp-map-scan` writes only the scan package:
  - `.specify/project-map/map-scan.md`
  - `.specify/project-map/coverage-ledger.md`
  - `.specify/project-map/coverage-ledger.json`
  - `.specify/project-map/scan-packets/<lane-id>.md`
```

Then add the detailed contract sections from the design document:

- Passive Project Learning Layer using `--command map-scan`
- Output Contract
- Phase 1: Full Project-Relevant Inventory
- Phase 2: Coverage Classification
- Phase 3: Reading Depth Assignment
- Phase 4: Criticality Scoring
- Phase 5: Scan Packet Generation
- Required Scan Dimensions
- `map-scan.md` Structure
- `coverage-ledger.json` Shape
- Scan Packet Template
- Build Readiness Checklist
- Report Completion

Use the design's required categories, criticality values, reading-depth values, JSON shape, and scan packet template verbatim. Keep the phrase `` `unknown` is a scan failure `` in the template.

- [ ] **Step 4: Create `templates/commands/map-build.md`**

Create `templates/commands/map-build.md` by adapting the build side of the design. Include these exact anchors:

```markdown
---
description: Use after `sp-map-scan` has produced a complete scan package and you need to build or refresh `PROJECT-HANDBOOK.md` and `.specify/project-map/**`.
workflow_contract:
  when_to_use: A completed scan package exists and the canonical handbook/project-map atlas must be built or refreshed from it.
  primary_objective: Validate the scan package, dispatch read-only explorer packets, write the canonical atlas, and prove reverse coverage closure.
  primary_outputs: '`PROJECT-HANDBOOK.md`, `.specify/project-map/index/*.json`, `.specify/project-map/root/*.md`, `.specify/project-map/modules/<module-id>/*.md`, and `.specify/project-map/index/status.json`.'
  default_handoff: Return to the blocked workflow that required fresh navigation coverage.
---

{{spec-kit-include: ../command-partials/map-build/shell.md}}

`sp-map-build` begins with validation, not writing.
```

Then add these sections:

- Passive Project Learning Layer using `--command map-build`
- Required Inputs
- Readiness Refusal Rules
- Execution Strategy
- Explorer Packet Dispatch
- Atlas Output Contract
- Root and Module Document Detail Rules
- Reverse Coverage Validation
- First-Party Workflow Quality Hooks
- Report Completion

Keep these phrases exactly:

- `must not guess and continue`
- `scan gap report`
- `packet results without paths read`
- `packet results that only summarize without evidence`
- `unresolved critical rows`
- `reverse coverage validation`
- `every accepted packet result has paths read and confidence`

- [ ] **Step 5: Remove the old one-step map template files**

Delete:

```text
templates/commands/map-codebase.md
templates/command-partials/map-codebase/shell.md
tests/test_map_codebase_template_guidance.py
```

- [ ] **Step 6: Run focused template tests**

Run:

```powershell
pytest tests/test_map_scan_build_template_guidance.py tests/test_alignment_templates.py -q
```

Expected: new map-scan/map-build tests pass or fail only on remaining old `sp-map-codebase` assertions in `test_alignment_templates.py`. Fix any remaining assertions in Task 3, not by weakening the new template contract.

- [ ] **Step 7: Commit the template split**

Run:

```powershell
git add templates/commands/map-scan.md templates/commands/map-build.md templates/command-partials/map-scan/shell.md templates/command-partials/map-build/shell.md
git add -u templates/commands/map-codebase.md templates/command-partials/map-codebase/shell.md tests/test_map_codebase_template_guidance.py
git commit -m "feat: split map workflow into scan and build templates"
```

Expected: commit creates the two new command templates and removes the old one-step template.

---

### Task 3: Route Existing Workflow Templates Through `map-scan -> map-build`

**Files:**
- Modify: `templates/commands/analyze.md`
- Modify: `templates/commands/checklist.md`
- Modify: `templates/commands/clarify.md`
- Modify: `templates/commands/constitution.md`
- Modify: `templates/commands/debug.md`
- Modify: `templates/commands/fast.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/constitution-template.md`
- Modify: `templates/command-partials/constitution/shell.md`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_debug_template_guidance.py`
- Modify: `tests/test_fast_template_guidance.py`
- Modify: `tests/test_quick_template_guidance.py`
- Modify: `tests/test_specify_guidance_docs.py`

- [ ] **Step 1: Replace hard routing text in command templates**

For each command template listed above, replace direct one-step text with the two-step wording:

```markdown
run `/sp-map-scan` to produce the scan package, then run `/sp-map-build` to refresh the canonical handbook/project-map atlas before continuing
```

For post-completion refresh guidance, use:

```markdown
run `/sp-map-scan` followed by `/sp-map-build` before final completion reporting so `PROJECT-HANDBOOK.md`, `.specify/project-map/**`, and `.specify/project-map/index/status.json` are refreshed in the same pass
```

For cases where the current workflow cannot complete the refresh, use:

```markdown
mark `.specify/project-map/index/status.json` dirty through the project-map freshness helper and recommend `/sp-map-scan -> /sp-map-build` before the next brownfield workflow proceeds
```

- [ ] **Step 2: Replace passive gate wording**

In `templates/passive-skills/spec-kit-project-map-gate/SKILL.md`, replace old route text with:

```markdown
If the repository has no trustworthy handbook/project-map coverage for the touched area, use `sp-map-scan` first to produce the scan package and then `sp-map-build` to refresh `PROJECT-HANDBOOK.md` and `.specify/project-map/**` before continuing.
```

In `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`, replace old route text with:

```markdown
- Use `sp-map-scan -> sp-map-build` before other workflow steps when handbook or project-map coverage is missing, stale, or too broad for the touched area.
```

- [ ] **Step 3: Update alignment tests for the new route**

In `tests/test_alignment_templates.py`, replace assertions such as:

```python
assert "run `/sp-map-codebase` before continuing" in content
```

with:

```python
assert "run `/sp-map-scan`" in content
assert "run `/sp-map-build`" in content
```

For recommendation assertions, replace:

```python
assert "recommend `/sp-map-codebase`" in content
```

with:

```python
assert "recommend `/sp-map-scan -> /sp-map-build`" in content
```

- [ ] **Step 4: Update focused template guidance tests**

Update tests that currently assert old map guidance:

```python
assert "run `/sp-map-codebase` before final completion reporting" in content.lower()
```

to:

```python
lowered = content.lower()
assert "run `/sp-map-scan` followed by `/sp-map-build` before final completion reporting" in lowered
```

Apply this pattern in:

- `tests/test_debug_template_guidance.py`
- `tests/test_fast_template_guidance.py`
- `tests/test_quick_template_guidance.py`
- `tests/integrations/test_integration_codex.py`

- [ ] **Step 5: Run targeted template tests**

Run:

```powershell
pytest tests/test_map_scan_build_template_guidance.py tests/test_alignment_templates.py tests/test_debug_template_guidance.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py -q
```

Expected: tests pass for template routing or fail only on Python/generator surfaces handled in later tasks.

- [ ] **Step 6: Commit template routing changes**

Run:

```powershell
git add templates tests/test_alignment_templates.py tests/test_debug_template_guidance.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py
git commit -m "refactor: route workflows through map scan and build"
```

Expected: commit contains only shared template and related template-test changes.

---

### Task 4: Update Python Command Metadata, Freshness Messages, and Learning Targets

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Modify: `src/specify_cli/extensions.py`
- Modify: `src/specify_cli/learnings.py`
- Modify: `src/specify_cli/project_map_status.py`
- Modify: `src/specify_cli/codex_team/api_surface.py`
- Modify: `src/specify_cli/hooks/learning.py`
- Modify: `tests/test_specify_guidance_docs.py`
- Modify: `tests/hooks/test_learning_hooks.py`
- Modify: `tests/test_project_map_status.py`
- Modify: `tests/codex_team/test_tmux_smoke.py`
- Modify: `tests/contract/test_codex_team_auto_dispatch_cli.py`

- [ ] **Step 1: Update command descriptions**

In `src/specify_cli/__init__.py`, replace the `map-codebase` entry in `COMMAND_DESCRIPTIONS` with:

```python
    "map-scan": "Use when handbook/project-map coverage is missing, stale, or insufficient and you need a complete scan package before atlas construction.",
    "map-build": "Use after map-scan has produced a scan package and you need to build or refresh PROJECT-HANDBOOK.md and .specify/project-map/ from that package.",
```

- [ ] **Step 2: Update CLI freshness error messages**

In `_project_map_preflight`, change the remediation message to:

```python
        console.print(
            "Run [cyan]map-scan[/cyan] followed by [cyan]map-build[/cyan] to refresh `PROJECT-HANDBOOK.md` and `.specify/project-map/`, then retry."
        )
```

In `_ensure_project_map_artifacts_exist`, change the remediation message to:

```python
    console.print(
        "Run [cyan]map-scan[/cyan] followed by [cyan]map-build[/cyan] first so `PROJECT-HANDBOOK.md` and `.specify/project-map/*.md` exist, then retry [cyan]project-map complete-refresh[/cyan]. Use [cyan]project-map record-refresh[/cyan] only for low-level/manual recovery."
    )
```

- [ ] **Step 3: Update init output support skills**

In the "Support skills" section, replace the single map-codebase line with:

```python
    steps_lines.append(f"   - [cyan]{_display_cmd('map-scan')}[/] - Generate `.specify/project-map/map-scan.md`, coverage ledgers, and scan packets for existing code before atlas construction")
    steps_lines.append(f"   - [cyan]{_display_cmd('map-build')}[/] - Build or refresh `PROJECT-HANDBOOK.md` and `.specify/project-map/` from the completed scan package")
```

In the enhancement list, replace the old required-for-existing-code line with:

```python
            f"○ [cyan]{_display_cmd('map-scan')}[/] [bright_black](required for existing code)[/bright_black] - Produce the complete scan package before brownfield specification, planning, task generation, or implementation resumes",
            f"○ [cyan]{_display_cmd('map-build')}[/] [bright_black](required after map-scan)[/bright_black] - Build the handbook/project-map atlas from the scan package and prove reverse coverage closure",
```

- [ ] **Step 4: Update project-map freshness default reason**

In `src/specify_cli/project_map_status.py`, change `complete_project_map_refresh` to:

```python
def complete_project_map_refresh(project_root: Path) -> ProjectMapStatus:
    return mark_project_map_refreshed(
        project_root,
        head_commit=git_head_commit(project_root),
        branch=git_branch_name(project_root),
        reason="map-build",
        refresh_topics=list(TOPIC_FILES),
        refresh_scope="full",
        refresh_basis="map-build",
        changed_files_basis=[],
    )
```

- [ ] **Step 5: Update core command fallback names**

In `src/specify_cli/extensions.py`, replace `"map-codebase"` with:

```python
    "map-scan",
    "map-build",
```

- [ ] **Step 6: Update learning injection targets**

In `src/specify_cli/learnings.py`, replace `sp-map-codebase` targets with both map workflow commands:

```python
MAP_WORKFLOW_TARGETS = ["sp-map-scan", "sp-map-build"]
```

Use the constant where existing lists currently include `sp-map-codebase`. For example, replace:

```python
return ["sp-map-codebase", "sp-specify", "sp-deep-research", "sp-plan", "sp-tasks", "sp-implement", "sp-debug"]
```

with:

```python
return ["sp-map-scan", "sp-map-build", "sp-specify", "sp-deep-research", "sp-plan", "sp-tasks", "sp-implement", "sp-debug"]
```

- [ ] **Step 7: Update hook learning injection targets**

In `src/specify_cli/hooks/learning.py`, replace:

```python
"map_coverage_gap": ["sp-map-codebase", "PROJECT-HANDBOOK.md", ".specify/project-map/"],
"tooling_trap": ["sp-debug", "sp-implement", "sp-map-codebase"],
```

with:

```python
"map_coverage_gap": ["sp-map-scan", "sp-map-build", "PROJECT-HANDBOOK.md", ".specify/project-map/"],
"tooling_trap": ["sp-debug", "sp-implement", "sp-map-scan", "sp-map-build"],
```

- [ ] **Step 8: Update Codex team auto-dispatch stale-map message**

In `src/specify_cli/codex_team/api_surface.py`, replace the stale-map message with:

```python
"message": f"Project-map freshness is {freshness['freshness']}. Refresh with map-scan followed by map-build before auto-dispatch.",
```

- [ ] **Step 9: Update related tests**

Apply these expected-value changes:

```python
assert "map-build" in status_payload["last_refresh_reason"]
```

for complete-refresh tests that currently expect `"map-codebase"`.

For generated output tests, assert both new commands:

```python
assert "$sp-map-scan" in result.output
assert "$sp-map-build" in result.output
assert "$sp-map-codebase" not in result.output
```

For learning tests, assert both injection targets:

```python
assert "sp-map-scan" in result.data["injection_targets"]
assert "sp-map-build" in result.data["injection_targets"]
```

- [ ] **Step 10: Run Python metadata tests**

Run:

```powershell
pytest tests/test_project_map_status.py tests/hooks/test_learning_hooks.py tests/codex_team/test_tmux_smoke.py tests/contract/test_codex_team_auto_dispatch_cli.py -q
```

Expected: tests pass or fail only on integration-generated surfaces handled in Task 5.

- [ ] **Step 11: Commit Python metadata changes**

Run:

```powershell
git add src/specify_cli/__init__.py src/specify_cli/extensions.py src/specify_cli/learnings.py src/specify_cli/project_map_status.py src/specify_cli/codex_team/api_surface.py src/specify_cli/hooks/learning.py tests
git commit -m "refactor: update map workflow metadata"
```

Expected: commit contains command metadata, freshness reason, learning targets, and matching tests.

---

### Task 5: Update Integration-Specific Generated Surfaces

**Files:**
- Modify: `src/specify_cli/integrations/codex/__init__.py`
- Modify: `src/specify_cli/integrations/claude/__init__.py`
- Modify: `src/specify_cli/integrations/claude/hooks/claude-hook-dispatch.py`
- Modify: `src/specify_cli/integrations/gemini/hooks/gemini-hook-dispatch.py`
- Modify: `tests/integrations/test_cli.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/integrations/test_integration_claude.py`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_base_toml.py`

- [ ] **Step 1: Replace Codex map-codebase augmentation with scan/build augmentations**

In `src/specify_cli/integrations/codex/__init__.py`, remove the `_augment_shared_skill` block targeting `skills_dir / "sp-map-codebase" / "SKILL.md"` and add two blocks:

```python
        self._augment_shared_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-map-scan" / "SKILL.md",
            f"## {agent_name} Native Multi-Agent Execution",
            (
                "\n"
                f"## {agent_name} Native Multi-Agent Execution\n\n"
                f"When running `sp-map-scan` in {agent_name}, dispatch read-only inventory and classification subagents whenever the selected strategy is `native-multi-agent`.\n"
                f"- Use `spawn_agent` for bounded scan lanes such as source and architecture inventory, template/generated-surface inventory, scripts/runtime/state inventory, integrations inventory, and tests/docs/release inventory.\n"
                f"- Scan subagents must not write `PROJECT-HANDBOOK.md`, `.specify/project-map/index/*.json`, `.specify/project-map/root/*.md`, or `.specify/project-map/modules/**`.\n"
                f"- Use `wait_agent` only at the documented join points before finalizing `coverage-ledger.json` and before writing scan packets.\n"
                f"- Use `close_agent` after integrating finished scan results.\n"
            ),
        )
        self._augment_shared_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-map-build" / "SKILL.md",
            f"## {agent_name} Native Multi-Agent Execution",
            (
                "\n"
                f"## {agent_name} Native Multi-Agent Execution\n\n"
                f"When running `sp-map-build` in {agent_name}, you **MUST** dispatch explorer subagents for scan packets whenever the selected strategy is `native-multi-agent`.\n"
                f"- Use `spawn_agent` for bounded explorer packets declared under `.specify/project-map/scan-packets/`.\n"
                f"- Explorer subagents are read-only evidence collectors and must not write final atlas artifacts directly.\n"
                f"- Do not continue broad leader-local atlas writing until every required packet result has paths read, facts, confidence, unknowns, verification route, and atlas targets.\n"
                f"- Use `wait_agent` only at the documented join points before writing final atlas documents and before reverse coverage validation.\n"
                f"- Use `close_agent` after integrating finished explorer results.\n"
            ),
        )
```

- [ ] **Step 2: Update Claude argument hints**

In `src/specify_cli/integrations/claude/__init__.py`, replace:

```python
    "map-codebase": "Optional subsystem or workflow area to emphasize while mapping",
```

with:

```python
    "map-scan": "Optional subsystem, workflow, or focus area to emphasize while generating the scan package",
    "map-build": "Optional atlas build focus after a completed map-scan package exists",
```

- [ ] **Step 3: Update native hook dispatch maps**

In both hook dispatch files, replace the old map command row:

```python
    "sp-map-codebase": "map-codebase",
```

with:

```python
    "sp-map-scan": "map-scan",
    "sp-map-build": "map-build",
```

Apply this to:

- `src/specify_cli/integrations/claude/hooks/claude-hook-dispatch.py`
- `src/specify_cli/integrations/gemini/hooks/gemini-hook-dispatch.py`

- [ ] **Step 4: Update integration CLI output assertions**

In `tests/integrations/test_cli.py`, replace output assertions:

```python
assert "$sp-map-codebase" in result.output
```

with:

```python
assert "$sp-map-scan" in result.output
assert "$sp-map-build" in result.output
assert "$sp-map-codebase" not in result.output
```

For slash-command output, use:

```python
assert "/sp-map-scan" in result.output
assert "/sp-map-build" in result.output
assert "/sp-map-codebase" not in result.output
```

- [ ] **Step 5: Update generated skill existence and frontmatter assertions**

In `tests/integrations/test_cli.py`, replace:

```python
assert (skills_dir / "sp-map-codebase" / "SKILL.md").exists()
map_codebase_fm = self._frontmatter(skills_dir / "sp-map-codebase" / "SKILL.md")
assert isinstance(map_codebase_fm["description"], str) and map_codebase_fm["description"].strip()
assert map_codebase_fm["description"].startswith("Use when")
assert "handbook/project-map coverage" in map_codebase_fm["description"].lower()
```

with:

```python
assert (skills_dir / "sp-map-scan" / "SKILL.md").exists()
assert (skills_dir / "sp-map-build" / "SKILL.md").exists()
assert not (skills_dir / "sp-map-codebase" / "SKILL.md").exists()

map_scan_fm = self._frontmatter(skills_dir / "sp-map-scan" / "SKILL.md")
map_build_fm = self._frontmatter(skills_dir / "sp-map-build" / "SKILL.md")

assert isinstance(map_scan_fm["description"], str) and map_scan_fm["description"].strip()
assert isinstance(map_build_fm["description"], str) and map_build_fm["description"].strip()
assert map_scan_fm["description"].startswith("Use when")
assert map_build_fm["description"].startswith("Use after")
assert "scan package" in map_scan_fm["description"].lower()
assert "project-handbook.md" in map_build_fm["description"].lower()
```

- [ ] **Step 6: Replace Codex generated map-codebase test**

In `tests/integrations/test_integration_codex.py`, replace `test_codex_generated_sp_map_codebase_includes_native_mapping_guidance` with:

```python
def test_codex_generated_sp_map_scan_and_build_include_native_mapping_guidance(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-map-scan-build"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    scan_content = (target / ".codex" / "skills" / "sp-map-scan" / "SKILL.md").read_text(encoding="utf-8").lower()
    build_content = (target / ".codex" / "skills" / "sp-map-build" / "SKILL.md").read_text(encoding="utf-8").lower()

    assert "coverage-ledger.json" in scan_content
    assert "scan-packets/<lane-id>.md" in scan_content
    assert 'choose_execution_strategy(command_name="map-scan"' in scan_content
    assert "spawn_agent" in scan_content
    assert "inventory and classification subagents" in scan_content
    assert "must not write final atlas truth" in scan_content

    assert "project-handbook.md" in build_content
    assert ".specify/project-map/index/*.json" in build_content
    assert ".specify/project-map/root/*.md" in build_content
    assert ".specify/project-map/modules/<module-id>/*.md" in build_content
    assert 'choose_execution_strategy(command_name="map-build"' in build_content
    assert "spawn_agent" in build_content
    assert "wait_agent" in build_content
    assert "close_agent" in build_content
    assert "reverse coverage validation" in build_content
    assert "complete-refresh" in build_content
```

- [ ] **Step 7: Update base integration tests**

In base Markdown, skills, and TOML integration tests, replace generated path and command-name expectations for `sp-map-codebase` with both `sp-map-scan` and `sp-map-build`. Add negative assertions that old generated files do not exist.

Use the relevant extension per integration:

```python
assert (commands_dir / "sp.map-scan.md").exists()
assert (commands_dir / "sp.map-build.md").exists()
assert not (commands_dir / "sp.map-codebase.md").exists()
```

For skills-based integrations:

```python
assert (skills_dir / "sp-map-scan" / "SKILL.md").exists()
assert (skills_dir / "sp-map-build" / "SKILL.md").exists()
assert not (skills_dir / "sp-map-codebase" / "SKILL.md").exists()
```

- [ ] **Step 8: Run integration tests**

Run:

```powershell
pytest tests/integrations/test_cli.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py -q
```

Expected: tests pass for generated surfaces. Remaining failures should identify docs or package assertions handled in Task 6.

- [ ] **Step 9: Commit integration changes**

Run:

```powershell
git add src/specify_cli/integrations tests/integrations
git commit -m "refactor: generate map scan and build integrations"
```

Expected: commit contains integration-specific mappings and matching generated-surface tests.

---

### Task 6: Update Docs, Agent Context Blocks, and Helper Script Messaging

**Files:**
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Modify: `scripts/bash/update-agent-context.sh`
- Modify: `scripts/powershell/update-agent-context.ps1`
- Modify: `scripts/bash/project-map-freshness.sh`
- Modify: `scripts/powershell/project-map-freshness.ps1`
- Modify: `tests/test_specify_guidance_docs.py`
- Modify: `tests/test_agent_context_managed_block.py`
- Modify: `tests/test_project_map_freshness_scripts.py`

- [ ] **Step 1: Update AGENTS managed block guidance**

In `AGENTS.md`, replace the brownfield gate rules with:

```markdown
- If handbook/project-map coverage is missing, stale, or too broad, run the runtime's `map-scan` workflow entrypoint to produce the scan package, then run `map-build` to refresh the atlas before continuing.
```

And:

```markdown
- If that refresh cannot happen in the current pass, mark `.specify/project-map/index/status.json` dirty and explicitly route the next brownfield workflow through `sp-map-scan -> sp-map-build`.
```

- [ ] **Step 2: Update agent-context script managed-block strings**

Apply the same two replacement strings in:

- `scripts/bash/update-agent-context.sh`
- `scripts/powershell/update-agent-context.ps1`

Keep quote escaping correct in PowerShell:

```powershell
'- If handbook/project-map coverage is missing, stale, or too broad, run the runtime''s `map-scan` workflow entrypoint to produce the scan package, then run `map-build` to refresh the atlas before continuing.'
```

- [ ] **Step 3: Update freshness helper script messages and default reason**

In `scripts/bash/project-map-freshness.sh`, change the missing-artifact message:

```bash
echo "Run map-scan followed by map-build first so PROJECT-HANDBOOK.md and .specify/project-map/*.md exist." >&2
```

Change the complete-refresh default reason:

```bash
REASON="map-build"
```

In `scripts/powershell/project-map-freshness.ps1`, change the missing-artifact message:

```powershell
Write-Error "Cannot record a fresh project-map baseline because canonical map files are missing:`n - $($missing -join "`n - ")`nRun map-scan followed by map-build first so PROJECT-HANDBOOK.md and .specify/project-map/*.md exist."
```

Change the default reason:

```powershell
$why = if ($Reason) { $Reason } else { "map-build" }
```

- [ ] **Step 4: Update README and quickstart support skill lists**

In `README.md`, replace:

```markdown
- Support skills: `map-codebase`, `test`, `auto`, `clarify`, `deep-research`, `checklist`, `analyze`, `debug`, `explain`
```

with:

```markdown
- Support skills: `map-scan`, `map-build`, `test`, `auto`, `clarify`, `deep-research`, `checklist`, `analyze`, `debug`, `explain`
```

In `docs/quickstart.md`, replace:

```markdown
- **Support skills**: `/speckit.map-codebase`, `/speckit.auto`, `/speckit.clarify`, `/speckit.deep-research`, `/speckit.checklist`, `/speckit.analyze`, `/speckit.debug`, `/speckit.explain`
```

with:

```markdown
- **Support skills**: `/speckit.map-scan`, `/speckit.map-build`, `/speckit.auto`, `/speckit.clarify`, `/speckit.deep-research`, `/speckit.checklist`, `/speckit.analyze`, `/speckit.debug`, `/speckit.explain`
```

- [ ] **Step 5: Update brownfield prose in README and quickstart**

Use this wording in both files:

```markdown
Already have code? Run `map-scan` first to produce the scan package, then run `map-build` to generate or refresh `PROJECT-HANDBOOK.md` and `.specify/project-map/` before deeper specification, planning, task generation, or implementation work.
```

When describing workflows that discover weak atlas coverage, use:

```markdown
mark `.specify/project-map/index/status.json` dirty and run `map-scan -> map-build` as the follow-up refresh workflow
```

- [ ] **Step 6: Update docs tests**

In `tests/test_specify_guidance_docs.py`, replace old assertions with:

```python
assert "`map-scan`" in readme
assert "`map-build`" in readme
assert "`map-codebase`" not in readme
assert "/speckit.map-scan" in quickstart
assert "/speckit.map-build" in quickstart
assert "/speckit.map-codebase" not in quickstart
```

Update the brownfield test:

```python
assert "Run `map-scan` first" in readme
assert "then run `map-build`" in readme
assert "/speckit.map-scan" in quickstart
assert "/speckit.map-build" in quickstart
assert "required brownfield gate" in readme.lower()
assert "required brownfield gate" in quickstart.lower()
```

- [ ] **Step 7: Run docs and script tests**

Run:

```powershell
pytest tests/test_specify_guidance_docs.py tests/test_agent_context_managed_block.py tests/test_project_map_freshness_scripts.py -q
```

Expected: docs and managed block tests pass.

- [ ] **Step 8: Commit docs and script messaging**

Run:

```powershell
git add AGENTS.md README.md docs/quickstart.md scripts/bash/update-agent-context.sh scripts/powershell/update-agent-context.ps1 scripts/bash/project-map-freshness.sh scripts/powershell/project-map-freshness.ps1 tests/test_specify_guidance_docs.py tests/test_agent_context_managed_block.py tests/test_project_map_freshness_scripts.py
git commit -m "docs: route brownfield mapping through scan and build"
```

Expected: commit contains docs, managed context strings, helper script messages, and tests.

---

### Task 7: Sweep Remaining `map-codebase` References and Package Assertions

**Files:**
- Modify: any remaining non-historical source/test/template/docs file returned by `rg`
- Do not modify: historical design/plan docs under `docs/superpowers/specs/` and `docs/superpowers/plans/` unless the current implementation plan explicitly references them

- [ ] **Step 1: Search remaining old workflow references**

Run:

```powershell
rg -n "map-codebase|sp-map-codebase|map_codebase" -g "!**/__pycache__/**" -g "!*.pyc" .
```

Expected: remaining matches are only historical docs that describe previous work, or current spec/plan docs that intentionally discuss the replacement. No active source, template, generated-surface test, helper script, README, quickstart, or AGENTS route should still advertise `map-codebase`.

- [ ] **Step 2: Patch active leftovers**

For each active leftover, replace using the naming rules at the top of this plan. Examples:

```text
map-codebase -> map-scan followed by map-build
sp-map-codebase -> sp-map-scan -> sp-map-build
/sp-map-codebase -> /sp-map-scan -> /sp-map-build
$sp-map-codebase -> $sp-map-scan -> $sp-map-build
```

Do not change historical references in:

```text
docs/superpowers/specs/2026-04-29-map-scan-build-design.md
docs/superpowers/plans/2026-04-29-map-scan-build-implementation.md
```

- [ ] **Step 3: Update packaging tests if they assert template filenames**

In `tests/test_packaging_assets.py`, replace expected `map-codebase.md` assets with:

```python
assert "templates/commands/map-scan.md" in asset_paths
assert "templates/commands/map-build.md" in asset_paths
assert "templates/commands/map-codebase.md" not in asset_paths
```

Use the actual variable names present in that test file.

- [ ] **Step 4: Run packaging and extension tests**

Run:

```powershell
pytest tests/test_packaging_assets.py tests/test_extension_skills.py -q
```

Expected: package asset and extension command-name tests pass.

- [ ] **Step 5: Commit cleanup**

Run:

```powershell
git add .
git restore --staged docs/superpowers/specs/2026-04-29-map-scan-build-design.md docs/superpowers/plans/2026-04-29-map-scan-build-implementation.md
git commit -m "chore: remove active map-codebase references"
```

Expected: commit contains only active source/test/docs cleanup. If the current plan file should be committed, commit it separately in Task 9.

---

### Task 8: Run Full Targeted Regression and Fix Failures

**Files:**
- Modify: only files implicated by failing tests

- [ ] **Step 1: Run the core regression set**

Run:

```powershell
pytest tests/test_map_scan_build_template_guidance.py tests/test_alignment_templates.py tests/test_specify_guidance_docs.py tests/test_packaging_assets.py tests/integrations/test_cli.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py -q
```

Expected: all pass.

- [ ] **Step 2: Run hook, freshness, and learning regression**

Run:

```powershell
pytest tests/test_project_map_status.py tests/test_project_map_freshness_scripts.py tests/hooks/test_learning_hooks.py tests/contract/test_codex_team_auto_dispatch_cli.py tests/codex_team/test_tmux_smoke.py -q
```

Expected: all pass.

- [ ] **Step 3: Run broad tests if targeted suites pass**

Run:

```powershell
pytest -q
```

Expected: all pass. If full suite is too slow or fails due unrelated dirty-tree state, capture the exact failing tests and run the smallest implicated subset after patching.

- [ ] **Step 4: Fix any failures without weakening the contract**

When a failure mentions old `map-codebase` expected output, update the expected output to the new two-step flow. When a failure shows a missing generated command, verify whether `templates/commands/map-scan.md` and `templates/commands/map-build.md` are included by `IntegrationBase.list_command_templates()` before adding integration-specific exceptions.

- [ ] **Step 5: Commit regression fixes**

Run:

```powershell
git add .
git restore --staged docs/superpowers/plans/2026-04-29-map-scan-build-implementation.md
git commit -m "test: align map scan build regression coverage"
```

Expected: commit contains only regression fixes from this task.

---

### Task 9: Final Review and Plan Commit

**Files:**
- Modify: `docs/superpowers/plans/2026-04-29-map-scan-build-implementation.md`

- [ ] **Step 1: Review final diff**

Run:

```powershell
git diff --stat
git diff -- templates/commands/map-scan.md templates/commands/map-build.md src/specify_cli/integrations/codex/__init__.py src/specify_cli/__init__.py
```

Expected: diff shows the two-command workflow, Codex augmentations for both commands, and no active one-step map-codebase routing.

- [ ] **Step 2: Confirm active old references are gone**

Run:

```powershell
rg -n "map-codebase|sp-map-codebase|map_codebase" -g "!**/__pycache__/**" -g "!*.pyc" .
```

Expected: only historical design/plan references remain. Active templates, docs, source, scripts, and tests use `map-scan` and `map-build`.

- [ ] **Step 3: Commit this implementation plan**

Run:

```powershell
git add docs/superpowers/plans/2026-04-29-map-scan-build-implementation.md
git commit -m "plan: implement map scan build workflow"
```

Expected: one commit containing only this plan file.

- [ ] **Step 4: Final status check**

Run:

```powershell
git status --short
```

Expected: no uncommitted changes from this implementation. If unrelated pre-existing user changes remain, leave them untouched and mention them in the final summary.

## Self-Review Checklist

- Spec coverage: Tasks cover new command templates, scan package outputs, coverage ledger JSON, scan packets, scan/build boundaries, refusal rules, reverse coverage validation, integration generation, docs, helper scripts, learning targets, freshness metadata, and tests.
- Placeholder scan: The plan uses concrete file paths, command names, snippets, and assertions. It does not rely on unspecified implementation work.
- Type/name consistency: Command names are `map-scan` and `map-build`; skill names are `sp-map-scan` and `sp-map-build`; freshness reason is `map-build`; old `sp-map-codebase` is removed from active generated surfaces.
