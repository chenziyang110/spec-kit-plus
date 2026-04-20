# Conventions

**Last Updated:** 2026-04-20
**Coverage Scope:** repository-wide coding and documentation conventions
**Primary Evidence:** src/, templates/, tests/, linting/config files
**Update When:** naming, import, error-handling, documentation, or testing conventions change

## Naming Patterns

- Use actual CLI executable names for integration keys (for example
  `cursor-agent`, `kiro-cli`, `qodercli`) to avoid mapping shims.
- Keep command/template names aligned with workflow names (`specify`, `plan`,
  `tasks`, `implement`, `fast`, `quick`, `debug`, `map-codebase`).
- Use uppercase topical filenames in project-map docs (`ARCHITECTURE.md`,
  `STRUCTURE.md`, etc.) as stable navigation keys.

## Formatting and Linting

- Python style follows project tooling in `pyproject.toml` and CI.
- Markdown docs should keep concise, contract-oriented wording and avoid
  duplicate source-of-truth blocks.
- Template and mirror wording should preserve exact phrases used by tests.

## Imports and Exports

- Favor explicit imports in integration modules and central registration in
  registry/init surfaces.
- Keep runtime-specific logic separated in submodules rather than bloating
  `__init__.py`.

## Error Handling

- CLI errors should be actionable and explicit, especially for missing tools,
  unsupported integrations, and runtime constraints.
- Avoid silent fallback behavior when user requested a specific path/tool.

## Comments and Docs

- Keep user-facing docs aligned across `README.md`, `docs/quickstart.md`, and
  workflow templates.
- Use `PROJECT-HANDBOOK.md` + `.specify/project-map/` for navigation truth.
- Do not use `项目技术文档.md` as a technical source of truth. Migrate any
  still-useful structure into `PROJECT-HANDBOOK.md` + `.specify/project-map/`
  and refresh those artifacts through `sp-map-codebase` when needed.

## Testing Conventions

- Add or update smallest relevant tests with behavior/template changes.
- For guidance text changes, update associated guidance-doc tests.
- For integration/template inventory changes, validate with
  `tests/integrations/` suites.
