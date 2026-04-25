# Project Handbook Navigation System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the monolithic `legacy single-file technical writeup` workflow dependency with a workflow-owned navigation system built from `PROJECT-HANDBOOK.md` and `.specify/project-map/*.md`, then wire every relevant workflow, generated skill surface, and validation path to that system.

**Architecture:** Implement this in three layers. First, lock the new contract in tests so the change is driven by failures instead of doc drift. Second, add the new template assets and recursive shared-template installation support so generated projects actually receive the handbook system. Third, rewrite workflow templates, skill mirrors, and repository-local artifacts to consume the new navigation model consistently across `sp-specify`, `sp-plan`, `sp-tasks`, `sp-implement`, `sp-fast`, `sp-quick`, and `sp-debug`.

**Tech Stack:** Python, Typer, Markdown command templates, generated `SKILL.md` mirrors, pytest

---

## File Structure

### New shared template assets

- Create: `templates/project-handbook-template.md`
  - Root navigation entrypoint copied into generated projects.
- Create: `templates/project-map/ARCHITECTURE.md`
  - Conceptual layers, abstractions, boundaries, truth ownership.
- Create: `templates/project-map/STRUCTURE.md`
  - Directory responsibilities, key file locations, shared surfaces.
- Create: `templates/project-map/CONVENTIONS.md`
  - Naming, import rules, error handling, code-style guidance.
- Create: `templates/project-map/INTEGRATIONS.md`
  - External dependencies, env/config, CI/runtime assumptions.
- Create: `templates/project-map/WORKFLOWS.md`
  - User flows, maintainer flows, handoffs, neighboring-workflow risks.
- Create: `templates/project-map/TESTING.md`
  - Test layers, smallest meaningful checks, regression-sensitive zones.
- Create: `templates/project-map/OPERATIONS.md`
  - Startup, runtime constraints, recovery, operator notes.

### Shared installation/runtime code

- Modify: `src/specify_cli/__init__.py`
  - Make `_install_shared_infra()` copy nested template directories under `.specify/templates/`.
  - Keep no-overwrite semantics and manifest tracking.
- Modify: `templates/constitution-template.md`
  - Change the technical source-of-truth rule from `legacy single-file technical writeup` to the handbook system.

### Workflow templates

- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/fast.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/debug.md`

### Repo-local mirrors and live artifacts

- Modify: `.agents/skills/sp-specify/SKILL.md`
- Modify: `.agents/skills/sp-plan/SKILL.md`
- Modify: `.agents/skills/sp-tasks/SKILL.md`
- Modify: `.agents/skills/sp-implement/SKILL.md`
- Modify: `.agents/skills/sp-fast/SKILL.md`
- Modify: `.agents/skills/sp-quick/SKILL.md`
- Modify: `.agents/skills/sp-debug/SKILL.md`
- Add: `PROJECT-HANDBOOK.md`
- Add: `.specify/templates/project-handbook-template.md`
- Add: `.specify/templates/project-map/ARCHITECTURE.md`
- Add: `.specify/templates/project-map/STRUCTURE.md`
- Add: `.specify/templates/project-map/CONVENTIONS.md`
- Add: `.specify/templates/project-map/INTEGRATIONS.md`
- Add: `.specify/templates/project-map/WORKFLOWS.md`
- Add: `.specify/templates/project-map/TESTING.md`
- Add: `.specify/templates/project-map/OPERATIONS.md`
- Modify: `.specify/templates/constitution-template.md`
- Add: `.specify/project-map/ARCHITECTURE.md`
- Add: `.specify/project-map/STRUCTURE.md`
- Add: `.specify/project-map/CONVENTIONS.md`
- Add: `.specify/project-map/INTEGRATIONS.md`
- Add: `.specify/project-map/WORKFLOWS.md`
- Add: `.specify/project-map/TESTING.md`
- Add: `.specify/project-map/OPERATIONS.md`
- Modify: historical single-file technical writeup references
- Modify: `.specify/memory/constitution.md`

### Tests

- Add: `tests/test_project_handbook_templates.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_constitution_defaults.py`
- Modify: `tests/test_fast_template_guidance.py`
- Modify: `tests/test_quick_template_guidance.py`
- Modify: `tests/test_debug_template_guidance.py`
- Modify: `tests/test_extension_skills.py`
- Modify: `tests/test_specify_guidance_docs.py`
- Modify: `tests/integrations/test_cli.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_base_skills.py`

### User-facing docs

- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Modify: `CHANGELOG.md`

---

### Task 1: Lock the handbook-system contract in tests

**Files:**
- Create: `tests/test_project_handbook_templates.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_constitution_defaults.py`
- Modify: `tests/test_fast_template_guidance.py`
- Modify: `tests/test_quick_template_guidance.py`
- Modify: `tests/test_debug_template_guidance.py`

- [ ] **Step 1: Add a dedicated template-contract test for the new navigation artifacts**

Create `tests/test_project_handbook_templates.py` with assertions like:

```python
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_project_handbook_template_exists_and_routes_to_project_map():
    content = _read("templates/project-handbook-template.md")
    assert "# Project Handbook" in content
    assert "## System Summary" in content
    assert "## Shared Surfaces" in content
    assert "## Risky Coordination Points" in content
    assert "## Topic Map" in content
    assert ".specify/project-map/ARCHITECTURE.md" in content
    assert ".specify/project-map/OPERATIONS.md" in content


