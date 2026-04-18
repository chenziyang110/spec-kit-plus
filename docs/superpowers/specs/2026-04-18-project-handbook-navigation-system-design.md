# Project Handbook Navigation System Design

**Date:** 2026-04-18
**Status:** Proposed
**Owner:** Codex

## Summary

This design replaces the current single-file brownfield scout model centered on `项目技术文档.md` with a workflow-owned navigation system built for progressive disclosure.

The approved direction is:

- keep one stable root entrypoint for both humans and agents
- split deep project knowledge into fixed topical documents instead of one growing document
- make the navigation system a first-class internal dependency of `specify` workflows
- require navigation updates whenever code changes alter structure, ownership, interfaces, workflows, or operational expectations

The design keeps the value of a repository-level "project manual" while removing the weaknesses of a monolithic document: topic drift, stale sections, poor routing, and weak touched-area coverage.

## Problem Statement

The current model treats `项目技术文档.md` as both:

- a required workflow dependency
- and a single container for all project understanding

That creates four problems:

1. The workflows already rely on it as a core scout artifact, so it is not truly optional or external.
2. A single document naturally drifts toward the most recently changed subsystem instead of staying balanced across the whole project.
3. Fast and targeted workflows need different levels of detail, but a monolithic document cannot support lightweight routing and deep analysis equally well.
4. There is no strong product-level contract for freshness, topical coverage, or update triggers.

The result is a hard dependency with soft quality control.

## Reference Analysis: `get-shit-done`

`get-shit-done` does not rely on one giant architecture note. It uses a layered navigation model:

- a stable high-level system document in `docs/ARCHITECTURE.md`
- project and milestone state artifacts such as `PROJECT.md` and `ROADMAP.md`
- specialized brownfield mapping artifacts under `.planning/codebase/`

The important lessons are:

1. Use one stable entrypoint for orientation.
2. Split detailed understanding by topic.
3. Give each topic document a clear purpose and update trigger.
4. Let workflows detect and rely on these artifacts as internal state, not as external reference material.

This design applies those ideas to `spec-kit-plus` while preserving `specify`'s command model and artifact layout.

## Goals

- Establish a workflow-owned project navigation system for all relevant `specify` workflows.
- Support progressive disclosure: shallow overview first, topic drill-down second, live code reads only when needed.
- Give `sp-specify` enough structured context to support brownfield alignment with high confidence.
- Keep `sp-fast` lightweight while still giving it a safe routing layer.
- Support `sp-quick` and `sp-debug` without forcing them to read a full architecture package every time.
- Make update obligations explicit whenever repository changes affect navigation semantics.
- Use ASCII filenames for the primary entrypoint to avoid cross-runtime encoding friction.

## Non-Goals

- Do not turn the navigation system into a second planning system.
- Do not duplicate `spec.md`, `alignment.md`, `context.md`, or `plan.md`.
- Do not require every workflow to read every topical document on every invocation.
- Do not preserve `项目技术文档.md` as the long-term primary artifact.
- Do not let the navigation system become a narrative changelog.

## Alternatives Considered

### Option A: Keep a single monolithic file and improve its template

Pros:

- minimal implementation change
- backward compatibility is simple

Cons:

- still drifts toward recently touched subsystems
- hard to support fast-path and deep-path workflows equally well
- weak progressive disclosure

Decision:

- rejected

### Option B: One root handbook plus fixed topical documents

Pros:

- supports progressive disclosure
- clear routing for fast, quick, debug, and deep planning workflows
- easier freshness and coverage checks
- aligns with the layered artifact model seen in `get-shit-done`

Cons:

- requires template, workflow, and test updates

Decision:

- approved

### Option C: Topic directory only, no single entry document

Pros:

- clean separation of topics

Cons:

- no stable first-read artifact
- higher entry cost for both humans and agents

Decision:

- rejected

## Approved Architecture

The navigation system has two layers:

1. A stable root entrypoint:
   - `PROJECT-HANDBOOK.md`
2. A fixed topical map:
   - `.specify/project-map/*.md`

The handbook is the routing layer. The topical documents are the depth layer.

## Artifact Model

### Root Entry Artifact

`PROJECT-HANDBOOK.md`

Purpose:

- first-read entrypoint for project orientation
- routing guide for where to look next
- summary of shared surfaces and risky coordination points
- compact update contract for future changes

This file must stay concise enough for fast-path workflows.

### Topical Artifacts

The initial fixed set is:

