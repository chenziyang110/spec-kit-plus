# Project Handbook

**Last Updated:** YYYY-MM-DD
**Purpose:** Compatibility/export navigation view for this repository.

## System Summary

[What this project is, its primary runtime shape, its major layers or runtime
units, and the main capability surfaces that planners or implementers must keep
in view.]

[Cover the project type, primary technology stack, build/dependency tooling, and deployment shape. Name the major capability surfaces, runtime units, and architectural boundaries that downstream readers must understand first.]

## System Boundaries

[State what this repository deliberately owns, what it coordinates but does not own,
and what sits clearly outside the system boundary.]

## High-Value Capabilities

- [List the highest-value capabilities a newcomer should understand first.]
- [For each capability, state why it matters and which topical file should be
  read next.]
- **Lossless `sp-specify` state**: `sp-specify` is lossless-state backed for
  new feature packages. The trusted recovery source is
  `brainstorming/journal.ndjson` plus JSON stage artifacts indexed by
  `brainstorming/stage-manifest.json`; Markdown is not a trusted recovery source.
  Final artifacts carry `compiled_from` / source-map references so
  planning can trace major claims to event IDs or evidence IDs.
- **Pre-spec discussion**: `sp-discussion` stores resumable product/technical
  discussions under `.specify/discussions/<slug>/`, produces technical options
  and requirements drafts, and only hands off after explicit user request.
  Handoff now begins with `handoff-assessment.md`: one bounded result writes
  latest-copy `handoff-to-specify.md` and `handoff-to-specify.json` with a
  Must-Preserve Ledger (`MP-*` items), coverage status, and planning gate status,
  while broad directions stay inside `sp-discussion` through `split-plan.md`
  candidate backlog entries and canonical
  `handoffs/<candidate_id>-handoff-to-specify.md` and
  `handoffs/<candidate_id>-handoff-to-specify.json` files, with `CAND-001` and
  `CAND-002` as examples. After one candidate ships, return to the same
  discussion slug to select the next stage.

## How To Read This Project

- Start here for compatibility/export orientation.
- **Advisory project cognition index**:
  - `.specify/project-cognition/status.json` for freshness, coverage, stale paths, and refresh metadata
  - `.specify/project-cognition/project-cognition.db` as the canonical graph store
  - the task-local project cognition query bundle, including readiness and `minimal_live_reads`
- **Cross-project cognition reference**: use the project cognition runtime as
  explicit-only, supplemental-only, fresh-only context with a minimal read before
  broader source inspection. When another local directory is used as a
  reference, check for `.specify/` first, run
  `cognition discover --root <path> --format json`, and use that project's
  cognition only when `.specify/project-cognition/status.json` and
  `.specify/project-cognition/project-cognition.db` exist,
  `reference_readiness` is `ready`, freshness is `fresh`, and `graph_ready` is
  true. If the reference is stale, blocked, or incomplete, do not treat legacy
  `.specify/project-map/**` outputs as current truth; fall back to minimal live
  reads or recommend refreshing the reference project.
- New generated workflows use `.specify/project-cognition/status.json`, `.specify/project-cognition/project-cognition.db`, and `project-cognition query` as advisory navigation inputs.
- Read this handbook only when a user or workflow explicitly asks for the compatibility/export view; it is not the default evidence path.
- Use `map-update` for localized stale cognition recommendations and ordinary changed-path map maintenance; recommend `map-scan` followed by `map-build` when the user wants a missing, unusable, schema-incompatible, explicitly rebuilt, architecture-replaced, or path-index-incomplete baseline repaired.
- For the first brownfield cognition baseline, run `sp-map-scan` followed by `sp-map-build` when you want a map baseline. That pair is complete only when scan acceptance and build acceptance pass: `project-cognition validate-scan --format json` and `project-cognition validate-build --format json`. Ordinary workflows may continue from live repository evidence when the map is missing, stale, or blocked.
- After a successful `sp-map-update`, committing the refreshed source changes does not require a full rebuild by itself; update the git-baseline freshness metadata with `project-cognition record-refresh` or `project-cognition complete-refresh` unless validation reports `needs_rebuild`.
- Recorded refresh and ready refresh are different outcomes: `partial_refresh` means refresh data was recorded but readiness still failed.
- Use `.cognitionignore` or `.specify/project-cognition/.cognitionignore` to exclude vendored, generated, archived, or nested-reference projects from project cognition. The rules are gitignore-compatible and affect `map-scan`, `map-build`, and `map-update`; excluded paths must not enter project cognition graph evidence, runtime route indexes, or `minimal_live_reads`.
- Support drift is not runtime-truth staleness; resolve support-surface drift without reflexively routing to `map-update`.
- Preserve the state vocabulary: `fresh`, `missing`, `stale`, `support_drift`, `partial_refresh`, and `possibly_stale` are machine freshness states; `recommended_next_action` is the public operator guidance.
- Use `Where To Read Next` for task-oriented routing.
- Map points, code proves: use live code, tests, scripts, configuration, or authoritative docs as evidence whenever making technical claims.

