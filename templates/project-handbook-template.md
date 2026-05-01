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
- **First stop for any task**: open `.specify/project-map/QUICK-NAV.md` — a concise Layer 1 routing table that answers "which document should I open?"
- The handbook is the index-first entrypoint.
- Read `.specify/project-map/index/atlas-index.json` and `.specify/project-map/index/status.json` before broad brownfield work.
- Treat the combined handbook/project-map set as the repository's atlas-style technical encyclopedia.
- The topical project-map documents hold the full technical detail.
- Use `Topic Map` to choose the next topical document.
- Use `Where To Read Next` for task-oriented routing.
- Fall back to live code reads only when the topical coverage is missing, stale, or too broad.
- Point to the topic docs instead of duplicating deep detail when the
  explanation belongs in a topical file.

## Quick Navigation (Layer 1)

Describe the four-layer atlas explicitly:

- **Layer 1 (routing)**: `QUICK-NAV.md` — task-to-document routing
- **Layer 2 (summary)**: `root/ARCHITECTURE.md` capability cards and root topical summaries
- **Layer 3 (detail)**: `modules/<module-id>/OVERVIEW.md` plus module-local docs
- **Layer 4 (source)**: live code and runtime state when the atlas is missing, stale, or too broad

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

- [Summarize which topical documents answer structure, runtime flow, state lifecycle,
  deployment topology, observability, security, release, and verification questions.]

## Where To Read Next

- [If you need to add or extend a capability, point to the topical file most
  likely to contain ownership, placement, and verification guidance.]
- [If you need API or protocol details, route to the relevant integration or
  workflow sections.]

## Topic Map

- `.specify/project-map/QUICK-NAV.md` - Layer 1 routing table for the four-layer atlas
- `.specify/project-map/index/atlas-index.json` - atlas entry summary and the next machine-readable lookup step
- `.specify/project-map/index/modules.json` - module registry, owned roots, and module document paths
- `.specify/project-map/index/relations.json` - cross-module dependencies, shared surfaces, and expansion routes
- `.specify/project-map/index/status.json` - atlas freshness plus module and deep staleness state
- `.specify/project-map/root/ARCHITECTURE.md` - layers, abstractions, truth ownership, and cross-module seams
- `.specify/project-map/root/STRUCTURE.md` - global structure, shared directories, and placement rules
- `.specify/project-map/root/CONVENTIONS.md` - repository-wide conventions and contract rules
- `.specify/project-map/root/INTEGRATIONS.md` - external tools, env, runtime dependencies, and trust boundaries
- `.specify/project-map/root/WORKFLOWS.md` - user flows, maintainer flows, and cross-module workflow risks
- `.specify/project-map/root/TESTING.md` - root verification strategy and shared regression-sensitive surfaces
- `.specify/project-map/root/OPERATIONS.md` - startup, recovery, troubleshooting, operator notes, and runtime invariants
- `.specify/project-map/modules/<module-id>/OVERVIEW.md` - module-local routing, ownership, and next reads

## Update Triggers

- [When structure, ownership, interfaces, workflows, or runtime assumptions change]

## Recent Structural Changes

- [Short rolling summary]