- `.specify/project-map/ARCHITECTURE.md`
- `.specify/project-map/STRUCTURE.md`
- `.specify/project-map/CONVENTIONS.md`
- `.specify/project-map/INTEGRATIONS.md`
- `.specify/project-map/WORKFLOWS.md`
- `.specify/project-map/TESTING.md`
- `.specify/project-map/OPERATIONS.md`

These files are shared project artifacts, not feature artifacts.

## Root Handbook Template

`PROJECT-HANDBOOK.md` should use this fixed structure:

### 1. System Summary

- what the repository is
- primary runtime or product shape
- major layers in one short block

### 2. How To Read This Project

- where a new reader should start
- when to use topical docs
- when workflows should fall back to live code reads

### 3. Shared Surfaces

- registries
- template directories
- command routing files
- exported contracts
- config schemas

This section exists mainly to help `sp-fast` and `sp-quick` detect when work is not truly local.

### 4. Risky Coordination Points

- files or modules that can silently affect many flows
- cross-integration touchpoints
- state or runtime boundaries

### 5. Topic Map

For each topical file:

- file path
- what questions it answers
- when to read it

### 6. Update Triggers

- what kinds of repository changes require handbook or topical updates

### 7. Recent Structural Changes

- short rolling summary of the latest navigation-relevant changes
- not a full changelog

## Topical File Templates

Every topical document must start with the same metadata block:

```markdown
# [Topic Name]

**Last Updated:** YYYY-MM-DD
**Coverage Scope:** [what area this document covers]
**Primary Evidence:** [main files, directories, commands, or tests used]
**Update When:** [what changes should trigger edits here]
```

This metadata is required so workflows can reason about freshness and coverage.

### `ARCHITECTURE.md`

Must answer:

- what the major conceptual layers are
- what owns truth for key decisions or state
- what the main data or control flows are
- what abstractions and boundaries matter

Suggested fixed sections:

- Pattern Overview
- Layers
- Core Abstractions
- Main Flows
- Truth Ownership and Boundaries
- Cross-Cutting Concerns

### `STRUCTURE.md`

Must answer:

- where code lives
- what each major directory owns
- where new code should go
- what shared write surfaces exist

Suggested fixed sections:

- Directory Layout
- Directory Responsibilities
- Key File Locations
- Shared Coordination Files
- Where To Add New Code

### `CONVENTIONS.md`

Must answer:

- how code is written in this repository
- naming and import rules
- error handling norms
- documentation and test conventions

Suggested fixed sections:

- Naming Patterns
- Formatting and Linting
- Imports and Exports
- Error Handling
- Comments and Docs
- Testing Conventions

### `INTEGRATIONS.md`

Must answer:

- what external tools, services, and environments this repository depends on
- what configuration or credentials matter
- what CI/CD or runtime assumptions exist

Suggested fixed sections:

- External Services and Tools
- Environment Configuration
- CI/CD and Release Surfaces
- Runtime Dependencies
- Integration Risks

### `WORKFLOWS.md`

Must answer:

- what the important user or maintainer flows are
- what adjacent flows can be accidentally broken
- what command or workflow boundaries exist

Suggested fixed sections:

- Core User Flows
- Core Maintainer Flows
- Adjacent Workflow Risks
- Entry Commands and Handoffs

### `TESTING.md`

Must answer:

- how testing is structured
- what the minimum useful verification steps are
- where regression-sensitive areas live

Suggested fixed sections:

- Test Layers
- Key Test Directories
- Smallest Meaningful Checks
- Regression-Sensitive Areas
- When To Expand Verification

### `OPERATIONS.md`

Must answer:

- how to run, resume, inspect, and recover the system
- what operational or runtime caveats exist
- what health or recovery paths matter

Suggested fixed sections:

- Startup and Execution Paths
- Runtime Constraints
- Recovery and Resume
- Troubleshooting Entry Points
- Operator Notes

## Workflow Read Contracts

The navigation system is shared across workflows, but each workflow reads it differently.

### `sp-specify`

Must:

- read `PROJECT-HANDBOOK.md` first
- read touched-area topical files next
- use the topic map to route clarification and codebase scout work
- fall back to live repository reads only when the topical coverage is missing, stale, or too broad

### `sp-plan`

Must:

- read `PROJECT-HANDBOOK.md`
- prioritize `ARCHITECTURE.md`, `STRUCTURE.md`, `INTEGRATIONS.md`, and `WORKFLOWS.md`
- use these artifacts to anchor design choices, constraints, and plan structure

### `sp-tasks`

Must:

- read `PROJECT-HANDBOOK.md`
- prioritize `WORKFLOWS.md`, `TESTING.md`, and `CONVENTIONS.md`
- use these artifacts to shape execution order, validation, and coordination tasks

