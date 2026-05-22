# Project Cognition Go Runtime Hard Switch Design

## Summary

Extract the `project-cognition` runtime/helper layer from Python into a standalone Go executable while keeping the `sp-map-scan`, `sp-map-build`, and `sp-map-update` workflow prompts semantically unchanged.

The Go executable becomes the only project cognition runtime. `spec-kit-plus` remains responsible for workflow template generation, installation assets, and release packaging, but it no longer implements the project cognition runtime commands in Python.

## Goals

- Ship `project-cognition` as a compiled Go artifact, including Windows `.exe` release output.
- Keep the Go source in this repository as a long-term monorepo module while publishing it as an independent artifact.
- Preserve `sp-map-scan`, `sp-map-build`, and `sp-map-update` prompt semantics.
- Render `{{specify-subcmd:project-cognition ...}}` to direct `project-cognition ...` invocations.
- Replace all existing Python `project-cognition` runtime/helper subcommands with Go implementations.
- Use a new runtime storage format instead of preserving Python-era status or SQLite schema compatibility.
- Remove `specify project-cognition ...` and `specify project-map ...` from the runtime execution path.

## Non-Goals

- Do not migrate existing Python-era `.specify/project-cognition/status.json` or SQLite databases.
- Do not keep `specify project-map ...` as a compatibility alias.
- Do not keep a Python forwarding wrapper for `specify project-cognition ...`.
- Do not rewrite the `sp-map-*` workflow prompts into a fully programmatic scanner or builder.
- Do not split the Go runtime into a separate repository in the first implementation.

## Architecture Boundary

`project-cognition` becomes a standalone Go CLI:

```text
project-cognition <subcommand> [options]
```

The source should live in this repository as an independent Go module under `tools/project-cognition/`. This matches the existing `tools/spec-lint/` release-tool pattern while keeping the runtime source clearly separated from the Python package.

`spec-kit-plus` owns:

- workflow templates and generated agent assets
- placeholder rendering for `{{specify-subcmd:...}}`
- install and release packaging
- documentation that teaches the generated workflow

The Go runtime owns:

- `.specify/project-cognition/` runtime state
- status and readiness calculation
- scan/build validation gates
- SQLite or other query runtime schema
- query, lexicon, update, refresh, discovery, and read helper behavior
- machine-readable JSON output for workflow automation

## Command Contract

The first Go version must cover the current Python `project-cognition` command family rather than leaving dual implementations.

The Go CLI must preserve workflow-dependent options even though the runtime
storage format is a hard switch. Removing these options would require prompt and
script rewrites beyond the intended rendering change.

Required commands and options:

```text
project-cognition status --format json
project-cognition check --format json
project-cognition mark-dirty [REASON] --reason <reason> --origin-command <command> --origin-feature-dir <path> --origin-lane-id <id> --packet-file <path> --format json
project-cognition clear-dirty --format json
project-cognition record-refresh --reason <reason> --format json
project-cognition complete-refresh --format json
project-cognition refresh-topics <topic>... --reason <reason> --format json

project-cognition validate-scan --format json
project-cognition validate-build --format json
project-cognition publish-runtime-metadata --format json
project-cognition update --changed-paths <path> --scope <path> --reason <reason> --format json

project-cognition lexicon --intent <intent> --query <text> --limit <n> --format json
project-cognition query --intent <intent> --query <text> --expanded-query <text> --paths <path> --query-plan <json> --query-plan-file <path> --format json
project-cognition discover --root <path> --format json
project-cognition read --project <path> --slice <name> --include-graph <name> --format json
project-cognition doctor --format json
project-cognition rebuild
```

`update` must support repeated `--changed-paths` and repeated `--scope` as
aliases for changed-path input. If neither is supplied, it must derive the
changed paths from git diff/status using the current runtime baseline metadata.
Supporting a singular `--changed-path` alias is allowed, but not required by the
current workflow contract.

