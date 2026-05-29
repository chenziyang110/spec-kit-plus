# Greenfield Project Cognition Design

**Date:** 2026-05-30
**Status:** Draft for user review
**Owner:** Codex

## Summary

Freshly initialized Spec Kit Plus projects should not be forced through
`sp-map-scan -> sp-map-build` before they have project code to scan.

Today, `specify init` installs or pins the `project-cognition` runtime and
creates `.specify/project-cognition/`, but a newly initialized empty project
still has no query-ready project cognition database. When generated workflows
encounter the missing baseline, they can recommend the full brownfield
scan/build path even though there is no business source, test surface, API,
runtime, or UI to map.

This design adds an init-time greenfield starter baseline. `specify init` should
call a new runtime command, `project-cognition init-empty`, when the initialized
project has no business-code evidence. The command creates both
`.specify/project-cognition/status.json` and a real
`.specify/project-cognition/project-cognition.db`. The database has the full
SQLite schema, a valid active generation, ready metadata, and an explicit
`baseline_kind=greenfield_empty` marker. It does not fabricate graph rows or
insert `.specify/**` paths into the project graph.

The result is a legitimate query-ready empty baseline:

- greenfield requirement and planning workflows can continue immediately
- `lexicon` and `query` can open the runtime and return honest empty-candidate
  payloads
- brownfield projects with existing code still route to full baseline
  construction when they need it
- later source-changing workflows can update project cognition through the
  existing inline update path as real project files appear

## Problem

The current runtime model has one missing-baseline path:

```text
missing project cognition baseline -> run map-scan, then map-build
```

That is correct for a brownfield repository with existing code and no usable
graph-native cognition baseline. It is wrong for a freshly initialized project
that only contains Spec Kit scaffolding, agent command files, passive skills,
memory templates, and documentation.

For a greenfield project, there is no useful scan work to delegate:

- no business source paths exist yet
- no tests exist yet
- no runtime entry points exist yet
- no project-specific module ownership exists yet
- `.specify/**` and generated agent assets must not enter graph evidence
- scan/build would produce either empty artifacts or invalid graph facts

The user experience failure is direct: while doing requirements work on a newly
created project, the workflow may ask the user to run map scan/build for an
empty codebase. That blocks progress with maintenance work that cannot add
meaningful project cognition.

There is also a technical gap. Merely changing `status.json` is not sufficient,
because project cognition commands need a real SQLite runtime. If
`project-cognition.db` is missing, runtime agreement and query commands
correctly treat the baseline as broken or absent. A greenfield fix must create
the database, not only a status file.

## Goals

- Make freshly initialized empty projects query-ready without running
  `sp-map-scan -> sp-map-build`.
- Create a real `project-cognition.db` during initialization for greenfield
  projects.
- Explicitly distinguish `greenfield_empty` from brownfield missing baseline.
- Keep `.specify/**`, generated workflow assets, and generic scaffold docs out
  of graph-facing path indexes and evidence rows.
- Allow zero nodes, zero evidence rows, and zero path index rows only for a
  verified `greenfield_empty` active generation.
- Preserve strict scan/build requirements for brownfield projects.
- Keep `specify init` best-effort: failure to initialize greenfield cognition
  warns but does not fail project initialization.
- Let downstream workflows continue through `specify -> plan` for empty
  projects while still using live requirement artifacts as the proof layer.

## Non-Goals

- Do not weaken brownfield `sp-map-scan -> sp-map-build` acceptance rules.
- Do not use fake nodes, fake evidence, or fake `path_index` rows to satisfy
  existing validation gates.
- Do not add `.specify/**` paths to graph evidence, path indexes, symbol
  indexes, entrypoint indexes, or test indexes.
- Do not make `greenfield_empty` claim that project source has been scanned.
- Do not require a full graph rebuild when the first generated source files are
  created.
- Do not turn `project-cognition init-empty` into a general-purpose scanner.

## Approved Direction

Add a runtime-owned empty baseline command and call it automatically from
`specify init` for empty greenfield projects.

```text
specify init
  |
  v
install or resolve project-cognition runtime
  |
  v
project-cognition init-empty --format json
  |
  v
.specify/project-cognition/status.json
.specify/project-cognition/project-cognition.db
```