## Compatibility Export Model

Describe the handbook export model explicitly:

- **Debug export**: `DEBUG-HANDBOOK.md` — compatibility view of symptom routing, likely truth owners, failure propagation, investigation playbooks, and verification exit rules
- **Build/change export**: `BUILD-HANDBOOK.md` — compatibility view of product capability map, workflow sequences, change entrypoints, collaboration routes, propagation risks, implementation playbooks, and verification routes
- **Legacy project-map alias**: `specify project-map ...` routes to project cognition for existing projects; new workflows should not read or require `.specify/project-map/**`
- **Advisory navigation**: `.specify/project-cognition/status.json`, `.specify/project-cognition/project-cognition.db`, and the task-local project cognition query bundle

The export model should help the reader distinguish compatibility views from
the graph-native cognition runtime used as advisory navigation before broader code reads begin.

## Senior Consequence Analysis Gate

Project cognition is necessary but not sufficient for dependency analysis. It gives workflow agents ownership, consumers, state surfaces, change-propagation facts, verification routes, conflicts, and known unknowns. The map points to likely evidence, but the Senior Consequence Analysis Gate turns live project facts into product and implementation obligations.

When work involves lifecycle operations, running or concurrent objects, destructive actions, shared state, downstream consumers, compatibility, security, or multiple plausible behaviors, workflows must preserve:

- Affected Object Map
- State-Behavior Matrix
- Dependency Impact Table
- Recovery And Validation Contract
- Coverage Gaps

For example, "close team" must consider running workers, queued tasks, late result submission, heartbeat state, `status`, `await`, `resume`, `cleanup`, idempotency, and validation evidence before the workflow can claim the feature is ready for the next stage.

Use `CA-###` IDs for consequence obligations that must survive handoff from `discussion` to `specify`, `plan`, `tasks`, `analyze`, and `implement`. `fast` upgrades when the gate triggers; `quick` may continue only when the consequence model is bounded; `debug` traces the dependency loop and rejects surface-only fixes.

## Shared Surfaces

- [Registries, routing files, template directories, config schemas, exported
  contracts, or other shared surfaces whose changes propagate into multiple
  areas]

## Risky Coordination Points

- [Files, modules, or runtime surfaces that can silently affect multiple
  workflows or capability surfaces]

## Change-Propagation Hotspots

- [Where a change is likely to fan out across consumers, integrations, config,
  scripts, docs, operators, or tests]

## Change Impact Guide

- [Provide the fastest route from a proposed code change to the affected cognition slices and compatibility/export views.]
- [For each major hotspot, say which topical document explains the blast radius,
  hidden dependencies, lifecycle risks, and minimum verification route.]
- [For existing capabilities, route readers through the capability flow and lifecycle truth layer before broader source inspection.]

## Verification Entry Points

- [Fastest trustworthy checks, scripts, suites, or manual proofs for the major
  capability surfaces]

## Known Unknowns

- [Stale areas, unresolved ownership, weak observability, or evidence gaps that
  downstream workflows should treat carefully]

## Low-Confidence Areas

- [Call out current stale, inferred, or weakly evidenced areas so readers know
  where extra live-code verification is needed.]
- [Tie low-confidence areas back to specific capabilities, workflows, or boundaries whenever possible.]

## Atlas Views

- [Summarize which cognition status and slices answer debugging, requirement shaping, implementation planning, testing, and verification questions.]
- [Call out where compatibility/export handbooks still help continuity without becoming the primary runtime truth path.]

## Where To Read Next

- [If you need to add or extend a capability, point to the topical file most
  likely to contain ownership, placement, and verification guidance.]
- [If you need to debug or extend an existing capability, route first through `By Symptom` or `By Capability`, then the matching deep workflow page.]
- [If you need API or protocol details, route to the relevant integration or
  workflow sections.]

## Topic Map

- `.specify/project-cognition/status.json` - default runtime status, freshness, coverage, stale paths, and refresh metadata
- `.specify/project-cognition/project-cognition.db` - canonical SQLite graph store
- project cognition query bundle - default route to task-local cognition bundles, readiness, and `minimal_live_reads`
- `DEBUG-HANDBOOK.md` - compatibility/export debug view
- `BUILD-HANDBOOK.md` - compatibility/export build/change view
- `specify project-map ...` - legacy CLI alias for existing projects, not the new runtime truth path

## Update Triggers

- [When structure, ownership, interfaces, workflows, or runtime assumptions change]

## Recent Structural Changes

- [Short rolling summary]
