# Cross-Project Project Cognition Reference Design

**Date:** 2026-05-11
**Status:** Approved
**Owner:** Codex

## Summary

This design adds a shared, explicit, and conservative way for one
`spec-kit-plus` downstream project to reference another downstream project's
project cognition runtime.

The approved direction is:

- keep the current brownfield default unchanged: workflows still trust the
  current project's own `.specify/project-cognition/*` first
- add an explicit helper surface for discovering downstream project candidates
  and reading a named reference project's project cognition runtime
- detect candidates by finding directories that contain `.specify/`
- support nested downstream projects inside a larger container repository or
  workspace
- allow discovery to be automatic and lightweight
- require explicit user intent before any deep read of another project's
  cognition runtime
- treat non-`fresh` external cognition as ineligible reference context
- keep `.specify/project-map/*` and handbook outputs as compatibility or export
  surfaces, not the primary cross-project reference entrypoint

This is a shared runtime capability, not a new `sp-*` workflow.
It should be implemented as a helper surface that existing workflows can call
when the user explicitly asks to reference another downstream project.

## Problem

Generated downstream projects now keep their primary brownfield runtime truth
under `.specify/project-cognition/status.json` and the workflow-appropriate
slice files.

That solves single-project context loading, but there is still no shared,
product-level way to do the following safely:

1. start from a larger directory that may contain multiple downstream projects
2. discover which nested directories are valid `spec-kit-plus` downstream
   projects
3. inspect lightweight eligibility metadata without pulling in deep context
4. explicitly choose one of those projects as a reference project
5. read only the minimum project cognition artifacts needed from that chosen
   project
6. refuse to use reference cognition that is stale, missing, or otherwise
   untrusted

Without this capability, users and workflows fall back to ad hoc behavior:

- guessing candidate project roots manually
- reading handbook or project-map exports because they are easier to find
- over-reading another project's files without an explicit trust check
- treating stale cognition as "close enough" reference context

That produces three product problems.

### 1. Discovery is not standardized

The system does not currently expose one shared rule for "what counts as a
downstream project candidate inside a larger root".

### 2. Trust is not enforced consistently

The current project-map gate explains how to trust the active project's own
runtime truth, but there is no equivalent contract for external reference
context.

### 3. Atlas and cognition can be conflated again

The repository has already moved the main runtime truth path from
`.specify/project-map/*` to `.specify/project-cognition/*`.
If cross-project reading is added carelessly, users and templates may start
using project-map exports as the convenient cross-project entrypoint and
reintroduce the exact ambiguity the cognition runtime was created to resolve.

## Goals

- Add a shared helper surface for discovering nested downstream project
  candidates under a larger root path.
- Make `.specify/` the cheap and deterministic candidate signal.
- Let workflows auto-discover candidates conservatively without auto-reading
  deep foreign context.
- Require explicit user intent before reading another project's cognition
  runtime.
- Treat only `fresh` external cognition as admissible reference context.
- Read the smallest matching external cognition surface first:
  `status.json`, then the requested slice, then targeted graph artifacts only
  when explicitly needed.
- Preserve provenance so the system can distinguish "current project truth"
  from "reference project supplemental evidence".
- Keep the capability shared across CLI integrations and reusable from prompts,
  hooks, teams runtime, and future helper surfaces.

## Non-Goals

- Do not change the brownfield default so that ordinary workflows start reading
  sibling or nested downstream projects automatically.
- Do not guess which external project is "probably relevant".
- Do not merge multiple projects into one federated project cognition graph.
- Do not write external cognition data back into the active project.
- Do not run `map-update`, `map-scan`, or `map-build` automatically against a
  reference project from another workflow.
- Do not promote `.specify/project-map/*`, `PROJECT-HANDBOOK.md`, or other
  compatibility or export surfaces back to the primary cross-project truth
  entrypoint.
- Do not auto-inject external cognition into delegated worker packets in this
  first pass.

## Current Constraints

The existing repository already establishes the following constraints:

- generated downstream projects should treat
  `.specify/project-cognition/status.json` plus the smallest matching slice as
  the default brownfield runtime truth path