def test_project_map_templates_share_metadata_contract():
    for rel_path in [
        "templates/project-map/ARCHITECTURE.md",
        "templates/project-map/STRUCTURE.md",
        "templates/project-map/CONVENTIONS.md",
        "templates/project-map/INTEGRATIONS.md",
        "templates/project-map/WORKFLOWS.md",
        "templates/project-map/TESTING.md",
        "templates/project-map/OPERATIONS.md",
    ]:
        content = _read(rel_path)
        assert "**Last Updated:**" in content
        assert "**Coverage Scope:**" in content
        assert "**Primary Evidence:**" in content
        assert "**Update When:**" in content
```

- [ ] **Step 2: Rewrite alignment-template assertions around the handbook system**

Update `tests/test_alignment_templates.py` so `specify`, `plan`, `tasks`, and `implement` stop asserting `legacy single-file technical writeup` and start asserting:

```python
assert "PROJECT-HANDBOOK.md" in content
assert ".specify/project-map/ARCHITECTURE.md" in content
assert ".specify/project-map/STRUCTURE.md" in content
assert ".specify/project-map/WORKFLOWS.md" in content
assert "Treat `PROJECT-HANDBOOK.md` as the root navigation artifact" in content
assert "Use `Topic Map` to choose the smallest relevant topical documents" in content
```

Also replace old scout expectations such as:

```python
assert "grounded in the codebase scout from `legacy single-file technical writeup`" in content
```

with new expectations such as:

```python
assert "grounded in the project handbook and touched-area topical map" in content
```

- [ ] **Step 3: Update constitution and workflow-guidance tests**

Change `tests/test_constitution_defaults.py` to assert:

```python
assert "PROJECT-HANDBOOK.md" in content
assert ".specify/project-map/" in content
assert "progressive disclosure" in content.lower()
```

Update `tests/test_fast_template_guidance.py`, `tests/test_quick_template_guidance.py`, and `tests/test_debug_template_guidance.py` to require the new read contracts:

```python
assert "read `project-handbook.md`" in content
assert "shared surfaces" in content
assert "risky coordination points" in content
```

for `fast`,

```python
assert "read `project-handbook.md`" in content
assert "topic map" in content
assert "touched-area topical files" in content
```

for `quick`, and

```python
assert "read `project-handbook.md`" in content
assert "truth ownership" in content
assert "read whichever of `architecture.md`, `workflows.md`, `integrations.md`, `testing.md`, and `operations.md` map to the failing area" in content
```

for `debug`.

- [ ] **Step 4: Run the template-contract test subset and confirm red**

Run:

```powershell
pytest tests/test_project_handbook_templates.py `
  tests/test_alignment_templates.py `
  tests/test_constitution_defaults.py `
  tests/test_fast_template_guidance.py `
  tests/test_quick_template_guidance.py `
  tests/test_debug_template_guidance.py -q
```

