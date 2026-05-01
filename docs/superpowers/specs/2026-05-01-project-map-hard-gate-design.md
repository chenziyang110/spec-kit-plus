# Project-Map Hard Gate and Atlas Knowledge Base Design

**Date:** 2026-05-01
**Status:** Proposed
**Owner:** Codex

## Summary

This design restores `project-map` to its intended role: the mandatory
knowledge base that every `sp-*` workflow must read before it inspects source
code, proposes a fix, writes a plan, or edits implementation files.

The approved direction is:

- treat `project-map` as a hard-read atlas, not as optional navigation help
- keep the four-layer atlas model, but make every layer mandatory in a defined
  minimum read set before source-level work begins
- upgrade Layer 1 from a thin route table into a high-signal entry index that
  behaves like a dictionary and compass for repository work
- keep `map-scan -> map-build` as the atlas production path, but make its
  outputs more query-friendly and more clearly shaped for downstream workflow
  consumption
- unify atlas consumption semantics across this repository and generated
  projects so workflows always follow one logical atlas contract even when the
  physical file paths differ
- make atlas consumption auditable so workflows can prove which atlas surfaces
  they actually read

This is not a token-saving design. It is a correctness and execution-quality
design. The goal is to make atlas consumption mandatory, useful, and testable.

## Problem Statement

The current system has a structural mismatch between atlas production and atlas
consumption.

On the production side, the repository has already moved toward a stronger
atlas model:

- `sp-map-scan` produces inventory, coverage ledgers, and executable scan
  packets
- `sp-map-build` consumes those packets, reads live repository evidence, and
  writes handbook plus atlas outputs
- the project-map design already treats the atlas as layered technical truth

On the consumption side, however, `sp-*` workflows have drifted away from that
intent:

1. `context-loading-gradient.md` turns layering into a "read less" policy
   instead of a "read the atlas first, then go deeper as needed" policy.
2. `sp-fast` and `sp-quick` can now proceed after reading only Layer 1 or even
   just a route table plus source files, which bypasses the atlas as a true
   knowledge base.
3. some workflows still carry older hard-gate instructions that require
   reading `PROJECT-HANDBOOK.md` and relevant `project-map` docs, while the
   newer layered sections suggest lighter reads. Those mixed signals encourage
   shallow execution.
4. freshness behavior was softened into warning-first behavior for lightweight
   commands, which lets workflows proceed on stale or weak atlas coverage.
5. this repository no longer treats repo-local `.specify/project-map/**` as
   committed source-of-truth content, but many templates and injected
   instructions still hardcode those physical paths. As a result, the same
   logical atlas can resolve to different physical paths depending on where the
   workflow runs.

The result is predictable:

- workflows often inspect code before atlas truth
- workflows can route themselves from shallow context
- lightweight commands lose architectural awareness
- the atlas behaves like a helpful optional doc set instead of the repository's
  working knowledge base

This design exists to remove that ambiguity.

## Goals

- Make `project-map` the mandatory pre-source knowledge base for all `sp-*`
  workflows other than `sp-map-scan` and `sp-map-build`.
- Preserve the existing layered atlas model while redefining it as a hard-read
  contract.
- Keep `PROJECT-HANDBOOK.md` as the root entrypoint, but require workflows to
  continue into relevant atlas layers before source work.
- Upgrade Layer 1 into a real problem-routing and knowledge-retrieval entry
  surface.
- Define one logical atlas contract that works for both this repository and
  generated projects.
- Make freshness a real gate again, not just a warning.
- Shape `map-scan` and `map-build` outputs so they are optimized for workflow
  consumption, not only for document generation.
- Record enough atlas-read evidence that workflow runs can prove what they
  consumed.

## Non-Goals

- Do not remove or replace the layered atlas model.
- Do not replace `PROJECT-HANDBOOK.md` with a purely machine-readable file.
- Do not collapse all technical truth back into one global document.
- Do not make source code the first-read surface again.
- Do not preserve the current "warn but proceed" approach for stale atlas state
  as the default workflow behavior.