### `sp-implement`

Must:

- read `PROJECT-HANDBOOK.md`
- prioritize `STRUCTURE.md`, `CONVENTIONS.md`, `TESTING.md`, and `OPERATIONS.md`
- use them to prevent incorrect placement, style drift, validation gaps, or unsafe runtime assumptions

### `sp-quick`

Must:

- read `PROJECT-HANDBOOK.md`
- read only the touched-area topical files needed for the bounded quick task
- avoid full-map loading unless the task expands

This keeps quick mode lightweight while still giving it a shared navigation contract.

### `sp-fast`

Must:

- read only the lightweight routing portion of `PROJECT-HANDBOOK.md`
- use `Shared Surfaces` and `Risky Coordination Points` to determine whether the task is truly fast-path work

If the requested change touches a shared surface or risky coordination point, the workflow should escalate to `sp-quick` immediately.

### `sp-debug`

Must:

- read `PROJECT-HANDBOOK.md`
- read whichever of `ARCHITECTURE.md`, `WORKFLOWS.md`, `INTEGRATIONS.md`, `TESTING.md`, and `OPERATIONS.md` map to the failing area
- use the navigation system to identify truth-owning layers, adjacent flows, and observability entrypoints

This makes the debug workflow better at locating the real ownership boundary before forming a hypothesis.

## Update Contract

The navigation system must be updated whenever a change affects:

- directory structure
- module ownership
- shared registries or coordination files
- command routing
- interface or contract shape
- configuration shape
- external integrations
- testing strategy or regression-sensitive areas
- runtime constraints or operator expectations
- recovery, startup, or release behavior

This rule applies whether or not the repository change was made through `sp-specify`.

In other words:

- code changes may bypass the full spec workflow
- navigation updates may not be bypassed when the navigation meaning changed

## Validation Rules

The workflow should eventually validate the navigation system on five axes:

1. Existence
   - required files exist
2. Routing quality
   - the handbook points to the right topical files
3. Freshness
   - topical files have valid metadata and recent update context
4. Coverage
   - touched areas are represented by at least one relevant topical document
5. Consistency
   - paths, commands, file names, and responsibilities match the live repository

## Migration Plan

### Phase 1: Introduce the new system

- add `PROJECT-HANDBOOK.md`
- add `.specify/project-map/` templates
- keep `项目技术文档.md` temporarily for compatibility

### Phase 2: Rewire workflows

- update `sp-specify`, `sp-plan`, `sp-tasks`, `sp-implement`
- extend `sp-quick`, `sp-fast`, and `sp-debug` with read contracts appropriate to their scope

### Phase 3: Compatibility bridge

During migration, `项目技术文档.md` should become a short bridge artifact rather than the primary source of truth.

Its role should be:

- point to `PROJECT-HANDBOOK.md`
- point to `.specify/project-map/`
- avoid carrying independent technical truth

This prevents dual source-of-truth drift.

### Phase 4: Remove the old hard-coded dependency

Once all templates, skills, and tests target the new system:

- remove direct hard-coded dependence on `项目技术文档.md`
- keep only the handbook and project-map artifacts as the canonical navigation system

## Consequences

### Positive

- better progressive disclosure
- better fit for fast, quick, debug, and deep planning workflows
- less topic drift than the current single-file model
- stronger workflow semantics around coverage and freshness
- cleaner ASCII-first primary entrypoint

### Costs

- more templates and workflow instructions to maintain
- migration effort across templates, mirrored skills, and tests
- need for new validation rules so the topical set stays coherent

## Open Implementation Questions

These are implementation questions, not design blockers:

1. Should the project-map templates live only under `templates/` and be copied into initialized repos, or also exist in `.specify/templates/` as mirrored runtime assets?
2. Should `Recent Structural Changes` in `PROJECT-HANDBOOK.md` be capped to a rolling window by count or by age?
3. Should validation treat missing touched-area topical coverage as a warning in `sp-fast`/`sp-quick` but as a harder failure in `sp-specify`/`sp-plan`?

## Approved Direction

The approved design is:

- replace the monolithic `项目技术文档.md` dependency with a workflow-owned navigation system
- use `PROJECT-HANDBOOK.md` as the stable root entrypoint
- use `.specify/project-map/*.md` as the fixed topical depth layer
- apply read contracts across `sp-specify`, `sp-plan`, `sp-tasks`, `sp-implement`, `sp-quick`, `sp-fast`, and `sp-debug`
- require navigation updates whenever repository changes alter navigation meaning

This turns project navigation into a first-class internal workflow artifact instead of an oversized supplemental document.