Expected:

- `tests/test_project_handbook_templates.py` fails because the new template files do not exist yet.
- Existing template-guidance tests fail because the repository still references `legacy single-file technical writeup`.

- [ ] **Step 5: Commit the red contract**

```bash
git add tests/test_project_handbook_templates.py tests/test_alignment_templates.py tests/test_constitution_defaults.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_debug_template_guidance.py
git commit -m "test: lock handbook navigation template contract"
```

### Task 2: Add handbook/project-map template assets and recursive shared-template installation

**Files:**
- Create: `templates/project-handbook-template.md`
- Create: `templates/project-map/ARCHITECTURE.md`
- Create: `templates/project-map/STRUCTURE.md`
- Create: `templates/project-map/CONVENTIONS.md`
- Create: `templates/project-map/INTEGRATIONS.md`
- Create: `templates/project-map/WORKFLOWS.md`
- Create: `templates/project-map/TESTING.md`
- Create: `templates/project-map/OPERATIONS.md`
- Modify: `src/specify_cli/__init__.py`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_base_skills.py`

- [ ] **Step 1: Create the root handbook template**

Add `templates/project-handbook-template.md` with this exact skeleton:

```markdown
# Project Handbook

**Last Updated:** YYYY-MM-DD
**Purpose:** Root navigation artifact for this repository.

## System Summary

[What this project is, its primary runtime shape, and its major layers.]

## How To Read This Project

- Start here for orientation.
- Use `Topic Map` to choose the next topical document.
- Fall back to live code reads only when the topical coverage is missing, stale, or too broad.

## Shared Surfaces

- [Registries, routing files, template directories, config schemas, exported contracts]

## Risky Coordination Points

- [Files or modules that can silently affect multiple workflows]

## Topic Map

- `.specify/project-map/ARCHITECTURE.md` - layers, abstractions, truth ownership
- `.specify/project-map/STRUCTURE.md` - where code lives and where to add new code
- `.specify/project-map/CONVENTIONS.md` - naming, imports, error handling, style
- `.specify/project-map/INTEGRATIONS.md` - external tools, env, runtime dependencies
- `.specify/project-map/WORKFLOWS.md` - user flows, maintainer flows, workflow risks
- `.specify/project-map/TESTING.md` - test layers and smallest meaningful checks
- `.specify/project-map/OPERATIONS.md` - startup, recovery, troubleshooting, operator notes

## Update Triggers

- [When structure, ownership, interfaces, workflows, or runtime assumptions change]

## Recent Structural Changes

- [Short rolling summary]
```

- [ ] **Step 2: Create the seven project-map templates**

Each file under `templates/project-map/` must begin with the same metadata contract:

```markdown
# Architecture

**Last Updated:** YYYY-MM-DD
**Coverage Scope:** repository-wide conceptual architecture
**Primary Evidence:** src/, templates/, tests/, README.md
**Update When:** layers, abstractions, boundaries, or truth ownership change
```

and then follow the approved section list from the design:

```markdown
## Pattern Overview
## Layers
## Core Abstractions
## Main Flows
## Truth Ownership and Boundaries
## Cross-Cutting Concerns
```

Repeat that approach for the other six topical files using the exact approved section names from the design doc.

- [ ] **Step 3: Make shared-template installation recursive**

Replace the top-level `iterdir()` copy loop in `_install_shared_infra()` with a recursive copy that preserves relative paths under `.specify/templates/`:

```python
for src_path in templates_src.rglob("*"):
    if src_path.is_dir():
        continue
    if src_path.name == "vscode-settings.json" or src_path.name.startswith("."):
        continue

    rel_path = src_path.relative_to(templates_src)
    dst = dest_templates / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        skipped_files.append(str(dst.relative_to(project_path)))
        continue

    shutil.copy2(src_path, dst)
    manifest.record_existing(dst.relative_to(project_path).as_posix())
