# Testing

**Last Updated:** 2026-04-19
**Coverage Scope:** repository-wide verification and regression strategy
**Primary Evidence:** tests/, CI config, workflow templates, docs
**Update When:** test layering, minimum checks, or regression-sensitive areas change

## Test Layers

- Unit/behavior tests for CLI and helper modules.
- Contract tests for templates, docs wording, and generated artifact invariants.
- Integration tests validating `specify init` output and integration-specific
  behavior.
- Runtime-focused tests under `tests/codex_team/` and related workflow areas.

## Key Test Directories

- `tests/integrations/` for generated project/integration contracts.
- `tests/` top-level guidance/template tests (for example
  `test_alignment_templates.py`, `test_specify_guidance_docs.py`).
- `tests/codex_team/`, `tests/orchestration/`, and `tests/debug*` for runtime
  and operational behavior.

## Smallest Meaningful Checks

- Docs/navigation updates: run `test_specify_guidance_docs.py` and related
  constitution/template tests.
- Template/navigation asset updates: run `test_project_handbook_templates.py`
  plus integration-base inventory tests.
- Integration behavior changes: run targeted `tests/integrations/test_integration_<agent>.py`.

## Regression-Sensitive Areas

- `src/specify_cli/__init__.py` installation and registration logic.
- `templates/commands/` guidance language and generated mirror expectations.
- `.agents/skills/` and docs alignment with templates.
- Integration inventory expectations for nested template assets.

## When To Expand Verification

- Expand from focused tests to broader suite for cross-cutting edits in
  `src/specify_cli/`, template install behavior, or command semantics.
- Include multi-integration tests when changing shared integration base behavior.
