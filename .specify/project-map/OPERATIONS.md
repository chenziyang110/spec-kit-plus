# Operations

**Last Updated:** 2026-04-19
**Coverage Scope:** repository-wide runtime and operator playbooks
**Primary Evidence:** scripts/, src/, docs, troubleshooting paths in tests
**Update When:** startup flows, runtime constraints, or recovery paths change

## Startup and Execution Paths

- Developer setup: install via `uv` and run `specify --help` / `specify check`.
- Local development path: editable install from repository, then invoke CLI
  commands directly.
- Generated-project path: `specify init <project> --ai <agent>` installs
  templates, scripts, and integration-specific command assets.

## Runtime Constraints

- Python 3.11+, `uv`, and `git` are baseline prerequisites.
- CLI-based integrations need corresponding tools on `PATH` unless using
  `--ignore-agent-tools`.
- Codex team runtime requires a tmux-capable backend and stays Codex-scoped.

## Recovery and Resume

- Re-run focused pytest subsets when guidance/template contracts fail.
- For Codex runtime sessions, use `specify team resume`, `status`, `await`,
  `shutdown`, and `cleanup` as lifecycle operations.
- Keep generated artifact and mirror drift in sync by updating templates, docs,
  and tests in the same change.

## Troubleshooting Entry Points

- Template/install regressions: `tests/integrations/test_integration_base_*`.
- Guidance regressions: `tests/test_specify_guidance_docs.py`,
  `tests/test_alignment_templates.py`, `tests/test_constitution_defaults.py`.
- Integration-specific failures: targeted `tests/integrations/test_integration_*.py`.

## Operator Notes

- Treat `PROJECT-HANDBOOK.md` as root navigation and `.specify/project-map/` as
  topical depth before broad codebase scans.
- Update handbook/topic docs when changes alter navigation meaning, ownership,
  workflow boundaries, or operational assumptions.