- Do not maintain two separate consumption contracts for this repository and
  generated projects.

## Current-State Assessment

### Atlas Production

`map-scan` and `map-build` are already directionally aligned with the idea of
an atlas-style knowledge base:

- `map-scan` inventories the repository, classifies surfaces, assigns reading
  depth, scores criticality, and produces scan packets
- `map-build` validates the scan package, dispatches read-only explorer work,
  writes atlas outputs, and runs reverse coverage checks
- the atlas output family already includes handbook, Layer 1 entry, machine
  indexes, root topical docs, and module-local docs

This means the production side is much closer to the target state than the
consumption side.

### Atlas Consumption

The workflows are not currently aligned with the atlas-as-knowledge-base
vision.

Observed problems:

- workflows can treat Layer 1 as sufficient context
- lightweight commands are allowed to skip root and module atlas reads
- stale atlas state can be tolerated instead of blocking work
- templates mix old hard-gate language with new layered-minimization language
- path contracts drift between this repository and generated projects

The system therefore behaves like this:

```text
atlas production: strong
atlas consumption: weak
overall workflow quality: degraded
```

## Approved Atlas Role

The atlas becomes the canonical pre-source knowledge base for repository work.

That means:

- atlas first
- source second
- chat memory never substitutes for atlas truth

More concretely:

- `PROJECT-HANDBOOK.md` remains the root orientation artifact
- Layer 1 routes the workflow into the right atlas surfaces
- Layer 2 expresses root-level cross-module truth
- Layer 3 expresses module-local truth
- Layer 4 remains the source evidence layer used only after the atlas has
  constrained the problem space

This role applies to every ordinary `sp-*` workflow, including `sp-fast` and
`sp-quick`.

## Approved Layer Model

The four-layer model remains intact, but its meaning changes from
"progressively optional" to "progressively mandatory with a minimum read set."

### Layer 1: Entry / Compass / Dictionary

Purpose:

- classify the current problem shape quickly
- route the workflow to the right root topics and modules
- reveal high-risk shared surfaces and change-propagation hotspots
- expose verification entry points and common route patterns

Layer 1 is not just a task-type route table. It is the atlas retrieval layer.

### Layer 2: Root Cross-Module Truth

Purpose:

- architecture boundaries
- workflows and state transitions
- conventions and placement rules
- integrations and protocol seams
- testing strategy and verification entry points
- operations and recovery rules

Layer 2 is mandatory decision context, not optional background reading.

### Layer 3: Module-Local Truth

Purpose:

- module ownership
- truth lives
- extension guidance
- change propagation
- module-local workflows and testing
- module-level known unknowns and stale boundaries

Most feature planning, implementation, and debugging work will rely on this
layer once Layer 1 identifies the relevant module.

### Layer 4: Source Evidence

Purpose:

- verify atlas claims
- inspect concrete implementation details
- gather exact signatures, behavior, and failing evidence

Source code is a proof layer, not the default starting point.

## Hard Atlas Gate

Every `sp-*` workflow except `sp-map-scan` and `sp-map-build` must pass an
atlas gate before it performs any of the following:

- repository search
- file reading beyond the atlas minimum set
- reproduction or test execution
- planning or debugging analysis
- code changes
- user-facing technical recommendations

### Minimum Required Read Set

The atlas gate succeeds only after the workflow has read:

1. `PROJECT-HANDBOOK.md`
2. `atlas.entry`
3. `atlas.index.status`
4. `atlas.index.atlas`
5. at least one relevant root topic document
6. at least one relevant module overview document

If the current task touches shared surfaces, cross-module seams, or protocol
boundaries, the workflow must also read:

- `atlas.index.relations`
- any additional root topics identified by the entry layer

### Command-Specific Minimums

`sp-fast`

- must still pass the atlas gate
- may stop after the minimum required read set when the task is truly local and
  the atlas indicates no cross-surface risk
