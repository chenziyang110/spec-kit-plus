# Project Map Retirement Design

**Date:** 2026-05-14  
**Status:** Draft for review  
**Scope:** Generated workflow guidance, map-scan/map-build runtime outputs, project cognition freshness commands, launcher-backed helper commands, initialization assets, documentation, and regression tests  
**Primary goal:** Retire `.specify/project-map/**` from all new runtime workflows while keeping `specify project-map ...` as a temporary legacy CLI alias for existing projects.

## Summary

`project-cognition` is now the canonical brownfield runtime. It owns freshness,
query readiness, task-local bundles, and the SQLite graph store. `project-map`
was useful as a human-readable atlas and migration bridge, but new workflows
still read, write, validate, and install `.specify/project-map/**` in places
where the system already says `project-cognition` is the truth layer.

This creates two concrete failures:

- generated workflows can still instruct agents to read stale project-map
  artifacts instead of querying project cognition
- generated workflow instructions can still call bare `specify ...` commands,
  which can hit an old executable on `PATH` instead of the launcher that
  initialized the project

The approved direction is:

- new `sp-*` workflows must not read `.specify/project-map/**`
- `sp-map-scan`, `sp-map-build`, and `sp-map-update` must not require or publish
  `.specify/project-map/**` outputs
- map workbench state moves under `.specify/project-cognition/workbench/**`
- `project-cognition` becomes the preferred public command namespace for
  freshness, dirty-state, refresh, query, and update operations
- `project-map` remains only as a legacy CLI alias during the migration window
- generated helper command text uses `{{specify-subcmd:...}}` so downstream
  projects use their trusted project launcher instead of a potentially stale
  global `specify`

## Problem

The repository currently has a split-brain runtime contract.

On the new side:

- `.specify/project-cognition/status.json` is documented as the lightweight
  freshness entrypoint
- `.specify/project-cognition/project-cognition.db` is the canonical graph store
- `specify project-cognition query` returns task-local bundles and
  `minimal_live_reads`
- ordinary brownfield workflows are supposed to consume the query result before
  broad source reads

On the old side:

- `map-scan` still lists `.specify/project-map/map-state.md`,
  `.specify/project-map/coverage-ledger.json`, scan packets, and quick-nav
  exports as outputs
- `map-build` still reads `.specify/project-map/coverage-ledger.json` and
  `.specify/project-map/scan-packets/`
- refresh finalizers still call or document `specify project-map
  complete-refresh`
- CLI refresh helpers currently validate that compatibility/export project-map
  files exist before recording a fresh baseline
- generated AGENTS blocks, passive skills, README/handbook text, and tests still
  preserve project-map as a runtime or support read surface
- several generated instructions hard-code `specify project-cognition ...`
  instead of the existing launcher-backed `{{specify-subcmd:...}}` placeholder

The result is confusing for agents and users: the system says the graph-native
cognition runtime is canonical, but the workflows still maintain and consult
the older atlas surface.

## Goals

- Remove `.specify/project-map/**` from every new generated workflow runtime
  read path.
- Stop `map-scan`, `map-build`, and `map-update` from producing or requiring
  `.specify/project-map/**` artifacts.
- Move all map workbench state to `.specify/project-cognition/workbench/**`.
- Make `project-cognition` the preferred command namespace in generated
  guidance and docs.
- Preserve `specify project-map ...` only as a temporary compatibility alias for
  existing projects and user scripts.
- Ensure refresh finalizers operate from cognition readiness, not from the
  existence of compatibility/export files.
- Route generated helper commands through `{{specify-subcmd:...}}` so they
  honor `.specify/config.json` `specify_launcher` when present.
- Add tests that prevent project-map from reappearing as a new runtime surface.

## Non-Goals

- Do not remove the `specify project-map ...` CLI alias in this change.
- Do not delete old historical design docs that mention project-map.
- Do not make agents read raw SQLite tables directly.
- Do not preserve `.specify/project-map/**` as an optional generated export in
  new projects.
- Do not require existing downstream projects to delete their old
  `.specify/project-map/**` directories before upgrading.
- Do not introduce a second launcher mechanism; reuse the existing
  `{{specify-subcmd:...}}` renderer and project launcher binding.

## Decision

Use a staged retirement:

1. **New runtime path:** project cognition only.
2. **Legacy command path:** `project-map` CLI aliases remain available but are
   not generated, recommended, or required by new workflows.
3. **Compatibility assets:** `.specify/project-map/**` is no longer installed or
   validated as a required runtime surface for new projects.
4. **Launcher safety:** every generated first-party helper command uses
   `{{specify-subcmd:...}}` in source templates and renders to a launcher-backed
   command in generated projects.

