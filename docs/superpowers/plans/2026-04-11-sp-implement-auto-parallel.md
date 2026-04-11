# sp-implement Auto-Parallel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `sp-implement` automatically choose between sequential execution, Codex native subagents, and `specify team` when parallel work is warranted.

**Architecture:** Keep the shared `implement` template agent-agnostic, but strengthen it with an explicit execution-strategy selection step. Add a Codex-only post-processing hook so generated `sp-implement` skills include the stronger `specify team` guidance without leaking that product surface to non-Codex integrations.

**Tech Stack:** Python, Typer integration layer, Markdown command templates, pytest

---

### Task 1: Lock the behavior with tests

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/integrations/test_integration_codex.py`

- [ ] Add a template regression asserting `templates/commands/implement.md` explicitly requires execution-strategy selection and mentions sequential/native subagent/team routing in generic terms.
- [ ] Add a Codex integration regression asserting generated `.agents/skills/sp-implement/SKILL.md` includes Codex-only routing to `specify team`.
- [ ] Run the focused pytest targets and confirm the new assertions fail before implementation.

### Task 2: Strengthen the shared implement template

**Files:**
- Modify: `templates/commands/implement.md`

- [ ] Add an explicit strategy-selection step after task parsing and before execution.
- [ ] Require the agent to evaluate sequential execution vs native subagents vs agent-specific coordinated runtime.
- [ ] Keep the wording generic so non-Codex integrations do not advertise `specify team`.

### Task 3: Add Codex-only sp-implement post-processing

**Files:**
- Modify: `src/specify_cli/integrations/codex/__init__.py`

- [ ] Override Codex skill setup to append a Codex-only execution-strategy addendum to `sp-implement/SKILL.md`.
- [ ] Scope the addendum to `sp-implement` only.
- [ ] Preserve existing team-skill behavior and generated asset contracts.

### Task 4: Verify the end state

**Files:**
- Modify: `docs/superpowers/plans/2026-04-11-sp-implement-auto-parallel.md`

- [ ] Run the focused pytest suite for template and Codex integration coverage.
- [ ] Review the generated assertions and implementation for non-Codex leakage.
- [ ] Record verification outcome here if behavior or scope changed during implementation.

## Verification Notes

- `pytest tests/test_alignment_templates.py -q`
- `pytest tests/integrations/test_integration_codex.py -q`
- `pytest tests/test_alignment_templates.py tests/integrations/test_integration_codex.py -q`

Result: all targeted checks passed after the Codex post-processing path was updated to rewrite `sp-implement/SKILL.md` through the manifest-aware helper.