- `.specify/project-map/*` is still useful, but as a compatibility or export
  surface
- `src/specify_cli/cognition/paths.py` already defines the canonical active
  project's project cognition filesystem layout
- `templates/passive-skills/spec-kit-project-map-gate/SKILL.md` already makes
  the active project's cognition runtime the hard gate before ordinary
  brownfield work
- workflow templates such as `templates/commands/explain.md` already teach
  minimal cognition loading for the current project

The new capability should align with those rules instead of introducing a
parallel context-loading model.

## Approved Direction

Three approaches were considered.

### Option 1: Prompt-Only Convention

- update workflow templates to say "if the user names another project, go read
  that project's cognition files"
- do not add a shared runtime helper

### Option 2: Shared Cross-Project Cognition Helper Surface

- add an explicit discovery and read capability in the CLI and Python runtime
- let workflows call that helper when the user explicitly requests a reference
  project

### Option 3: Automatic Multi-Project Context Fusion

- scan nearby projects automatically
- infer the relevant candidate
- merge foreign context into ordinary workflow startup

The approved direction is Option 2.

Option 1 is too fragile.
It spreads behavior across prompts, makes testing weak, and creates drift risk.

Option 3 is too aggressive.
It violates the desired trust boundary and makes context loading opaque.

Option 2 is the smallest solution that is explicit, testable, and consistent
with the current runtime architecture.

## Product Rules

The following rules are mandatory.

### Rule 1: Discovery May Be Automatic, Deep Read May Not

The system may automatically discover candidate downstream projects under a
larger root.
It may not automatically read a candidate project's deeper cognition runtime
just because that candidate exists.

### Rule 2: External Cognition Is Supplemental Only

The current project's own cognition runtime remains authoritative for the
current task.
External cognition is supplemental evidence only.
It can inform understanding, but it must not override current-project truth.

### Rule 3: Freshness Is a Hard Admission Gate

External cognition may be read only when the reference project's
`.specify/project-cognition/status.json` admits it as `fresh`.

The following states must block admission:

- `missing`
- `stale`
- `partial_refresh`
- `possibly_stale`
- any future non-ready state that is not explicitly classified as `fresh`

There is no degrade-to-warning fallback in this first pass.
Non-fresh external cognition is ineligible reference context.

### Rule 4: Project Cognition Is the Primary Entry Surface

Cross-project reference loading must begin from:

- `.specify/project-cognition/status.json`
- the requested slice under `.specify/project-cognition/slices/`
- targeted graph artifacts under `.specify/project-cognition/graph/` only when
  required

Compatibility or export surfaces such as `.specify/project-map/*`,
`PROJECT-HANDBOOK.md`, `DEBUG-HANDBOOK.md`, and `BUILD-HANDBOOK.md` must not be
the primary cross-project entrypoint.

## Discovery Model

### Discovery Root

Discovery starts from a user-supplied root path.
That root may be:

- a workspace folder
- a monorepo root
- a product umbrella repository
- any directory that may contain one or more downstream projects

### Candidate Rule

A directory is a downstream project candidate when it contains a `.specify/`
directory.

This should remain cheap and deterministic.
Discovery must not require deep file parsing just to decide whether a directory
is a candidate.

### Nested Projects

Discovery must support nested downstream projects.

If a larger container directory contains:

- one top-level downstream project
- several nested downstream projects
- or both

the scanner should report all valid candidates.

The scanner must therefore continue descending after finding a candidate rather
than assuming the first match is the only valid project root.

### Traversal Safety

Discovery should stay bounded and safe:

- avoid symlink loops
- avoid descending into obvious heavyweight non-source directories when they
  are not needed for candidate detection
- remain read-only

The implementation may prune common directories such as `.git`,
`node_modules`, `.venv`, `dist`, `build`, and cache directories, as long as the
rule stays deterministic and documented.

## Runtime Surface

This capability should be exposed as a low-level helper surface, not as a new
top-level planning workflow.

### New CLI Group