```

This change is required so `.specify/templates/project-map/*.md` lands in initialized projects.

- [ ] **Step 4: Update base integration inventory tests to understand nested templates**

Change `_template_files()` in all three base integration test mixins to return relative POSIX paths instead of only top-level names:

```python
return sorted(
    path.relative_to(templates_dir).as_posix()
    for path in templates_dir.rglob("*")
    if path.is_file() and path.name != "vscode-settings.json"
)
```

Keep the inventory assertion shape:

```python
files.append(f".specify/templates/{name}")
```

so nested entries such as `.specify/templates/project-map/ARCHITECTURE.md` are covered automatically.

- [ ] **Step 5: Run template-installation tests and make them green**

Run:

```powershell
pytest tests/test_project_handbook_templates.py `
  tests/integrations/test_integration_base_markdown.py `
  tests/integrations/test_integration_base_toml.py `
  tests/integrations/test_integration_base_skills.py -q
```

Expected:

- handbook/project-map template tests pass
- integration inventory tests now see nested `.specify/templates/project-map/*.md` artifacts

- [ ] **Step 6: Commit the template asset and installation slice**

```bash
git add templates/project-handbook-template.md templates/project-map src/specify_cli/__init__.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py
git commit -m "feat: add project handbook templates and recursive install support"
```

### Task 3: Rewrite constitution and workflow templates to use the handbook system

**Files:**
- Modify: `templates/constitution-template.md`
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/fast.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/debug.md`

- [ ] **Step 1: Replace the constitution source-of-truth rule**

Rewrite the engineering-standard bullet in `templates/constitution-template.md` to say:

```markdown
- **Technical Source of Truth**: Maintain `PROJECT-HANDBOOK.md` as the root
  navigation artifact and `.specify/project-map/` as the topical depth layer
  for structure, ownership, interfaces, workflows, testing, integrations, and
  operations. If the navigation system is missing in an existing codebase,
  generate it before structural work and keep it in sync whenever navigation
  meaning changes.
```

- [ ] **Step 2: Replace `specify`'s brownfield scout contract**

Update `templates/commands/specify.md` so the old section:

```markdown
- Check whether `legacy single-file technical writeup` exists at the repository root.
- If it is missing, analyze the repository and create `legacy single-file technical writeup` before continuing.
```

becomes:

```markdown
- Check whether `PROJECT-HANDBOOK.md` exists at the repository root.
- Check whether `.specify/project-map/ARCHITECTURE.md`, `.specify/project-map/STRUCTURE.md`, `.specify/project-map/CONVENTIONS.md`, `.specify/project-map/INTEGRATIONS.md`, `.specify/project-map/WORKFLOWS.md`, `.specify/project-map/TESTING.md`, and `.specify/project-map/OPERATIONS.md` exist.
- If the navigation system is missing, analyze the repository and create it before continuing.
- Treat `PROJECT-HANDBOOK.md` as the root navigation artifact and use `Topic Map` to choose the smallest relevant topical documents for the touched area.
```

Also replace language such as:

```markdown
grounded in the codebase scout from `legacy single-file technical writeup`
```

with:

```markdown
grounded in the project handbook and touched-area topical map
```

- [ ] **Step 3: Update `plan`, `tasks`, and `implement` to consume the new navigation system**

Apply the same pattern to:

- `templates/commands/plan.md`
- `templates/commands/tasks.md`
- `templates/commands/implement.md`

Use exact read-contract language like:

```markdown
- Read `PROJECT-HANDBOOK.md`.
- Read the smallest relevant combination of `.specify/project-map/ARCHITECTURE.md`, `.specify/project-map/STRUCTURE.md`, `.specify/project-map/CONVENTIONS.md`, `.specify/project-map/INTEGRATIONS.md`, `.specify/project-map/WORKFLOWS.md`, `.specify/project-map/TESTING.md`, and `.specify/project-map/OPERATIONS.md`.
- If the topical coverage for the touched area is missing, stale, or too broad, inspect the minimum live files needed to replace guesswork with evidence.
```

- [ ] **Step 4: Add lightweight and touched-area read contracts for `fast` and `quick`**

Update `templates/commands/fast.md` with a new process step:

```markdown
2. **Read the routing layer**
   - Read `PROJECT-HANDBOOK.md`.
   - Use `Shared Surfaces` and `Risky Coordination Points` to decide whether the task is truly local.
   - If the requested change touches a shared surface or risky coordination point, stop and redirect to `/sp-quick`.
```

Update `templates/commands/quick.md` in `Required Context Inputs` with:

```markdown
- Read `PROJECT-HANDBOOK.md` after the constitution gate and before any broad repository analysis.
- Use `Topic Map` to choose only the touched-area topical files needed for the current quick task.
- Do not load the full topical map unless the task expands beyond its bounded quick-task scope.
```

- [ ] **Step 5: Add handbook-driven debugging reads**

Update `templates/commands/debug.md` under `Required Context Inputs`:

```markdown
- Read `PROJECT-HANDBOOK.md` before root-cause analysis so the investigation starts from the current system map.
- Read whichever of `.specify/project-map/ARCHITECTURE.md`, `.specify/project-map/WORKFLOWS.md`, `.specify/project-map/INTEGRATIONS.md`, `.specify/project-map/TESTING.md`, and `.specify/project-map/OPERATIONS.md` map to the failing area.
- Use the navigation system to identify likely truth-owning layers, adjacent workflows, and observability entry points before forming a hypothesis.
```

- [ ] **Step 6: Run the workflow-guidance test subset**

Run:

```powershell
pytest tests/test_alignment_templates.py `
  tests/test_constitution_defaults.py `
  tests/test_fast_template_guidance.py `
  tests/test_quick_template_guidance.py `
  tests/test_debug_template_guidance.py -q
```

Expected:

- all workflow and constitution template tests pass against the handbook-system contract

- [ ] **Step 7: Commit the workflow-template rewrite**

```bash
git add templates/constitution-template.md templates/commands/specify.md templates/commands/plan.md templates/commands/tasks.md templates/commands/implement.md templates/commands/fast.md templates/commands/quick.md templates/commands/debug.md
git commit -m "feat: switch workflow templates to handbook navigation system"
```

### Task 4: Update skill mirrors and generated-project assertions

**Files:**
- Modify: `.agents/skills/sp-specify/SKILL.md`
- Modify: `.agents/skills/sp-plan/SKILL.md`
- Modify: `.agents/skills/sp-tasks/SKILL.md`
- Modify: `.agents/skills/sp-implement/SKILL.md`
- Modify: `.agents/skills/sp-fast/SKILL.md`
- Modify: `.agents/skills/sp-quick/SKILL.md`
- Modify: `.agents/skills/sp-debug/SKILL.md`
- Modify: `tests/test_extension_skills.py`
- Modify: `tests/integrations/test_cli.py`
- Modify: `tests/integrations/test_integration_codex.py`

- [ ] **Step 1: Update repository skill-mirror assertions**

Change `tests/test_extension_skills.py` so skill-mirror expectations use the new language:

```python
assert "PROJECT-HANDBOOK.md" in body
assert ".specify/project-map/ARCHITECTURE.md" in body
assert ".specify/project-map/WORKFLOWS.md" in body
assert "Topic Map" in body
```

Replace old assertions such as:

```python
assert "If `legacy single-file technical writeup` is missing coverage for the touched area" in body
```

with:

```python
assert "If the topical coverage for the touched area is missing, stale, or too broad" in body
```

- [ ] **Step 2: Update generated-project integration expectations**

Modify `tests/integrations/test_cli.py` and `tests/integrations/test_integration_codex.py` to assert:

```python
assert (project / ".specify" / "templates" / "project-handbook-template.md").exists()
assert (project / ".specify" / "templates" / "project-map" / "ARCHITECTURE.md").exists()
assert (project / ".specify" / "templates" / "project-map" / "OPERATIONS.md").exists()
```

and generated skill text like:

```python
assert "project-handbook.md" in content
assert "shared surfaces" in content
assert "topic map" in content
```

- [ ] **Step 3: Regenerate or manually sync the checked-in skill mirrors**

Update the checked-in `.agents/skills/*/SKILL.md` files so their bodies mirror the new command templates. The changed lines should include exact phrases such as:

```markdown
- Read `PROJECT-HANDBOOK.md` first.
- Use `Topic Map` to choose the smallest relevant topical documents.
- Use `Shared Surfaces` and `Risky Coordination Points` to decide whether the task is truly local.
```

for `sp-fast`, `sp-quick`, and `sp-debug`, and the corresponding handbook/project-map language for `sp-specify`, `sp-plan`, `sp-tasks`, and `sp-implement`.

- [ ] **Step 4: Run the mirror and integration subset**

Run:

```powershell
pytest tests/test_extension_skills.py `
  tests/integrations/test_cli.py `
  tests/integrations/test_integration_codex.py -q
