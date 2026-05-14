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
- **Pre-spec discussion**: `sp-discussion` stores resumable product/technical
  discussions under `.specify/discussions/<slug>/`, produces technical options
  and requirements drafts, and only hands off to `sp-specify` through explicit
  `handoff-to-specify.md`.

## How To Read This Project

- Start here for compatibility/export orientation.
- **Default runtime truth**:
  - `.specify/project-cognition/status.json` for freshness, coverage, stale paths, and refresh metadata
  - `.specify/project-cognition/project-cognition.db` as the canonical graph store
  - the task-local project cognition query bundle, including readiness and `minimal_live_reads`
- **Cross-project cognition reference**: use the project cognition runtime as
  explicit-only, supplemental-only, fresh-only context with a minimal read before
  broader source inspection.
- New generated workflows use `.specify/project-cognition/status.json`, `.specify/project-cognition/project-cognition.db`, and `project-cognition query` as the runtime truth surface.
- Read this handbook only when a user or workflow explicitly asks for the compatibility/export view; it is not the default runtime truth path.
- Use `map-update` for localized stale cognition runtime refresh; use `map-scan` followed by `map-build` when no usable baseline remains or a full rebuild is required.
- For the first brownfield cognition baseline, run `sp-map-scan` followed by `sp-map-build`. That pair is complete only when scan acceptance and build acceptance pass: `project-cognition validate-scan --format json` and `project-cognition validate-build --format json`. After that, normal code changes should use `sp-map-update` for bounded incremental refresh. Return to `sp-map-scan -> sp-map-build` only when the baseline is missing, unusable, schema-incompatible, or the changed closure cannot be bounded safely.
- Recorded refresh and ready refresh are different outcomes: `partial_refresh` means refresh data was recorded but readiness still failed.
- Support drift is not runtime-truth staleness; resolve support-surface drift without reflexively routing to `map-update`.
- Preserve the state vocabulary: `fresh`, `missing`, `stale`, `support_drift`, `partial_refresh`, and `possibly_stale` are machine freshness states; `recommended_next_action` is the public operator guidance.
- Use `Where To Read Next` for task-oriented routing.
- Fall back to live code reads only when project cognition coverage is missing, stale, or too broad.

## Compatibility Export Model

Describe the handbook export model explicitly:

- **Debug export**: `DEBUG-HANDBOOK.md` — compatibility view of symptom routing, likely truth owners, failure propagation, investigation playbooks, and verification exit rules
- **Build/change export**: `BUILD-HANDBOOK.md` — compatibility view of product capability map, workflow sequences, change entrypoints, collaboration routes, propagation risks, implementation playbooks, and verification routes
- **Legacy project-map alias**: `specify project-map ...` routes to project cognition for existing projects; new workflows should not read or require `.specify/project-map/**`
- **Runtime truth**: `.specify/project-cognition/status.json`, `.specify/project-cognition/project-cognition.db`, and the task-local project cognition query bundle

The export model should help the reader distinguish compatibility views from
the graph-native cognition runtime used before broader code reads begin.

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
