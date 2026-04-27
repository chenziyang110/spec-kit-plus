# Claude Native Hook Installation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add project-local Claude Code native hook installation that reuses the shared `specify hook` engine.

**Architecture:** Install thin Claude hook assets into `.claude/hooks/`, merge managed hook registrations into `.claude/settings.json`, and keep workflow truth inside `src/specify_cli/hooks/`. Reuse manifest tracking so uninstall remains ownership-safe.

**Tech Stack:** Python, Typer CLI, JSON settings merge logic, pytest

---

### Task 1: Add Claude integration tests for hook asset installation

**Files:**
- Modify: `tests/integrations/test_integration_claude.py`

- [ ] **Step 1: Write the failing test**

Add a test that calls `ClaudeIntegration.setup(...)` and asserts `.claude/hooks/`
exists with managed hook files plus `.claude/settings.json` exists.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integrations/test_integration_claude.py -k hook -q`
Expected: FAIL because hooks/settings are not created yet.

- [ ] **Step 3: Write minimal implementation**

Implement Claude hook asset install and settings generation.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/integrations/test_integration_claude.py -k hook -q`
Expected: PASS

### Task 2: Add Claude settings merge safety tests

**Files:**
- Modify: `tests/integrations/test_integration_claude.py`

- [ ] **Step 1: Write the failing test**

Add tests that:
- preserve unrelated user settings
- merge managed hooks without duplication
- skip destructive overwrite on invalid JSON

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integrations/test_integration_claude.py -k settings -q`
Expected: FAIL because merge logic is missing.

- [ ] **Step 3: Write minimal implementation**

Add a Claude-specific settings merge helper and register managed hooks.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/integrations/test_integration_claude.py -k settings -q`
Expected: PASS

### Task 3: Add Claude hook adapter assets

**Files:**
- Create: `src/specify_cli/integrations/claude/hooks/README.md`
- Create: `src/specify_cli/integrations/claude/hooks/claude-hook-dispatch.py`
- Modify: `src/specify_cli/integrations/claude/__init__.py`

- [ ] **Step 1: Write the failing test**

Add tests that assert installed hook scripts are recorded in the manifest and
their commands point at the installed `.claude/hooks/` location.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integrations/test_integration_claude.py -k dispatch -q`
Expected: FAIL because adapter assets are not installed or referenced.

- [ ] **Step 3: Write minimal implementation**

Install one shared dispatch script and route managed hook registrations through
that script with per-event arguments.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/integrations/test_integration_claude.py -k dispatch -q`
Expected: PASS

### Task 4: Update documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/quickstart.md`

- [ ] **Step 1: Write the failing documentation expectation**

Add or update a test only if a doc contract already exists; otherwise proceed
with direct doc updates.

- [ ] **Step 2: Write minimal documentation**

Document that Claude installs native hook assets into `.claude/hooks/` and
merges project-local `.claude/settings.json`, plus explain that shared workflow
truth still lives behind `specify hook ...`.

- [ ] **Step 3: Verify the docs render and read consistently**

Run: `rg -n "Claude.*hook|\\.claude/hooks|settings.json" README.md docs/quickstart.md`
Expected: Matches in both docs.

### Task 5: Final verification

**Files:**
- Modify: review all changed files

- [ ] **Step 1: Run targeted Claude integration tests**

Run: `python -m pytest tests/integrations/test_integration_claude.py -q`
Expected: PASS

- [ ] **Step 2: Run shared hook CLI verification**

Run: `python -m pytest tests/hooks/test_hook_engine.py tests/contract/test_hook_cli_surface.py -q`
Expected: PASS

- [ ] **Step 3: Review diff**

Run: `git diff --stat`
Expected: Claude integration, tests, and docs only.