- may not skip root/module docs and jump from Layer 1 directly to source

`sp-quick`

- must pass the atlas gate
- must also read any atlas relation or root topic surfaces named by Layer 1 for
  the touched area

`sp-debug`

- must pass the atlas gate
- must read workflow, testing, and operations root topics before reproduction
  or code tracing

`sp-specify`, `sp-plan`, `sp-tasks`

- must pass the atlas gate
- must read the relevant root topics, module docs, and relation surfaces needed
  for cross-surface planning decisions

`sp-implement`

- has the strictest gate
- may not compile packets, dispatch subagents, or inspect implementation files
  before the atlas read set is complete

## Freshness Policy

The atlas is only a reliable knowledge base if freshness is enforced.

### Approved Rule Set

- `missing`: block
- `stale`: block
- `possibly_stale`: evaluate topic impact before proceeding

The lightweight-command rule of "warn but proceed" is rejected.

### `possibly_stale` Behavior

When atlas state is `possibly_stale`, the workflow must inspect the
topic-routing output:

- if current task topics intersect `must_refresh_topics`, block and refresh
- if current task topics intersect `review_topics`, review the affected atlas
  docs before deciding whether they are still sufficient
- proceed only when the atlas remains task-sufficient for the touched area

This keeps the atlas usable without turning stale-state handling into
guesswork.

## Logical Atlas References

Templates and workflow rules must stop hardcoding physical atlas paths as the
primary contract.

### Approved Logical References

- `atlas.entry`
- `atlas.index.status`
- `atlas.index.atlas`
- `atlas.index.modules`
- `atlas.index.relations`
- `atlas.root.architecture`
- `atlas.root.structure`
- `atlas.root.conventions`
- `atlas.root.integrations`
- `atlas.root.workflows`
- `atlas.root.testing`
- `atlas.root.operations`
- `atlas.module.<id>.overview`
- `atlas.module.<id>.architecture`
- `atlas.module.<id>.structure`
- `atlas.module.<id>.workflows`
- `atlas.module.<id>.testing`

### Resolution Model

Generated projects resolve those references to:

- `.specify/project-map/**`

This repository resolves them to:

- `PROJECT-HANDBOOK.md`
- `templates/project-map/**`

The key rule is that workflows consume the same logical atlas contract in both
places, even when the physical files differ.

## Layer 1 Redesign

Layer 1 must become a true problem-index surface instead of a thin route table.

### Required Retrieval Dimensions

The entry layer must support at least:

- task routes
- symptom routes
- shared-surface hotspot routes
- verification routes
- propagation-risk routes
- module lookup
- root-topic lookup

### Required Answers

Layer 1 must help a workflow answer:

- what kind of problem is this
- which root topic should I read first
- which module most likely owns the touched area
- which shared surfaces are risky here
- which verification entry points matter if I change this surface
- which neighboring modules or workflows are likely to be affected

### Example Query Shape

For a problem such as "workflows are no longer reading project-map," the entry
layer should route directly to:

- handbook
- workflow root topic
- architecture root topic
- templates-generated-surfaces module docs
- relevant shared partials and integration injection surfaces
- verification entry points for template guidance and atlas contract tests

This is the behavior expected from a dictionary-like atlas entry surface.

## `map-scan` Adjustments

`map-scan` already produces most of the right foundational material, but it
must start producing Layer 1 retrieval inputs explicitly.

### Existing Strengths To Keep

- repository inventory
- coverage classification
- reading depth assignment
- criticality scoring
- scan packet generation
- reverse mapping to atlas targets

### New Required Outputs

The scan package must also produce inputs for:

- symptom indexes
- hotspot indexes
- verification indexes
- propagation indexes

These may live inside the existing ledger and packet structures, but they must
be explicit enough for `map-build` to synthesize a strong Layer 1 entry.

### New Coverage Expectation

High-value surfaces must not only map to final atlas docs. They must also be
discoverable through the retrieval model expected by Layer 1.