Add a new `cognition` CLI group under the main Typer app.

This makes the capability:

- explicit
- testable
- reusable
- consistent with other helper surfaces such as `project-map`, `learning`,
  `lane`, and `hook`

### Command: `specify cognition discover`

Suggested shape:

```text
specify cognition discover --root <path> [--format json]
```

Behavior:

- recursively scan the supplied root
- return downstream project candidates only
- do not read deep cognition artifacts
- do not read handbook or project-map exports
- do not infer which candidate should be used

### Command: `specify cognition read`

Suggested shape:

```text
specify cognition read --project <path> --slice change|debug [--include-graph nodes,edges,claims,conflicts] [--format json]
```

Behavior:

- accept one explicit reference project root
- verify that the path is a downstream project candidate
- load `status.json` first
- reject the read if the reference project's cognition runtime is not `fresh`
- load the requested slice only after admission succeeds
- load graph artifacts only when they are explicitly requested by the caller

This command should support direct use with a known project path.
It does not have to require a preceding `discover` call, but workflows should
normally use discovery first when the user starts from a larger root.

## Python Runtime Structure

Add shared Python helpers under `src/specify_cli/cognition/`.

Suggested modules:

- `src/specify_cli/cognition/discovery.py`
- `src/specify_cli/cognition/reference_read.py`

These helpers should reuse `src/specify_cli/cognition/paths.py` for local path
construction instead of inventing another filesystem contract.

The point is to avoid duplicating discovery and admission logic in:

- workflow templates
- hooks
- teams runtime
- future MCP or API helpers

## Data Contracts

The helper surface should preserve enough metadata to keep provenance and
admission explicit.

### Discover Payload

Each candidate should include at least:

- `project_root`
- `relative_path`
- `has_specify`
- `has_cognition`
- `freshness`
- `graph_ready`
- `available_slices`
- `repository` or `summary` when lightweight metadata is available from
  `status.json`

If cognition metadata is missing, discovery should still report the candidate.
It should simply mark it as non-admissible for deep reading.

### Read Payload

The read result should include at least:

- `reference_project`
- `admission`
  - `allowed`
  - `reason`
- `status`
- `slice`
- `graph`
- `provenance`

`provenance` should record the exact source paths that were read.

This matters because higher-level workflows must be able to say:

- which facts came from the current project
- which facts came from a named reference project
- which source files justify those facts

## Read Order Contract

Cross-project context loading must remain minimal.

### Minimum Read Order

1. `<project>/.specify/project-cognition/status.json`
2. requested slice:
   - `slices/change.json` for ordinary change or planning context
   - `slices/debug.json` for debugging context

### Optional Deeper Read

Only when the caller explicitly asks for it, or when the active workflow cannot
answer the needed ownership, propagation, or conflict question from the slice
alone, may the helper read targeted graph artifacts such as:

- `graph/nodes.json`
- `graph/edges.json`
- `graph/claims.json`
- `graph/conflicts.json`

Graph reads should remain targeted and explicit.
This helper should not default to loading the full graph set on every read.

## Workflow Integration

### Opt-In Only

Ordinary brownfield startup remains unchanged.
The project-map gate still means:

- read the current project's own project cognition runtime first
- do not mix in external cognition automatically

### When Workflows May Use External Cognition

Workflows may use the helper only when the user explicitly requests reference
context from another downstream project.

This is appropriate for workflows that gather explanatory or planning context,
such as:

- `explain`
- `clarify`
- `deep-research`
- `plan`
- `debug`

### How Workflows Should Use It

The workflow should:

1. discover candidates under a user-supplied root when needed
2. ask the user to explicitly name or confirm one candidate
3. read only that candidate's admissible cognition runtime
4. cite the reference project as supplemental context
5. continue using the active project's own cognition runtime as authoritative

### What Workflows Must Not Do

Workflows must not:

- silently switch to a foreign project's cognition runtime
- auto-merge multiple reference projects
- use non-fresh foreign cognition "with warning"
- rewrite current-project truth based on external cognition

## Template and Passive Skill Updates