The starter runtime is query-ready, but its identity is explicit:

```json
{
  "status": "ok",
  "freshness": "fresh",
  "readiness": "query_ready",
  "recommended_next_action": "use_project_cognition",
  "graph_ready": true,
  "baseline_kind": "greenfield_empty"
}
```

The database also records `baseline_kind=greenfield_empty` in metadata and uses
an active generation whose `kind` is `greenfield_empty`.

## State Model

Add `baseline_kind` to the project cognition status and database metadata.

Initial supported values:

- `brownfield_full`: a normal scan/build or fully reconstructed baseline
- `greenfield_empty`: a starter baseline for a project with no business code

The field may be omitted for older baselines. When omitted, the runtime should
treat a query-ready baseline with normal graph rows as `brownfield_full` for
compatibility. New writes should include the field.

Normal scan/build publication must write `brownfield_full` explicitly. This
includes the `build-from-scan` writer in `tools/project-cognition/internal/build/**`,
which currently publishes ready status/metadata and imports generation kind
`full`. The implementation should either keep the generation kind as the
existing compact value and add `baseline_kind=brownfield_full` in metadata and
status, or rename the generation kind only if all validators and tests are
updated in the same pass.

`greenfield_empty` means:

- the runtime is structurally query-ready
- the database schema and metadata are valid
- the active generation intentionally has no project source facts yet
- empty node, evidence, and path-index tables are acceptable
- the baseline is not proof that business code was scanned

`greenfield_empty` does not mean:

- scan/build has run
- source ownership is known
- generated workflow assets are project behavior
- future source changes can skip project cognition closeout

## Runtime Command Contract

Add a new command:

```text
project-cognition init-empty --format json
```

The command creates a query-ready empty runtime for the current project root.

### Inputs

The command reads:

- current working directory as the project root
- existing `.specify/project-cognition/status.json`, if present
- existing `.specify/project-cognition/project-cognition.db`, if present
- project file inventory only to decide whether empty initialization is safe

It must not read project source deeply. It is an initializer, not a scanner.

### Default Safety

By default, `init-empty` must not overwrite an existing project cognition
baseline.

If either `status.json` or `project-cognition.db` already exists:

- if they agree and are already query-ready, return `status=ok` with
  `already_initialized=true`
- if they are split-brain or blocked, return `status=blocked` with a recovery
  action
- do not delete or replace existing files unless a future explicit `--force`
  mode is added and invoked by a human

`specify init` must not pass `--force`.

### Greenfield Eligibility

`init-empty` should only create a greenfield baseline when the project has no
business-code evidence.

The implementation should ignore known scaffold and runtime support surfaces
when making this decision:

- `.specify/**`
- generated agent command or skill directories
- generated workflow templates and passive skills
- `.git/**`
- generic project documents such as `AGENTS.md`, `README.md`, and init options
- project cognition runtime files

The first implementation can keep the greenfield detector conservative. If it
is unsure whether a repository has real code, it should decline to initialize
the empty baseline and let brownfield rules apply. False negatives are annoying
but safe. False positives can hide a real brownfield missing-baseline problem.

### Outputs

The command writes:

- `.specify/project-cognition/status.json`
- `.specify/project-cognition/project-cognition.db`

It may create `.specify/project-cognition/` if missing.

It should not write scan workbench artifacts such as:

- `workbench/repository-universe.json`
- `workbench/coverage-ledger.json`
- `evidence/`
- `provisional/nodes.json`
- `provisional/edges.json`
- `coverage.json`

Those are scan/build artifacts, and a greenfield starter baseline is not a scan
package.

### JSON Result

Successful output should include stable fields:

```json
{
  "status": "ok",
  "readiness": "query_ready",
  "baseline_kind": "greenfield_empty",
  "active_generation_id": "GEN-greenfield-...",
  "status_path": ".specify/project-cognition/status.json",
  "graph_store_path": ".specify/project-cognition/project-cognition.db",
  "already_initialized": false,
  "errors": [],
  "warnings": []
}
```

Blocked output should include:

- `status=blocked`
- `readiness=blocked`
- `recommended_next_action`
- `recovery_action` when available
- `errors`
- `warnings`
- `status_path`
- `graph_store_path`

