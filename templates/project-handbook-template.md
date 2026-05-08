# Project Handbook

**Last Updated:** YYYY-MM-DD
**Purpose:** Root navigation artifact for this repository.

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

## How To Read This Project

- Start here for orientation.
- **Runtime handbook entrypoints**:
  - `DEBUG-HANDBOOK.md` for `sp-debug`
  - `BUILD-HANDBOOK.md` for ordinary non-debug `sp-*` workflows
- These workflow handbooks are the only primary runtime atlas documents.
- Read the handbook required by the current workflow before broad brownfield work.
- Read the fixed chapter IDs required by the current workflow contract instead of freeform scanning.
- Supporting project-map artifacts may exist for refresh workbench, continuity, or reference use, but they are not the primary runtime read path.
- Use `Where To Read Next` for task-oriented routing.
- Fall back to live code reads only when handbook coverage is missing, stale, or too broad.

## Runtime Handbook Entry Model

Describe the two-handbook runtime atlas explicitly:

- **Debug handbook**: `DEBUG-HANDBOOK.md` — symptom routing, likely truth owners, failure propagation, investigation playbooks, and verification exit rules
- **Build/change handbook**: `BUILD-HANDBOOK.md` — product capability map, workflow sequences, change entrypoints, collaboration routes, propagation risks, implementation playbooks, and verification routes
- **Source of last resort**: live code and runtime state when handbook coverage is missing, stale, or too broad

The entry model should help the reader decide which workflow handbook owns the
task before broader code reads begin.

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

- [Provide the fastest route from a proposed code change to the affected atlas views.]
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

- [Summarize which workflow handbook answers debugging, requirement shaping, implementation planning, testing, and verification questions.]
- [Call out where support-only or reference-only project-map artifacts still help continuity without becoming the primary runtime read path.]

## Where To Read Next

- [If you need to add or extend a capability, point to the topical file most
  likely to contain ownership, placement, and verification guidance.]
- [If you need to debug or extend an existing capability, route first through `By Symptom` or `By Capability`, then the matching deep workflow page.]
- [If you need API or protocol details, route to the relevant integration or
  workflow sections.]

## Topic Map

- `DEBUG-HANDBOOK.md` - canonical runtime handbook for `sp-debug`
- `BUILD-HANDBOOK.md` - canonical runtime handbook for the major non-debug workflows
- `.specify/project-map/index/status.json` - handbook freshness plus refresh-state truth source
- `.specify/project-map/scan-packets/` and `.specify/project-map/worker-results/` - refresh workbench artifacts for rebuilding the handbooks
- support-only project-map exports - continuity and tooling surfaces that should not become the primary runtime read path again

## Update Triggers

- [When structure, ownership, interfaces, workflows, or runtime assumptions change]

## Recent Structural Changes

- [Short rolling summary]
