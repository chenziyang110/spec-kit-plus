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

Required commands:

```text
project-cognition status --format json
project-cognition check --format json
project-cognition mark-dirty --reason <reason> --format json
project-cognition clear-dirty --format json
project-cognition record-refresh --reason <reason> --format json
project-cognition complete-refresh --format json
project-cognition refresh-topics <topic>... --reason <reason> --format json

project-cognition validate-scan --format json
project-cognition validate-build --format json
project-cognition publish-runtime-metadata --format json
project-cognition update --changed-path <path> --reason <reason> --format json

project-cognition lexicon --intent <intent> --query <text> --format json
project-cognition query --intent <intent> --query-plan <json> --format json
project-cognition discover --root <path> --format json
project-cognition read --root <path> --format json
project-cognition doctor --format json
project-cognition rebuild
```

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

Generated projects must have a documented requirement that `project-cognition` is on `PATH` before `sp-map-*` workflows use project cognition runtime commands.

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