## Database Contract

`init-empty` must create a real SQLite runtime database.

Required DB state:

- all required tables from `store.RequiredTables()` exist
- all required columns from `store.RequiredTableColumns()` exist
- `metadata.runtime_format` is `project-cognition-go`
- `metadata.runtime_schema` matches the runtime schema
- `metadata.schema_version` matches the store schema
- `metadata.active_generation_id` names the active greenfield generation
- `metadata.graph_store_path` is `.specify/project-cognition/project-cognition.db`
- `metadata.graph_ready` is `true`
- `metadata.baseline_state` is `fresh`
- `metadata.query_contract_version` is `1`
- `metadata.update_contract_version` is `1`
- `metadata.baseline_kind` is `greenfield_empty`
- `generations` has exactly one active starter generation or a compatible
  active starter generation created by an earlier `init-empty`
- the active generation has `kind=greenfield_empty`
- graph-facing evidence, node, edge, path, symbol, entrypoint, and test indexes
  are empty

The active generation id should be stable enough for one runtime session and
clearly identifiable, for example:

```text
GEN-greenfield-20260530T120000.000000000Z
```

The command should use existing store initialization code where possible so
schema creation stays centralized.

## Validation And Runtime Agreement

Current build validation assumes a brownfield graph and fails when an active
generation has no nodes, no evidence rows, or no path index rows. That remains
correct for `brownfield_full`. It must become a controlled exception for
`greenfield_empty`.

Update validation so:

- missing DB still fails
- missing status still fails when either side exists
- DB/status active generation mismatch still fails
- missing required tables or columns still fails
- missing runtime metadata still fails
- `baseline_kind=greenfield_empty` allows zero nodes
- `baseline_kind=greenfield_empty` allows zero evidence rows
- `baseline_kind=greenfield_empty` allows zero path index rows
- zero rows are allowed only when status metadata, DB metadata, and active
  generation kind agree on `greenfield_empty`

Runtime agreement should verify `baseline_kind` when present. If status says
`greenfield_empty` but the DB active generation or metadata does not, the
runtime should block with a recovery action rather than guessing.

Sparse path-index gates should not run for greenfield-empty generations because
there is no repository universe or index-required path set. This must be an
explicit branch, not a side effect of missing workbench files.

## Query And Lexicon Behavior

`project-cognition lexicon` should work against a `greenfield_empty` baseline.

Expected behavior:

- return `readiness=query_ready`
- return `recommended_next_action=use_project_cognition`
- return `baseline_kind=greenfield_empty`
- return an empty `concept_candidates` list
- set `unmapped_intent=true` when the user's query asks for project concepts
  that cannot exist yet
- include missing coverage such as `greenfield_empty_no_project_code`
- do not recommend `map-scan -> map-build`

`project-cognition query` should also work.

Expected behavior:

- return `readiness=query_ready` unless the input selected unknown concepts or
  the baseline agreement is blocked
- return empty affected graph nodes
- return `minimal_live_reads` from user and workflow artifacts, not from graph
  source paths
- explain that the project has no code baseline yet
- avoid presenting graph evidence as source-code proof

Minimal live reads for greenfield requirement and planning workflows can include
only artifacts that are valid for the active workflow, such as:

- the current feature spec or draft state when it exists
- `.specify/memory/constitution.md`
- `.specify/memory/project-rules.md`
- the user's current request
- AGENTS-level guidance loaded by the agent

The runtime should not force these paths into the graph. They are workflow
inputs, not project source evidence.

## `specify init` Behavior

During initialization, after the project cognition binary is resolved and
launcher config is written, `specify init` should best-effort run:

```text
project-cognition init-empty --format json
```

The command should be invoked through the resolved or pinned binary, not by
assuming `project-cognition` is on `PATH`.

If `init-empty` succeeds:

- leave the generated `status.json` and DB in place
- record the project cognition step as available
- optionally include a concise detail such as `greenfield baseline`

If `init-empty` declines because the project appears non-empty:

- do not treat this as an initialization failure
- preserve brownfield missing-baseline behavior
- surface a short warning or status detail when helpful