```

Expected:

- repo mirrors and generated-project skill surfaces match the new handbook-system contract

- [ ] **Step 5: Commit the skill-surface synchronization**

```bash
git add .agents/skills tests/test_extension_skills.py tests/integrations/test_cli.py tests/integrations/test_integration_codex.py
git commit -m "feat: align generated skills with handbook navigation system"
```

### Task 5: Migrate the `spec-kit-plus` repository itself to the handbook system

**Files:**
- Create: `PROJECT-HANDBOOK.md`
- Create: `.specify/templates/project-handbook-template.md`
- Create: `.specify/templates/project-map/ARCHITECTURE.md`
- Create: `.specify/templates/project-map/STRUCTURE.md`
- Create: `.specify/templates/project-map/CONVENTIONS.md`
- Create: `.specify/templates/project-map/INTEGRATIONS.md`
- Create: `.specify/templates/project-map/WORKFLOWS.md`
- Create: `.specify/templates/project-map/TESTING.md`
- Create: `.specify/templates/project-map/OPERATIONS.md`
- Modify: `.specify/templates/constitution-template.md`
- Create: `.specify/project-map/ARCHITECTURE.md`
- Create: `.specify/project-map/STRUCTURE.md`
- Create: `.specify/project-map/CONVENTIONS.md`
- Create: `.specify/project-map/INTEGRATIONS.md`
- Create: `.specify/project-map/WORKFLOWS.md`
- Create: `.specify/project-map/TESTING.md`
- Create: `.specify/project-map/OPERATIONS.md`
- Modify: historical single-file technical writeup references
- Modify: `.specify/memory/constitution.md`
- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Modify: `CHANGELOG.md`
- Modify: `tests/test_specify_guidance_docs.py`

- [ ] **Step 1: Add the live root handbook for this repository**

Create `PROJECT-HANDBOOK.md` with actual repository-specific routing content, including:

```markdown
## Shared Surfaces

