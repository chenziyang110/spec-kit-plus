# Conventions

**Last Updated:** 2026-04-30
**Coverage Scope:** Naming, generated-surface, state, compatibility, and review conventions.
**Primary Evidence:** `worker-results/integrations-generated-surfaces.json`, `project-map-atlas-state.json`, `docs-planning-operations.json`.
**Update When:** Agent naming, workflow names, state files, generated output conventions, or review rules change.

## Naming and Registration Conventions

- Integration keys should match the actual CLI executable name when one exists, such as `cursor-agent` rather than `cursor`.
- Built-in integration registration lives in `src/specify_cli/integrations/__init__.py`.
- Shared generated workflow names use `sp-<command>` skill/command naming, while template stems remain plain names such as `map-scan` and `map-build`.
- Skills-based integrations install into `skills/` directories; command/workflow/prompt/rules integrations use their agent-specific directory conventions.

## Contract and Compatibility Conventions

- Preserve the `specify -> plan` mainline in user-facing workflow guidance.
- Treat `deep-research` as an optional feasibility branch, not a mandatory stage.
- Treat `map-scan -> map-build` as the required brownfield context gate when atlas coverage is missing, stale, or too broad.
- Treat `test` as a compatibility router; `test-scan` and `test-build` own actual testing-system scan/build work.
- Do not claim equal multi-agent capability across runtimes. Current execution-oriented workflows use `execution_model: subagents-first`, `dispatch_shape: one-subagent | parallel-subagents | leader-inline-fallback`, and `execution_surface: native-subagents | managed-team | leader-inline`.
- Use `managed-team` only when durable team state, explicit join-point tracking, result files, or lifecycle control are needed beyond one in-session subagent burst.
- Use `leader-inline-fallback` only after recording why delegation is unavailable, unsafe, or not packetized.

## State and Data Semantics

- Canonical project-map status lives at `.specify/project-map/index/status.json`; legacy `.specify/project-map/status.json` remains a fallback/mirror path.
- `map-state.md` and `worker-results/*.json` are runtime evidence/state files and are ignored by freshness path classification.
- Project memory lives under `.specify/memory/project-rules.md` and `.specify/memory/project-learnings.md`.
- Planning state under `.planning/STATE.md` is current planning status; historical milestone files are context, not necessarily active work.
- Codex team state lives under `.specify/teams/state/`.

## Config and Option Propagation

- `pyproject.toml` force-includes templates, scripts, passive skills, project-map/testing templates, worker prompts, and engine assets into the wheel.
- `--integration` and `--ai` are mutually exclusive in `specify init`; `--ai` resolves through the same integration registry.
- `--ai-skills` is unnecessary for skills-based integrations and has no effect for command-based integrations.
- Agent-specific argument placeholders must stay correct: Markdown generally uses `$ARGUMENTS`, TOML uses `{{args}}`, Forge uses `{{parameters}}`.

## Development Workflow and Review Conventions

- Read `PROJECT-HANDBOOK.md` and relevant project-map docs before brownfield planning/debugging/implementation.
- If atlas coverage is stale or missing, run `sp-map-scan -> sp-map-build` before continuing.
- Use `rg`/file-list-driven evidence before broad manual reads.
- Keep changes scoped; do not rewrite generated surfaces without updating integration tests.
- Run focused tests for the touched surface before broader regression.

## Generated-Surface Conventions

- `templates/commands/*.md` are canonical workflow contracts.
- `templates/command-partials/*/shell.md` provide short objective/context sections included by command templates.
- Passive skills under `templates/passive-skills/` are installed by skills-based integrations and may include support assets.
- `src/specify_cli/integrations/base.py` appends runtime project-map gates, delegation contracts, question-tool preferences, and worker result guidance to generated surfaces.

## Security and Trust Conventions

- Do not hardcode secrets; use environment variables or generated config surfaces.
- Generated file destinations must stay within the project root.
- Extension/preset manifests validate schema version, IDs, semantic versions, compatibility, and safe relative paths.
- External agent CLIs and runtime tools are untrusted dependencies from this repo's perspective; adapter assumptions need revalidation when upstream behavior changes.

## Known Convention Unknowns

- Global user installs may lag the source checkout. For development verification, prefer `PYTHONPATH=src; python -m specify_cli ...` or an editable install.