`query` must support both inline `--query-plan` JSON and `--query-plan-file`.
For parity with the current workflow, `--query-plan @path/to/file.json` may also
be accepted as file input. The query plan payload must accept `raw_query`,
`expanded_queries`, `paths`, `path_hints`, `selected_concepts`,
`rejected_concepts`, `selection_reason`, and `reason`.

`mark-dirty` must preserve origin metadata because downstream resume and
preflight behavior use it to distinguish a broad dirty baseline from a
lane-scoped fallback. `--packet-file` must derive dirty scope paths from the
validated worker packet when available.

All workflow-facing commands must support `--format json`. Human-readable output may exist, but JSON is the contract for generated workflows and tests.

The JSON schema can change with the new runtime, but the first implementation must preserve the key workflow fields that prompts and gates depend on:

- `status`
- `readiness`
- `freshness`
- `recommended_next_action`
- `errors`
- `warnings`
- `minimal_live_reads`
- `changed_paths`
- `ignored_paths`
- `status_path`
- `graph_store_path` or its new-schema equivalent

## Namespace Decisions

`project-cognition` is the only Go runtime namespace.

Current Python cross-project helpers under `specify cognition discover` and
`specify cognition read` move into the Go executable as:

```text
project-cognition discover --root <path> --format json
project-cognition read --project <path> --slice <name> --include-graph <name> --format json
```

The implementation must update docs, templates, scripts, and tests that still
teach `cognition discover` or `cognition read`. Those helpers are runtime
support because they validate and read project cognition artifacts from
reference projects; they must not remain as active Python support commands.

`project-map` remains removed. There is no `project-cognition project-map` alias
and no `specify project-map ...` runtime compatibility path.

## Template Rendering

Prompt source files may continue to contain:

```text
{{specify-subcmd:project-cognition validate-build --format json}}
```

Generated command assets must render that as:

```text
project-cognition validate-build --format json
```

This rendering change applies only to `project-cognition` invocations. Other `{{specify-subcmd:...}}` placeholders keep the existing behavior unless the implementation plan discovers another explicit dependency.

The `sp-map-scan`, `sp-map-build`, and `sp-map-update` prompt text should not be semantically rewritten as part of this extraction. Any wording edits should be limited to command names, install requirements, and breaking-change documentation.

## Storage Strategy

The directory remains:

```text
.specify/project-cognition/
```

The contents become Go-runtime-owned. The Go runtime defines a new `status.json`, runtime marker, DB schema, and metadata contract. It does not need to preserve the current Python-era shape.

The hard storage switch applies to runtime-owned truth files:

- `.specify/project-cognition/status.json`
- `.specify/project-cognition/project-cognition.db`
- runtime marker and schema metadata
- query/update helper readiness metadata

The hard storage switch does not remove the prompt-owned scan/build workbench
artifact contract. Because `sp-map-scan`, `sp-map-build`, and `sp-map-update`
prompt semantics stay unchanged, these paths remain stable workflow artifacts
that the Go validation commands must understand:

- `.specify/project-cognition/evidence/`
- `.specify/project-cognition/provisional/nodes.json`
- `.specify/project-cognition/provisional/edges.json`
- `.specify/project-cognition/provisional/observations.json`
- `.specify/project-cognition/coverage.json`
- `.specify/project-cognition/workbench/map-scan.md`
- `.specify/project-cognition/workbench/coverage-ledger.md`
- `.specify/project-cognition/workbench/coverage-ledger.json`
- `.specify/project-cognition/workbench/scan-packets/`
- `.specify/project-cognition/workbench/map-state.md`
- `.specify/project-cognition/workbench/repository-universe.json`
- `.specify/project-cognition/workbench/capability-ledger.json`
- `.specify/project-cognition/workbench/control-ledger.json`
- `.specify/project-cognition/workbench/worker-results/`

The Go runtime may define new fields inside those workbench artifacts only when
the `sp-map-*` prompts and validation tests are updated in the same change.

Hard switch rules:

- If `.specify/project-cognition/` is missing, commands either initialize the new runtime state where appropriate or return a missing-baseline result.
- If `.specify/project-cognition/` exists but lacks the Go runtime marker or uses the old Python-era format, commands fail with an explicit unsupported-runtime error.
- No automatic migration is provided.
- No read-only compatibility query is provided for old SQLite databases.
- Recovery is a fresh baseline through `sp-map-scan -> sp-map-build` after the old runtime directory is removed or archived.

Legacy `.specify/project-map/**` artifacts are historical only. The Go runtime must not use them as truth, fallback state, or compatibility inputs.

## Spec Kit CLI Changes

Python runtime responsibilities to remove or replace:

- `project_cognition_app` subcommand implementations in `src/specify_cli/__init__.py`
- `project_map_app` legacy runtime alias in `src/specify_cli/__init__.py`
- Python runtime helpers under `src/specify_cli/cognition/**`
- runtime-truth responsibility in `src/specify_cli/project_cognition_status.py`
- compatibility runtime responsibility in `src/specify_cli/project_map_status.py`

Some Python modules may remain temporarily only if they support unrelated generated-template or install behavior, but they must not remain as active project cognition runtime implementations.

Generated docs and tests must stop teaching `specify project-cognition ...` and `specify project-map ...` as runtime commands.

## Release And Install

Release packaging must build and include the Go artifact. At minimum, Windows `.exe` is required because the requested distribution target is a compiled executable. The implementation plan should decide whether to ship all supported platform binaries in the same release pass.

Generated projects must have a documented requirement that `project-cognition`
is on `PATH` before `sp-map-*` workflows use project cognition runtime
commands. Generated helper scripts that currently call the persisted Specify
launcher and append `project-cognition` must be retargeted to invoke the Go
binary directly.

Launcher rule:

- Prefer `PROJECT_COGNITION_BIN` when set.
- Otherwise invoke `project-cognition` from `PATH`.
- Do not call `specify project-cognition ...`.
- Do not read `.specify/config.json` `specify_launcher.argv` for project cognition runtime commands.
- Fail with a clear install error when the binary cannot be found.

This applies to `project-cognition-freshness.sh`, `project-cognition-freshness.ps1`,
and any legacy freshness scripts that still shell out through `specify
project-cognition`.

## Workflow JSON Contract Appendix

The Go runtime may evolve internal schemas, but these workflow-facing JSON
payload shapes are part of the first release contract.

### Shared Error Shape

Any command that receives Python-era runtime state must return JSON with:

- `status`: `blocked` or `error`
- `readiness`: `unsupported_runtime`
- `error_code`: `unsupported_legacy_runtime`
- `recommended_next_action`: `run_map_scan_build`
- `errors`: non-empty list explaining that the old runtime format is not supported
- `status_path`: `.specify/project-cognition/status.json` when known

### Status, Check, Doctor

Must return:

- `status`
- `freshness`
- `readiness`
- `recommended_next_action`
- `status_path`
- `graph_store_path` or the new equivalent
- `dirty`
- `dirty_reasons`
- `dirty_origin_command`
- `dirty_origin_feature_dir`
- `dirty_origin_lane_id`
- `dirty_scope_paths`
- `stale_paths`
- `stale_reasons`
- `last_refresh_reason`
- `last_refresh_basis`
- `last_refresh_changed_files_basis`
- runtime format and schema version fields

### Dirty And Refresh Commands

`mark-dirty`, `clear-dirty`, `record-refresh`, `complete-refresh`, and
`refresh-topics` return the same status/check shape after applying the state
transition. `mark-dirty` must echo preserved origin metadata and any scope paths
derived from `--packet-file`.

### Validate Scan

Must return:

- `status`: `ok` or `blocked`
- `gate`: `scan_acceptance`
- `readiness`: `scan_ready` or `blocked`
- `errors`
- `warnings`
- `checked_paths`
- `details`

### Validate Build

Must return:

- `status`: `ok` or `blocked`
- `gate`: `build_acceptance`
- `readiness`: `query_ready` or `blocked`
- `errors`
- `warnings`
- `checked_paths`
- `details`, including active runtime generation/schema metadata and query smoke-test diagnostics

### Publish Runtime Metadata