If `init-empty` fails because the runtime is unavailable or incompatible:

- keep current best-effort behavior
- warn that project cognition could not be initialized
- do not fail `specify init`

`project_cognition_runtime.REQUIRED_COMMANDS` should include `init-empty` so
older cached runtime binaries are refreshed or rebuilt from bundled source.

## Workflow Guidance

Shared project cognition guidance must stop treating all missing or empty graph
states as the same.

The new routing model:

- `greenfield_empty`: continue with requirements, planning, or implementation
  using live workflow artifacts; do not recommend scan/build solely because the
  graph has no paths
- brownfield `missing`: continue or block according to the workflow's existing
  policy, and recommend `map-scan -> map-build` only when a first usable
  baseline is required
- stale or weak existing baseline: prefer `map-update` for ordinary localized
  maintenance
- structurally unusable baseline: recommend `map-scan -> map-build`

Generated workflow wording should be updated wherever it says or implies that a
missing project cognition baseline always means `sp-map-scan -> sp-map-build`.
The distinction must live in shared partials and passive skills so every
integration inherits it.

## Interaction With Future Source Changes

The greenfield baseline is a starting point. It should not remain empty forever
after source files are created.

When a source-changing `sp-*` workflow creates or modifies project code,
existing mutation closeout rules still apply:

1. Append closeout evidence to the active delta session when one exists.
2. Run inline `project-cognition update` with changed paths and affected
   surfaces.
3. Use `project-cognition mark-dirty` only when inline update cannot complete.

For a greenfield-empty baseline, the first successful update may either:

- keep `baseline_kind=greenfield_empty` but record changed paths as update
  evidence until enough graph structure exists, or
- promote the baseline kind to a non-empty mode such as `brownfield_incremental`
  or `brownfield_full` if the update writes real graph rows and validation can
  prove them

The first implementation should keep promotion conservative. It only needs to
ensure that empty initialization does not block the first requirements and
planning flows. Promotion rules can be refined during implementation if the
existing update path already has enough evidence to classify the baseline.

## Required Surface Changes

Runtime changes:

- `tools/project-cognition/internal/cli/cli.go`
- `tools/project-cognition/internal/build/**`
- `tools/project-cognition/internal/runtime/status.go`
- `tools/project-cognition/internal/runtimegate/agreement.go`
- `tools/project-cognition/internal/store/**`
- `tools/project-cognition/internal/validation/build.go`
- `tools/project-cognition/internal/buildgate/sparse.go`
- `tools/project-cognition/internal/query/lexicon.go`
- `tools/project-cognition/internal/query/query.go`

Python init changes:

- `src/specify_cli/project_cognition_runtime.py`
- `src/specify_cli/__init__.py`
- launcher/config helpers only if needed to invoke the pinned binary cleanly

Template and documentation changes:

- `src/specify_cli/integrations/base.py`
- `src/specify_cli/integrations/cursor_agent/__init__.py`
- `templates/command-partials/common/context-loading-gradient.md`
- `templates/command-partials/common/planning-context-loading-gradient.md`
- `templates/command-partials/common/navigation-check.md`
- `templates/command-partials/common/senior-consequence-analysis-gate.md`
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- workflow templates that directly mention map-scan/build routing
- `README.md`
- `PROJECT-HANDBOOK.md`
- `docs/quickstart.md`
- `docs/installation.md`
- `templates/project-handbook-template.md` if generated project guidance is
  affected

`src/specify_cli/integrations/base.py` is a first-class generated-output
surface because it appends project cognition advisory gate text after template
processing. Updating only shared Markdown templates would leave generated
commands or skills able to reintroduce the old first/missing-baseline
scan/build wording.

`src/specify_cli/integrations/cursor_agent/__init__.py` has its own
Cursor-specific project cognition addendum outside `base.py`. It must be
updated or explicitly routed through the shared wording so Cursor-generated
skills do not preserve unconditional first/missing-baseline scan/build
guidance.

`docs/quickstart.md` and `docs/installation.md` are user-facing setup surfaces.
They should either describe the init-time greenfield baseline or explicitly
stand down if the implementation proves their existing project-cognition setup
guidance remains accurate without edits.

Tests:

- Go runtime and CLI tests under `tools/project-cognition/internal/**`
- Python init tests that exercise project cognition bootstrap
- template alignment tests that assert greenfield guidance is present
- generated integration tests where command output text is asserted

## Testing Strategy

Add Go tests for:

- `project-cognition init-empty --format json` creates `status.json` and
  `project-cognition.db`
- the DB contains every required table and column
- DB metadata includes `baseline_kind=greenfield_empty`
- status includes `baseline_kind=greenfield_empty`
- active generation kind is `greenfield_empty`
- runtimegate agreement passes for the empty baseline
- `validate-build` passes for `greenfield_empty` with zero nodes, zero evidence,
  and zero path-index rows
- `validate-build` still fails for zero nodes or path-index rows when
  `baseline_kind` is not `greenfield_empty`
- status/DB baseline kind mismatch blocks agreement
- `lexicon` returns query-ready empty candidates without recommending
  map-scan/build
- `query` returns query-ready empty graph results and minimal live-read guidance
- `init-empty` does not overwrite an existing baseline
- `init-empty` declines or blocks safely when a non-empty project is detected
- `build-from-scan` writes `baseline_kind=brownfield_full` in status and DB
  metadata for normal scan/build baselines
- brownfield generation kind and `baseline_kind` agreement are either preserved
  as `kind=full` plus `baseline_kind=brownfield_full` or migrated together with
  validators and tests

Add Python tests for:

- `specify init` invokes `init-empty` when the binary supports it
- cached runtimes missing `init-empty` are refreshed or rebuilt through
  `REQUIRED_COMMANDS`
- `specify init` warning behavior when `init-empty` fails
- init remains successful when project cognition bootstrap is unavailable

Add template/docs tests for:

- greenfield-empty guidance does not route to scan/build
- brownfield missing-baseline guidance still routes to scan/build when a full
  first baseline is needed
- generated integration addenda from `src/specify_cli/integrations/base.py`
  include the `greenfield_empty` branch and do not reintroduce unconditional
  scan/build guidance
- Cursor's integration-specific addendum and
  `tests/integrations/test_integration_cursor_agent.py` assert the same
  `greenfield_empty` routing branch as the shared integration addenda
- passive skills and shared partials use the same routing language
- generated integrations inherit the updated guidance
- quickstart and installation docs either mention the greenfield bootstrap or
  are explicitly covered by a no-change assertion

## Acceptance Criteria

- A freshly initialized empty project has both project cognition status and DB
  files.
- `project-cognition status --format json` reports a query-ready
  `greenfield_empty` baseline.
- `project-cognition validate-build --format json` accepts the starter runtime
  only because it is explicitly greenfield-empty.
- `project-cognition lexicon` and `project-cognition query` run without asking
  for map-scan/build on a greenfield-empty project.
- Brownfield repositories with existing business code are not silently marked as
  greenfield-empty by `specify init`.
- Existing brownfield scan/build validation remains strict.
- Shared workflow guidance teaches: greenfield-empty can proceed; brownfield
  missing or unusable baselines use map-scan/build only when a full baseline is
  actually needed.
- `specify init` remains best-effort if project cognition runtime bootstrap
  fails.

## Rollout Plan

1. Add `BaselineKind` to runtime status and DB metadata handling.
2. Add store helper logic to create a greenfield-empty generation and publish
   ready metadata.
3. Add `project-cognition init-empty`.
4. Update runtime agreement and build validation for the controlled zero-row
   greenfield exception.
5. Update lexicon and query payloads for greenfield-empty baselines.
6. Make `specify init` invoke `init-empty` through the resolved runtime binary.
7. Update shared workflow guidance, passive skills, README, and handbook.
8. Add Go runtime tests, Python init tests, and template alignment tests.
9. Run focused verification for project cognition runtime and init surfaces.

## Open Decisions

- Whether the first update after source generation should immediately promote
  `baseline_kind` away from `greenfield_empty`, or wait until a later
  map-update/build path proves enough graph coverage.
- How broad the first greenfield eligibility detector should be. The safe
  default is conservative detection that declines when unsure.
- Whether to expose a user-facing `--force` mode for `init-empty` in the first
  implementation. `specify init` should not use it even if it exists.
