# Project Learning Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a passive project learning layer so `sp-specify`, `sp-plan`, `sp-implement`, `sp-debug`, `sp-fast`, and `sp-quick` all consume shared project memory and can passively accumulate candidate learnings over time.

**Architecture:** Implement this in five slices. First, lock initialization and helper-surface expectations in tests. Second, add shared learning file initialization plus a small runtime helper module and low-level CLI helper surface. Third, update command templates so the six major workflows read the shared learning layer at start and record passive candidate behavior at completion. Fourth, update skill-generation and packaging surfaces so generated agent skills include the new learning behavior. Fifth, run focused regression tests and tighten any drift.

**Tech Stack:** Python, Typer, Markdown command templates, pytest

---

## File Structure

- Create: `src/specify_cli/learnings.py`
  - Shared helper functions for initializing, locating, and summarizing project learning files.
- Modify: `src/specify_cli/__init__.py`
  - Initialize shared learning files during `specify init`.
  - Add a low-level Typer helper surface for learning file bootstrap/status.
  - Update skill descriptions if needed for generated command metadata.
- Modify: `pyproject.toml`
  - Ensure any new template files are bundled into the wheel/core pack.
- Create: `templates/project-rules-template.md`
  - Seed stable project rule memory.
- Create: `templates/project-learnings-template.md`
  - Seed stable shared learning memory.
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/debug.md`
- Modify: `templates/commands/fast.md`
- Modify: `templates/commands/quick.md`
  - Add shared learning layer read contract and passive candidate/promotion guidance.
- Modify: `tests/test_constitution_defaults.py`
  - Cover initialization of new memory files.
- Modify: `tests/test_alignment_templates.py`
  - Assert the shared learning read/write language in relevant templates.
- Modify: `tests/test_extension_skills.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/integrations/test_cli.py`
  - Verify generated skills include the new learning-layer contract.

---

### Task 1: Lock the learning-layer contract in tests

**Files:**
- Modify: `tests/test_constitution_defaults.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_extension_skills.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/integrations/test_cli.py`

- [ ] Add failing tests asserting that new projects initialize `.specify/memory/project-rules.md` and `.specify/memory/project-learnings.md` without overwriting existing files.
- [ ] Add failing template assertions requiring the six major command templates to read `constitution.md`, `project-rules.md`, and `project-learnings.md` before command-local context.
- [ ] Add failing generated-skill assertions proving the same guidance survives skill generation for Claude and Codex.
- [ ] Run the focused red suite and confirm failures are caused by missing learning-layer support rather than unrelated regressions.

### Task 2: Add shared learning initialization and helper module

**Files:**
- Create: `src/specify_cli/learnings.py`
- Modify: `src/specify_cli/__init__.py`
- Create: `templates/project-rules-template.md`
- Create: `templates/project-learnings-template.md`
- Modify: `pyproject.toml`
- Modify: `tests/test_constitution_defaults.py`

- [ ] Implement a shared helper module that knows the canonical paths for stable and runtime learning files and can ensure missing files exist.
- [ ] Add init-time bootstrap so `specify init` seeds stable memory files next to the constitution while preserving user-edited existing files.
- [ ] Add a low-level CLI helper surface for passive workflows to bootstrap/report learning file paths without exposing a new `sp-` workflow.
- [ ] Bundle the new templates into both source-checkout and wheel/core-pack installs.
- [ ] Re-run the initialization tests and get them green.

### Task 3: Wire passive learning guidance into workflow templates

**Files:**
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/debug.md`
- Modify: `templates/commands/fast.md`
- Modify: `templates/commands/quick.md`
- Modify: `tests/test_alignment_templates.py`

- [ ] Add a shared-start contract to each template: ensure learning files exist, read the three stable memory files in order, and review any command-relevant candidate learnings before deeper local context.
- [ ] Add a shared-end contract to each template: record new candidate learnings passively and only ask for confirmation on highest-signal items.
- [ ] Keep command roles differentiated:
  - `specify/plan` focus on workflow gaps, preferences, constraints
  - `implement/debug` focus on pitfalls, recovery paths, constraints
  - `fast/quick` stay conservative producers
- [ ] Re-run template guidance tests and fix wording drift until green.

### Task 4: Preserve the learning layer through generated skills and init surfaces

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Modify: `tests/test_extension_skills.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/integrations/test_cli.py`

- [ ] Ensure generated skills for supported integrations inherit the updated command template bodies and metadata cleanly.
- [ ] Verify init output and built-in skill generation still expose the expected command surface, with no `sp-learnings` user workflow added.
- [ ] Make sure any low-level learning helper stays out of the standard “start here” workflow output.
- [ ] Re-run the generated-skill and CLI tests and get them green.

### Task 5: Verify the full passive learning slice

**Files:**
- Modify only if verification exposes drift

- [ ] Run the focused regression suite covering initialization, templates, generated skills, and CLI surfaces.
- [ ] Inspect the diff for accidental scope creep, especially any constitution auto-edit behavior or new visible `sp-` workflow surface.
- [ ] If needed, run one end-to-end `specify init` smoke check in a temp directory and confirm the new memory files and template assets land in the expected locations.
