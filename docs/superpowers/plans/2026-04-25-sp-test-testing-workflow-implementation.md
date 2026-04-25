# sp-test Testing Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new shared `sp-test` workflow that bootstraps or refreshes project-wide unit testing systems, vendors multi-language testing skills into bundled passive skills, and makes later Spec Kit Plus workflows consume a durable testing contract.

**Architecture:** Extend the existing shared template system instead of adding a new runtime surface. First add the new testing workflow/template assets and their tests. Then vendor the language testing passive skills. Next wire the project-level testing contract into `plan`, `tasks`, `implement`, and `debug`. Finish by tightening packaging coverage and validating wheel/install behavior.

**Tech Stack:** Python, Typer CLI, Markdown/TOML/skills integrations, passive bundled skills, pytest

---

## File Structure

- Add: `templates/commands/test.md`
- Add: `templates/command-partials/test/shell.md`
- Add: `templates/testing/testing-contract-template.md`
- Add: `templates/testing/testing-playbook-template.md`
- Add: `templates/testing/testing-state-template.md`
- Add: `templates/testing/coverage-baseline-template.json`
- Modify: `src/specify_cli/__init__.py`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `pyproject.toml`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/debug.md`
- Modify: `templates/tasks-template.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-project-learning/SKILL.md`
- Add/Modify: `templates/passive-skills/*-testing/SKILL.md`
- Add: `tests/test_testing_workflow_guidance.py`
- Modify: `tests/test_extension_skills.py`
- Modify: `tests/test_passive_skill_installation.py`
- Modify: `tests/test_passive_skill_guidance.py`
- Modify: `tests/test_packaging_assets.py`
- Modify: `tests/integrations/test_cli.py`

---

## Execution Order

1. Lock the new `sp-test` surface in tests first.
2. Add shared template assets and user-visible command descriptions.
3. Vendor the multi-language testing passive skills.
4. Wire testing-contract consumption into `plan`, `tasks`, `implement`, and `debug`.
5. Verify packaging and installation paths so `uvx` / wheel builds can resolve the new assets.

---

## Validation Target

The implementation is complete when:

- `sp-test` is generated for supported integrations
- bundled passive testing skills are installed for skills-based integrations
- `plan`, `tasks`, `implement`, and `debug` all reference `.specify/testing/TESTING_CONTRACT.md`
- task generation no longer frames tests as globally optional when a testing contract exists
- packaging tests cover the new template assets
- targeted repository tests pass
