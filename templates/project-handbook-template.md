# Project Handbook

**Last Updated:** YYYY-MM-DD
**Purpose:** Root navigation artifact for this repository.

## System Summary

[What this project is, its primary runtime shape, its major layers or runtime
units, and the main capability surfaces that planners or implementers must keep
in view.]

[Cover the project type, primary technology stack, build/dependency tooling, and deployment shape. Name the major capability surfaces, runtime units, and architectural boundaries that downstream readers must understand first.]

## High-Value Capabilities

- [List the highest-value capabilities a newcomer should understand first.]
- [For each capability, state why it matters and which topical file should be
  read next.]

## How To Read This Project

- Start here for orientation.
- The handbook is the index-first entrypoint.
- The topical project-map documents hold the full technical detail.
- Use `Topic Map` to choose the next topical document.
- Use `Where To Read Next` for task-oriented routing.
- Fall back to live code reads only when the topical coverage is missing, stale, or too broad.
- Point to the topic docs instead of duplicating deep detail when the
  explanation belongs in a topical file.

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

## Where To Read Next

- [If you need to add or extend a capability, point to the topical file most
  likely to contain ownership, placement, and verification guidance.]
- [If you need API or protocol details, route to the relevant integration or
  workflow sections.]

## Topic Map

- `.specify/project-map/ARCHITECTURE.md` - layers, abstractions, truth ownership
- `.specify/project-map/STRUCTURE.md` - where code lives and where to add new code
- `.specify/project-map/CONVENTIONS.md` - naming, imports, error handling, style
- `.specify/project-map/INTEGRATIONS.md` - external tools, env, runtime dependencies
- `.specify/project-map/WORKFLOWS.md` - user flows, maintainer flows, workflow risks
- `.specify/project-map/TESTING.md` - test layers and smallest meaningful checks
- `.specify/project-map/OPERATIONS.md` - startup, recovery, troubleshooting, operator notes

## Update Triggers

- [When structure, ownership, interfaces, workflows, or runtime assumptions change]

## Recent Structural Changes

- [Short rolling summary]