## `map-build` Adjustments

`map-build` must continue to be the only atlas-writing step, but it must become
more consumption-oriented.

### Existing Strengths To Keep

- scan-package validation
- live repository reads
- packet evidence intake
- atlas synthesis
- reverse coverage validation

### New Responsibilities

`map-build` must ensure the atlas is:

- query-friendly
- gate-friendly
- machine-routable
- human-readable
- verification-aware

### Entry Layer Upgrade

`QUICK-NAV.md` must be expanded from a task table into a richer entry layer that
includes:

- task routes
- symptom routes
- hotspots
- verification entry points
- propagation-risk patterns

### Index Upgrade

The machine indexes should behave like an atlas query API for workflows:

- `atlas-index.json`: entry summary plus next-read routing metadata
- `modules.json`: module ownership, truth surfaces, and verification entry
  points
- `relations.json`: propagation and dependency relationships
- `status.json`: freshness and stale-surface routing data

The indexes should not be treated as atlas-internal scaffolding only.

## Consumption Evidence

Atlas consumption must become auditable.

Each workflow state surface should record an atlas read set before it is
allowed to proceed.

### Minimum Evidence Fields

- `atlas_read_completed`
- `atlas_paths_read`
- `atlas_root_topics_read`
- `atlas_module_docs_read`
- `atlas_status_basis`
- `atlas_blocked_reason`

### Suggested State Surfaces

- `workflow-state.md`
- quick `STATUS.md`
- debug session files
- `implement-tracker.md`
- packet metadata where relevant

This does not replace real file reads, but it makes them observable and
testable.

## Reverse Coverage Expansion

The current reverse coverage model is necessary but not sufficient.

### Existing Reverse Coverage To Keep

- every critical row lands in atlas targets
- every important row lands in atlas targets or grouped surfaces
- every accepted packet result has paths read and confidence

### New Consumption Reachability Checks

The atlas should also prove:

- every high-frequency problem type can be routed from Layer 1
- every critical shared surface can be discovered from Layer 1 or atlas indexes
- every key verification entry point can be located from Layer 1 or module
  metadata

This closes the gap between "the atlas mentions the truth somewhere" and
"workflows can actually find the truth before they start coding."

## Implementation Priorities

### Phase 1: Stop the Drift

Priority:

- rework the shared context-loading contract so every `sp-*` workflow uses an
  atlas hard gate
- remove lightweight exceptions that skip root/module atlas reads
- restore blocking behavior for stale atlas state

### Phase 2: Unify Logical Atlas References

Priority:

- replace hardcoded physical atlas paths in shared templates and injected
  workflow guidance with logical atlas references
- align this repository and generated projects under the same logical atlas
  contract

### Phase 3: Strengthen Layer 1

Priority:

- redesign `QUICK-NAV.md`
- shape machine indexes for retrieval
- make `map-scan` and `map-build` produce and synthesize query-oriented entry
  data

### Phase 4: Add Consumption Evidence

Priority:

- record atlas read sets in workflow state surfaces
- add tests that prove workflows cannot bypass atlas consumption

## Acceptance Criteria

This design is successful when all of the following are true:

- no ordinary `sp-*` workflow can begin source-level work before passing an
  atlas gate
- `sp-fast` and `sp-quick` both consume atlas truth before they read source
  code
- stale atlas state blocks work instead of merely generating warnings
- this repository and generated projects use the same logical atlas contract
- Layer 1 can route by task type, symptom, hotspot, verification, and
  propagation pattern
- `map-scan` and `map-build` produce atlas outputs that are clearly shaped for
  downstream workflow consumption
- workflow state surfaces can prove which atlas surfaces were read

## Recommendation

Adopt the design as written.

The atlas production side is already strong enough to support this direction.
The highest-value work is to re-establish atlas consumption as a hard gate,
unify logical atlas references, and redesign Layer 1 so workflows can route
into deep knowledge quickly and reliably.