This avoids a hard break for existing projects while making the new product
surface coherent.

## Target Runtime Layout

Canonical runtime state:

- `.specify/project-cognition/status.json`
- `.specify/project-cognition/project-cognition.db`
- `.specify/project-cognition/evidence/**`
- `.specify/project-cognition/provisional/nodes.json`
- `.specify/project-cognition/provisional/edges.json`
- `.specify/project-cognition/provisional/observations.json`
- `.specify/project-cognition/coverage.json`

Map workflow workbench state:

- `.specify/project-cognition/workbench/map-state.md`
- `.specify/project-cognition/workbench/coverage-ledger.md`
- `.specify/project-cognition/workbench/coverage-ledger.json`
- `.specify/project-cognition/workbench/scan-packets/<lane-id>.md`
- `.specify/project-cognition/workbench/worker-results/<packet-id>.json`
- `.specify/project-cognition/workbench/repository-universe.json`
- `.specify/project-cognition/workbench/capability-ledger.json`
- `.specify/project-cognition/workbench/control-ledger.json`

Retired from new runtime:

- `.specify/project-map/status.json`
- `.specify/project-map/index/status.json`
- `.specify/project-map/map-state.md`
- `.specify/project-map/coverage-ledger.json`
- `.specify/project-map/scan-packets/**`
- `.specify/project-map/worker-results/**`
- `.specify/project-map/root/**`
- `.specify/project-map/modules/**`
- `.specify/project-map/QUICK-NAV.md`

Existing downstream projects may keep these retired paths on disk. New workflow
guidance must not require or consult them.

## Command Surface

Preferred commands for new workflows:

- `{{specify-subcmd:project-cognition status --format json}}`
- `{{specify-subcmd:project-cognition check --format json}}`
- `{{specify-subcmd:project-cognition query --intent <intent> --query "$ARGUMENTS" --format json}}`
- `{{specify-subcmd:project-cognition update --paths <path> --reason "<reason>" --format json}}`
- `{{specify-subcmd:project-cognition complete-refresh --format json}}`
- `{{specify-subcmd:project-cognition mark-dirty --reason "<reason>" --format json}}`

Legacy commands:

- `specify project-map status`
- `specify project-map check`
- `specify project-map mark-dirty`
- `specify project-map clear-dirty`
- `specify project-map record-refresh`
- `specify project-map complete-refresh`
- `specify project-map refresh-topics`

The legacy commands call the same cognition implementation. They should remain
available for older projects, but new generated content should not mention them
except in migration notes or compatibility docs.

## Workflow Changes

### sp-map-scan

`sp-map-scan` collects project-internal evidence and provisional graph inputs.
It must write scan workbench state under
`.specify/project-cognition/workbench/**`, not `.specify/project-map/**`.

Its completion checks should prove:

- cognition status exists or is initialized
- evidence and provisional graph inputs exist
- workbench ledgers exist under project cognition
- no final runtime truth has been published yet
- no `.specify/project-map/**` output is required

### sp-map-build

`sp-map-build` validates scan inputs and publishes the query-backed SQLite
runtime. It must read from:

- `.specify/project-cognition/evidence/**`
- `.specify/project-cognition/provisional/**`
- `.specify/project-cognition/coverage.json`
- `.specify/project-cognition/workbench/**`

It must output:

- `.specify/project-cognition/status.json`
- `.specify/project-cognition/project-cognition.db`
- accepted worker result evidence under the cognition workbench

It must finalize through:

- `{{specify-subcmd:project-cognition complete-refresh --format json}}`

It must not require `PROJECT-HANDBOOK.md`, `DEBUG-HANDBOOK.md`,
`BUILD-HANDBOOK.md`, or `.specify/project-map/**` before recording a fresh
cognition baseline.

### sp-map-update

`sp-map-update` performs localized refreshes against an existing cognition
baseline. It should use the project cognition query/update helpers and write any
refresh workbench state under `.specify/project-cognition/workbench/**`.

Its finalizer should use `project-cognition complete-refresh` when readiness is
ready, or `project-cognition mark-dirty` when refresh cannot complete.

### Other sp-* workflows

All ordinary workflows should consume:

- `.specify/project-cognition/status.json`
- `project-cognition query` results
- returned `minimal_live_reads`

They should not read `.specify/project-map/**` for routine routing, planning,
debugging, implementation, explanation, testing, or closeout.

## Generated Asset Changes

New generated projects should not install `.specify/project-map/**` as a
required runtime asset.

Surfaces to update:

- `templates/commands/**`
- `templates/command-partials/**`
- `templates/passive-skills/**`
- `templates/worker-prompts/**`
- `templates/project-handbook-template.md`
- `scripts/bash/update-agent-context.sh`
- `scripts/powershell/update-agent-context.ps1`
- integration addenda in `src/specify_cli/integrations/**`
- init asset copy rules in `src/specify_cli/__init__.py` and integration base
  installers
- packaging force-includes in `pyproject.toml`
- README, quickstart, upgrade, and project handbook text

`templates/project-map/**` can remain in the repository during the first
retirement phase only if it is no longer installed into new projects and no
test treats it as required. A later cleanup can delete the dormant template
tree once downstream compatibility concerns are resolved.

## Launcher Requirement

Every generated first-party command invocation must use the existing launcher
placeholder in source templates:

```text
{{specify-subcmd:project-cognition query --intent implement --query "$ARGUMENTS" --format json}}
```

Generated files must not retain `{{specify-subcmd:...}}`; they should contain
the rendered command. When `.specify/config.json` has `specify_launcher`, the
rendered command must target that launcher. When no launcher is configured, the
existing fallback behavior remains.

This specifically fixes the failure mode where a downstream workflow runs a
stale global `specify` that does not expose `project-cognition`.

## CLI Behavior

`project-cognition` commands become the canonical public surface.

`complete-refresh`, `record-refresh`, and `refresh-topics` must validate
cognition runtime readiness and status metadata. They must not fail only because
compatibility/export project-map files are absent.

`project-map` remains registered as a legacy Typer subcommand group. In text
mode it may show a deprecation or compatibility note. In JSON mode, preserve
machine-readable compatibility unless a non-breaking `warnings` field is
already part of the relevant payload shape.

The code can keep internal helper names during the first pass if renaming them
would create unnecessary churn, but user-facing help text, docs, and generated
guidance should say `project cognition`, not `project map`.

## Migration

Existing projects:

- may keep `.specify/project-map/**`
- may keep using `specify project-map ...` during the compatibility window
- should run `specify integration repair` after upgrading so generated
  workflows stop relying on project-map reads and bare helper commands

New projects:

- should initialize `.specify/project-cognition/**`
- should not initialize `.specify/project-map/**` as required runtime state
- should generate launcher-backed `project-cognition` helper instructions

Repair behavior:

- should refresh managed workflow files and passive skills to remove project-map
  runtime reads
- should preserve user-owned files and unrelated custom state
- should not delete old `.specify/project-map/**` directories automatically

## Testing Strategy

Add or update tests in these families:

- CLI contract tests for `project-cognition` status/check/dirty/refresh commands
  without `.specify/project-map/**`
- CLI compatibility tests proving `project-map` alias commands still call the
  same implementation
- map-scan/map-build template tests proving outputs and required inputs use
  `.specify/project-cognition/workbench/**`
- generated integration tests proving new projects do not require
  `.specify/project-map/**`
- alignment tests proving ordinary `sp-*` templates do not instruct runtime
  reads from `.specify/project-map/**`
- launcher rendering tests proving generated cognition helper commands do not
  hard-code bare `specify ...` when a project launcher is present
- documentation tests proving README/handbook text describes project-map only as
  legacy compatibility, not as a runtime requirement

The regression rule should be strict for generated runtime surfaces:

- no required read of `.specify/project-map/**`
- no required output under `.specify/project-map/**`
- no bare generated `specify project-cognition ...` helper instruction when the
  template can use `{{specify-subcmd:...}}`

## Risks

- Some existing tests currently assert project-map assets are installed. Those
  assertions need to be replaced with cognition runtime assertions.
- Existing downstream projects may still have old instructions. This is handled
  through `integration repair`, not automatic deletion.
- Removing project-map outputs from `map-scan` and `map-build` may expose stale
  references in passive skills or managed AGENTS blocks. The implementation
  must sweep generated assets, docs, scripts, and tests in one pass.
- Changing JSON payloads for legacy alias commands could break scripts. The
  first pass should prefer stable payloads and deprecation in text/help surfaces.

## Acceptance Criteria

- A newly initialized project can run cognition freshness and query commands
  without any `.specify/project-map/**` directory.
- `sp-map-scan` and `sp-map-build` templates no longer require, read, or output
  `.specify/project-map/**`.
- Ordinary generated `sp-*` workflows no longer route agents to project-map
  runtime reads.
- Generated helper commands use launcher-backed `project-cognition` command
  shapes.
- `specify project-cognition complete-refresh` does not require project-map
  compatibility/export files.
- `specify project-map complete-refresh` remains available as a legacy alias.
- Tests prevent new project-map runtime dependencies from being reintroduced.

