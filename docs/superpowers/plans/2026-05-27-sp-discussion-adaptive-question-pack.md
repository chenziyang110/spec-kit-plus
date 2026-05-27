# sp-discussion Adaptive Question Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `sp-discussion` faster by allowing same-topic optional follow-up questions while preserving single-question safety gates.

**Architecture:** This is a template-contract change. The source of behavior is the command template, shell partial, state template, and generated integration tests.

**Tech Stack:** Markdown templates, pytest contract tests.

---

### Task 1: Update Discussion Question Contract

**Files:**
- Modify: `templates/commands/discussion.md`
- Modify: `templates/command-partials/discussion/shell.md`
- Modify: `templates/discussion-state-template.md`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_codex.py`

- [x] Add `Adaptive Question Pack` guidance to `templates/commands/discussion.md`.
- [x] Replace rigid shell wording with primary-question plus optional follow-up wording.
- [x] Add question-pack state fields to `templates/discussion-state-template.md`.
- [x] Update focused tests to assert the new contract survives template rendering.
- [x] Run the relevant pytest subset.
