# Operations

**Last Updated:** 2026-04-27
**Coverage Scope:** repository-wide runtime and operator playbooks
**Primary Evidence:** docs/local-development.md, docs/installation.md, pyproject.toml, src/specify_cli/codex_team/, extensions/agent-teams/engine/, tests/codex_team/
**Update When:** startup paths, packaging flows, runtime constraints, troubleshooting entrypoints, or recovery paths change

## Startup and Execution Paths

- Fast local dev: `python -m src.specify_cli --help` or `python src/specify_cli/__init__.py ...`
- Editable install: `uv venv` -> `uv pip install -e .` -> `specify ...`
- One-off run from source: `uvx --from . specify ...`
- Full regression: `pytest -q`

## Deployment and Runtime Topology

- Core product is a local Python CLI package distributed as a wheel.
- Generated downstream repos receive copied templates/scripts; they are not dynamically fetched at runtime when using bundled assets.
- Optional Codex runtime installs project-local state under `.specify/codex-team/` and may merge operator config into `.codex/config.toml`.
- The bundled agent-teams engine is a separate Node/Rust build surface that ships with the repo/package but is not the primary human CLI.

## Build and Packaging Playbooks

- Python wheel: `uv build`
- Editable local install: `uv pip install -e .`
- Agent-teams engine build: `npm --prefix extensions/agent-teams/engine run build`
- Offline install path is documented in `docs/installation.md`; it depends on wheel plus dependency transfer.

## Runtime Constraints

- Python 3.11+ for the core CLI.
- PowerShell 7+ is required for some Windows offline flows.
- Codex runtime currently expects a tmux-capable backend plus supporting toolchain detection (`tmux`, `node`, `npm`, `cargo`, `git`, and optionally `specify-teams-mcp`).

## Runtime and Toolchain Invariants

- `pyproject.toml` must keep `templates/`, `scripts/`, and extension engine assets in `tool.hatch.build.targets.wheel.force-include`.
- Shared scripts exist in both Bash and PowerShell variants.
- Integration inventories expect deterministic generated file sets.

## Runtime State Locations

- Repo-local atlas truth: `PROJECT-HANDBOOK.md`, `.specify/project-map/*.md`, `.specify/project-map/status.json`
- Generated project manifests: `.specify/integrations/*.manifest.json`
- Codex runtime state: `.specify/codex-team/`
- Quick/debug/generated workflow state (in downstream repos): `.planning/quick/`, `.planning/debug/`, `workflow-state.md`, `.specify/testing/`

## Observability Design

- Primary observability surface is the test suite; nearly every user-facing contract is asserted directly.
- Codex runtime adds `doctor`, `live-probe`, `watch`, `status`, and state JSON files for operational visibility.
- Hook results return structured warnings/errors rather than relying only on prose.
- Learning hooks expose workflow friction through pain scores, terminal review decisions, structured candidate payloads, and injection targets.
- Atlas freshness inspection exposes `must_refresh_topics`, `review_topics`, and changed-file reasoning.

## Failure Modes and Recovery Playbooks

- **Inventory drift**: update the owning installer/template and its inventory tests together.
- **Atlas stale or missing**: regenerate handbook/project-map docs and refresh the baseline.
- **Skipped learning closeout**: run `specify hook review-learning --command <workflow> --terminal-status <resolved|blocked>` and either capture the reusable finding or record a `none` decision with rationale.
- **Runtime backend missing**: use `specify team doctor` / `live-probe`, then repair external tools before retrying.
- **Config merge drift**: use the installer/restore path rather than hand-editing manifest-owned config files.
- **Wheel asset omission**: fix `pyproject.toml` force-include entries, then rerun `uv build` and packaging tests.

## Recovery and Resume

- Downstream repos resume workflow state from explicit files (`workflow-state.md`, quick `STATUS.md`, Codex runtime state JSON).
- Codex runtime supports `resume`, `await`, `shutdown`, and `cleanup` to recover or tear down state in order.
- Atlas refresh uses `project-map complete-refresh` after successful regeneration.

## Troubleshooting Entry Points

- CLI/import issues: `docs/local-development.md`
- Packaging/offline install issues: `docs/installation.md`
- Codex runtime failures: `tests/codex_team/` plus `src/specify_cli/codex_team/doctor.py`
- Atlas status confusion: `src/specify_cli/project_map_status.py`

## Operator Notes

- This repo is currently a dirty worktree; atlas freshness should be interpreted as documentation over the current working state, not a clean release tag.
- Because templates are product code, documentation-only review heuristics are not enough when `templates/` changes.
- The extension engine has its own build surface; Python tests alone do not prove Node/Rust packaging remains healthy.

## Known Runtime Unknowns

- Real-world external agent CLI behavior can drift from the repo's adapter assumptions between releases.
- Windows-native and tmux-adjacent runtime behavior remains a higher-risk operational area than plain Python CLI flows.
