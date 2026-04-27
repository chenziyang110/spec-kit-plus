# Conventions

**Last Updated:** 2026-04-27
**Coverage Scope:** repository-wide coding and documentation conventions
**Primary Evidence:** src/, templates/, tests/, README.md, docs/quickstart.md, pyproject.toml
**Update When:** naming, import, error-handling, documentation, workflow, or testing conventions change

## Naming Patterns

- Integration keys match actual CLI/binary names where possible (`cursor-agent`, `kiro-cli`, `qodercli`), and aliases are explicit (`AI_ASSISTANT_ALIASES`).
- Generated workflow surfaces use `sp.<name>` for Markdown/TOML commands and `sp-<name>` skill directories for skills-based integrations.
- Topic files and atlas filenames are uppercase and canonical: `ARCHITECTURE.md`, `WORKFLOWS.md`, `TESTING.md`, etc.
- Tests mirror the owned subsystem closely (`tests/integrations/test_integration_<name>.py`, `tests/codex_team/test_*.py`, `tests/hooks/test_*.py`).

## Formatting and Linting

- Python code is UTF-8 and generally normalized to `\n` before writes in shared integration utilities.
- There is no repo-wide lint command encoded as a hard gate in `pyproject.toml`; tests are the main enforced quality surface.
- Markdown templates are treated as structured product assets and are validated by string-contract tests rather than style-only tooling.

## Imports and Exports

- `src/specify_cli/__init__.py` is the assembled product surface; narrow modules feed into it rather than re-registering commands elsewhere.
- Integration registration happens centrally via `_register_builtins()` in `src/specify_cli/integrations/__init__.py`.
- Public helper modules often use explicit `__all__` lists in runtime-oriented packages (`codex_team`, installer helpers).

## Error Handling

- CLI-facing errors use Rich console output plus `typer.Exit`.
- Validation helpers prefer explicit exceptions with actionable messages (`ValueError`, custom hook errors, runtime environment errors).
- Test expectations emphasize contract clarity: missing assets, invalid config, and unsupported tool surfaces should fail with direct guidance.

## Contract and Compatibility Conventions

- Template wording is a product contract. If a phrase is asserted in tests, changing it requires updating the associated tests intentionally.
- Agent-specific folder names and command subdirs are compatibility-sensitive; they must stay aligned with `AGENT_CONFIG`, registrar config, and inventory tests.
- Runtime-facing terminology is canonicalized (`single-lane`, `native-multi-agent`, `sidecar-runtime`, `reported_status`, `WorkerTaskPacket`).

## State and Data Semantics

- `.specify/project-map/status.json` is the canonical atlas freshness baseline.
- Generated project workflow state lives in explicit files like `workflow-state.md`, quick-task `STATUS.md`, `implement` closeout artifacts, and Codex runtime JSON state.
- Delegated execution packets carry rules, references, and validation obligations; workers are not meant to rediscover them ad hoc from chat memory.

## Config and Option Propagation

- `pyproject.toml` is the Python package/build truth and also controls wheel force-included assets.
- Per-integration config and question-tool behavior lives in each integration module, not in shared docs.
- Generated Codex runtime config merges into `.codex/config.toml`; `.specify/config.json` holds JSON notify wiring.

## Comments and Docs

- README and quickstart are treated as product contract surfaces and are tested directly.
- `docs/superpowers/specs/` and `docs/superpowers/plans/` capture decision history and rollout reasoning.
- Atlas docs should distinguish verified facts from inferred areas rather than smoothing over uncertainty.

## Development Workflow and Review Conventions

- This repo relies heavily on focused regression tests before claiming changes are done.
- When a shared template or installer changes, update the owning tests in the same pass.
- Keep integration-specific behavior inside the integration module instead of multiplying branches in unrelated code.

## Testing Conventions

- Use `pytest` for the Python repo and treat contract tests as first-class product tests.
- Split tests by subsystem to preserve blame and failure locality.
- Prefer focused regression additions over broad, generic smoke tests when pinning a behavior change.