The helper is a shared runtime surface, but relevant prompts and passive skills
still need to know it exists.

Update the following surfaces so they teach the same contract:

- `templates/commands/explain.md`
- `templates/commands/clarify.md`
- `templates/commands/deep-research.md`
- `templates/commands/plan.md`
- `templates/commands/debug.md`
- `templates/passive-skills/spec-kit-project-map-gate/SKILL.md`

Those updates should add one shared rule:

- when the user explicitly requests a different downstream project as reference
  context, use the cross-project cognition helper
- external cognition remains supplemental
- only `fresh` external cognition is admissible
- project-map and handbook exports remain non-primary for this purpose

## Delegation and Packet Scope

This first pass should not auto-inject external cognition into worker task
packets.

Reason:

- delegated packets currently assume the active project's own context bundle
- automatic foreign-context packet propagation would enlarge scope
- it would need a stronger contract for provenance, trust acknowledgement, and
  task-local relevance

The approved v1 behavior is:

- leader workflows may use external cognition for understanding and planning
- if a leader later wants a subagent to see that reference, it must be passed
  deliberately by the higher-level workflow, not silently by the shared packet
  compiler

This keeps the first pass narrow and reduces regression risk.

## Error Handling

The helper should fail clearly in the following cases.

### Discover Errors

- root does not exist
- root is unreadable
- traversal failure blocks completion

### Read Errors

- project path does not contain `.specify/`
- project cognition runtime is missing
- `status.json` cannot be parsed
- `freshness` is not `fresh`
- requested slice is missing
- requested graph artifact is missing

The user-visible error should say why the read was refused.
For blocked freshness states, it should explicitly state that non-fresh external
project cognition cannot be used as reference context.

## Testing Surface

This feature must ship with shared regression coverage.

### 1. Discovery Tests

Cover at least:

- one downstream project under the root
- multiple nested downstream projects under the root
- a directory with `.specify/` but no project cognition runtime
- non-downstream directories that should be ignored

### 2. Admission and Read Tests

Cover at least:

- `fresh` reference cognition is admitted
- `missing`, `stale`, `partial_refresh`, and `possibly_stale` are rejected
- missing slice returns a clear error
- graph artifacts are not read unless explicitly requested

### 3. CLI Surface Tests

Cover at least:

- `specify cognition discover`
- `specify cognition read`
- JSON output shape
- stable refusal behavior for non-admissible projects

### 4. Prompt and Guidance Contract Tests

Cover at least:

- updated templates and passive skills mention external cognition only as an
  explicit helper path
- relevant surfaces repeat the `fresh only` rule
- relevant surfaces do not regress into teaching `.specify/project-map/*` as
  the default cross-project truth entrypoint

## Documentation Surface

At minimum, update:

- `README.md`
- `PROJECT-HANDBOOK.md`

The docs should explain:

- what cross-project cognition reference is for
- that it is a helper surface, not a new workflow
- that discovery may be automatic but deep read must be explicit
- that only `fresh` external cognition is admissible
- that compatibility or export atlas files are not the primary source for this
  feature

## Rollout Strategy

Implement this as a bounded shared-runtime change:

1. add the Python discovery and read helpers
2. expose them through the CLI
3. cover them with contract tests
4. update templates and docs to teach the same rules

Do not combine this work with broader multi-project orchestration,
cross-project packet propagation, or project-map contract redesign.

## Self-Review Checklist

This design passes the required review loop:

- no `TODO`, `TBD`, or placeholder sections remain
- the discovery rule, admission rule, and read-order rule are explicit
- the scope stays bounded to a helper capability rather than a new workflow
- the trust boundary is unambiguous: explicit only, supplemental only, fresh
  only
- the design does not reintroduce project-map exports as the primary truth path

## Decision

Implement a shared `cognition` helper surface that:

- discovers nested downstream project candidates by finding `.specify/`
- reads only explicitly selected reference projects
- admits only `fresh` external cognition
- starts from `status.json`, then the smallest matching slice, then optional
  graph artifacts
- keeps external cognition supplemental to the active project's own runtime
  truth
