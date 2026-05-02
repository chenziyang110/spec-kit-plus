# Architecture

**Last Updated:** YYYY-MM-DD
**Coverage Scope:** repository-wide conceptual architecture
**Primary Evidence:** src/, templates/, tests/, README.md
**Update When:** layers, abstractions, boundaries, or truth ownership change

## Pattern Overview

[Name the top-level architecture pattern, deployment shape, and major module dependencies. If concurrent feature lanes exist, record lanes as the execution-isolation boundary and note whether lane state is durable, rebuildable, or both.]

## High-Value Capabilities

[Summarize the major capabilities and which subsystem owns each one.]

## Layers

## Core Abstractions

## Key Components and Responsibilities

[List the most important components and include any core classes, interfaces, abstract types, enums, or major functions that drive behavior or verification.]

### Capability: <name>

[Use this card to capture owner, truth lives, extend here, minimum verification, failure modes, and confidence.]
[Confidence must use only: Verified / Inferred / Unknown-Stale.]

- Purpose:
- Owner:
- Truth lives:
- Entry points:
- Upstream inputs:
- Downstream consumers:
- Extend here:
- Do not extend here:
- Key contracts:
- Change propagation:
- Minimum verification:
- Failure modes:
- Confidence:

## Dependency Graph and Coupling Hotspots

[Capture dependency direction, shared abstractions, coupling hotspots, and blast radius for the most important architectural surfaces.]

## Main Flows

## Change Propagation Paths

## Internal Boundaries and Critical Seams

## Ownership and Truth Map

## Truth Ownership and Boundaries

## Decision and Evolution Links

[Link important components or boundaries back to ADRs, compatibility promises, migration history, or other decision records when those facts explain why the architecture looks this way.]

## Cross-Cutting Concerns

## Known Architectural Unknowns