Must return:

- `status`
- `metadata`
- `status_path`
- `graph_store_path` or the new equivalent
- `errors`
- `warnings`

### Update

Must return:

- `readiness`
- `recommended_next_action`
- `update_id`
- `changed_paths`
- `ignored_paths`
- `affected_nodes`
- `missing_coverage`
- `adopted_paths`
- `review_paths`
- `unadoptable_paths`
- `known_unknowns`
- `minimal_live_reads`
- `path_adoption`

### Lexicon

Must return:

- `readiness`
- `recommended_next_action`
- `intent`
- `query`
- `terms`
- `available_terms`
- `concept_candidates`
- `query_planning_contract`

Each `concept_candidates` item should include enough information for an agent to
build a query plan: `concept_id`, label or title, target type, aliases or
matched terms, query examples when available, evidence ids when available, and
a disambiguation hint when available.

### Query

Must return:

- `baseline_health`
- `query_coverage`
- `workflow_requirement`
- `path_adoption`
- `readiness`
- `recommended_next_action`
- `intent`
- `query`
- `query_plan`
- `selected_concepts`
- `rejected_concepts`
- `selection_reason`
- `capability_candidates`
- `symptom_candidates`
- `affected_nodes`
- `minimal_live_reads`
- `missing_coverage`
- `route_pack`
- `subgraph`

`route_pack` must include `items`, `routes`, `minimal_live_reads`, and
`why_these_reads` or equivalent explanatory fields. `subgraph` must include the
accepted node, edge, claim, and conflict slices needed by downstream workflows.

### Discover

Must return:

- `projects`
- per-project `root`
- per-project `status_path`
- per-project `graph_store_path` or equivalent
- per-project `reference_readiness`
- per-project `freshness`
- per-project `graph_ready`
- per-project blockers or warnings

### Read

Must return:

- `admission`
- `slice`
- `graph`
- `provenance`
- `minimal_read_order`

## Implementation Stages

1. Add the Go module and CLI skeleton.
2. Define the new runtime marker, `status.json`, and DB schema.
3. Implement status, check, doctor, and baseline format rejection.
4. Implement scan/build validation and runtime metadata publication.
5. Implement query, lexicon, update, refresh, discovery, and read commands.
6. Change template rendering so `{{specify-subcmd:project-cognition ...}}` renders to `project-cognition ...`.
7. Remove Python runtime command implementations and the `project-map` runtime alias.
8. Update packaging, documentation, and tests for the hard switch.

## Verification

Go-side verification:

- unit tests for CLI parsing and JSON output
- unit tests for runtime marker detection
- tests that old Python-era runtime state is rejected
- SQLite/schema tests for new runtime data
- command tests for status, validation, query, lexicon, update, and refresh behavior

Spec Kit verification:

- generated command templates render `project-cognition ...`
- no generated workflow requires `specify project-cognition ...`
- no generated workflow requires `specify project-map ...`
- release packaging includes the Go executable
- README and handbook describe the breaking runtime switch
- `sp-map-scan`, `sp-map-build`, and `sp-map-update` keep their workflow semantics

Regression families to revisit:

- integration template rendering tests
- project cognition CLI tests
- project map compatibility tests
- hook and preflight tests that mention map freshness
- release packaging tests
- docs guidance tests

## Risks

- Existing project cognition baselines will stop working and require a fresh baseline.
- Removing `project-map` compatibility will break old operator habits and any automation still calling that namespace.
- Tests currently encode Python helper behavior and will need substantial replacement.
- The Go runtime must rebuild enough query/update semantics to keep workflows useful; a shallow command port would not satisfy the workflow contract.
- Packaging must make the executable reliably available on `PATH`, or generated workflows will fail at command invocation time.

## Approval Notes

The confirmed product direction is:

- external independent runtime tool
- Go implementation
- monorepo source with independent release artifact
- full replacement of Python `project-cognition` subcommands
- hard switch to new storage format
- no `project-map` alias compatibility
- prompt semantics unchanged, with rendering changed to call `project-cognition`