- `src/specify_cli/__init__.py`
- `templates/commands/`
- `templates/`
- `src/specify_cli/integrations/`
- `.agents/skills/`
- `scripts/bash/` and `scripts/powershell/`

## Risky Coordination Points

- shared template installation in `src/specify_cli/__init__.py`
- integration base tests under `tests/integrations/`
- mirrored skill assets under `.agents/skills/`
- cross-workflow language alignment in `templates/commands/`
```

- [ ] **Step 2: Add the seven live project-map documents for `spec-kit-plus`**

Populate `.specify/project-map/*.md` with real repository content drawn from:

- `src/specify_cli/`
- `templates/`
- `tests/`
- `README.md`
- `docs/quickstart.md`

For example, `ARCHITECTURE.md` should name the CLI layer, integration layer, template/scaffold layer, orchestration/runtime layer, and verification layer. `STRUCTURE.md` should explicitly cover `src/specify_cli/`, `templates/`, `.agents/skills/`, `tests/`, and `.specify/`.

- [ ] **Step 3: Retire the historical single-file technical writeup references**

Replace any remaining long-form single-file technical writeup content with a
short note that points readers to:

- `PROJECT-HANDBOOK.md`
- `.specify/project-map/`

Do not keep parallel technical truth in any retained historical writeup.

- [ ] **Step 4: Sync repo-local template copies, constitution, and user-facing docs**

Update `.specify/templates/project-handbook-template.md`, `.specify/templates/project-map/`, `.specify/templates/constitution-template.md`, `.specify/memory/constitution.md`, `README.md`, `docs/quickstart.md`, and `CHANGELOG.md` so they describe the handbook system explicitly. Add README/quickstart language such as:

```markdown
- Generated projects now include `PROJECT-HANDBOOK.md` as the root navigation artifact.
- Deep project knowledge lives under `.specify/project-map/`.
- Any code change that alters navigation meaning must update the handbook system.
```

Update `tests/test_specify_guidance_docs.py` to assert those statements.

- [ ] **Step 5: Run repo-doc and constitution verification**

Run:

```powershell
pytest tests/test_constitution_defaults.py tests/test_specify_guidance_docs.py -q
```

Expected:

- constitution defaults and user-facing docs now teach the handbook system

- [ ] **Step 6: Commit the repository migration**

```bash
git add PROJECT-HANDBOOK.md .specify/templates/project-handbook-template.md .specify/templates/project-map .specify/templates/constitution-template.md .specify/project-map .specify/memory/constitution.md README.md docs/quickstart.md CHANGELOG.md tests/test_specify_guidance_docs.py
git commit -m "docs: migrate repo to project handbook navigation system"
```

### Task 6: Run the focused end-to-end verification sweep

**Files:**
- No new files in this task

- [ ] **Step 1: Run the focused handbook-system regression suite**

Run:

```powershell
pytest tests/test_project_handbook_templates.py `
  tests/test_alignment_templates.py `
  tests/test_constitution_defaults.py `
  tests/test_fast_template_guidance.py `
  tests/test_quick_template_guidance.py `
  tests/test_debug_template_guidance.py `
  tests/test_extension_skills.py `
  tests/test_specify_guidance_docs.py `
  tests/integrations/test_cli.py `
  tests/integrations/test_integration_codex.py `
  tests/integrations/test_integration_base_markdown.py `
  tests/integrations/test_integration_base_toml.py `
  tests/integrations/test_integration_base_skills.py -q
```

Expected:

- all handbook-system template, mirror, and integration checks pass

- [ ] **Step 2: Fix any path or inventory regressions exposed by recursive template copying**

If the suite reports missing generated files, inspect the failing relative path and make the installation logic or expected inventory list consistent. The most likely failure shapes are:

```text
Expected .specify/templates/project-map/ARCHITECTURE.md to exist
```

or

```text
inventory mismatch: .specify/templates/project-map/WORKFLOWS.md
```

Address those before widening the test scope.

- [ ] **Step 3: Run a smaller CLI smoke check after the test suite is green**

Run:

```powershell
python -m specify_cli --help
python -m specify_cli init --help
python -m specify_cli quick --help
python -m specify_cli debug --help
```

Expected:

- all commands render help successfully
- no crash from the shared-template installation changes

- [ ] **Step 4: Commit the final verification pass**

```bash
git add -A
git commit -m "test: verify handbook navigation system rollout"
```

## Spec Coverage Check

- Root navigation artifact and topical map: covered by Tasks 1 and 2.
- Recursive template installation and generated-project availability: covered by Task 2.
- Workflow read contracts for `specify`, `plan`, `tasks`, `implement`, `fast`, `quick`, and `debug`: covered by Task 3.
- Skill-mirror and generated-surface alignment: covered by Task 4.
- Repo-local migration and compatibility bridge from `legacy single-file technical writeup`: covered by Task 5.
- Validation and integration confidence: covered by Task 6.

## Placeholder Scan

- No `TODO`, `TBD`, or `implement later` placeholders were left in the tasks.
- Every step names exact files and exact commands.
- Code and text modifications are shown with concrete target snippets instead of abstract guidance.

## Type and Naming Consistency Check

- Canonical root artifact: `PROJECT-HANDBOOK.md`
- Canonical topical directory: `.specify/project-map/`
- Canonical topical files: `ARCHITECTURE.md`, `STRUCTURE.md`, `CONVENTIONS.md`, `INTEGRATIONS.md`, `WORKFLOWS.md`, `TESTING.md`, `OPERATIONS.md`
- Historical single-file technical writeup references retired from the live contract.
