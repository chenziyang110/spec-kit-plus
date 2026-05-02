# Project-To-PRD Workflow Design

**Date:** 2026-05-02
**Status:** Proposed
**Scope:** New `sp-prd` workflow, generated workflow templates, project-context routing, PRD evidence extraction, master-pack synthesis, export document templates, and workflow-state integration
**Primary goal:** Turn an existing software project into a professional, delivery-grade PRD suite by extracting current-state product truth from repository evidence, then exporting audience-specific views from one unified master pack

## Problem

Spec Kit Plus already has strong workflows for:

- turning a new or changed request into a specification package
- turning a specification package into an implementation plan
- breaking plans into execution-ready tasks
- routing brownfield work through handbook and project-map context

What it does not currently have is a first-class workflow for the opposite direction:

- starting from an existing project
- reading code, docs, routes, UI, APIs, config, tests, and terminology
- reconstructing the current product or service shape
- producing a complete PRD suite that can be used externally as product documentation and internally as planning or UI-design input

Today that job is either manual or handled informally by ad hoc analysis. The failure modes are predictable:

- the result is a single long narrative doc instead of a professional document set
- UI, service, data, and rule views drift because they do not share one truth source
- repository facts and inferred product meaning are mixed together with no confidence marking
- existing capabilities, screens, rules, or states are omitted because there is no coverage model
- the output looks like a PRD, but it is really a partial summary of the codebase

The product therefore needs a dedicated workflow that treats "existing project -> professional PRD suite" as a first-class operating mode.

## Goals

- Add a new independent `sp-prd` workflow for reverse-extracting a current-state PRD suite from an existing project.
- Support both external-facing PRD delivery and internal product-planning / UI-design reuse.
- Make repository evidence the primary truth source.
- Allow professional gap-filling when evidence is incomplete, but mark every consequential conclusion as `Evidence`, `Inference`, or `Unknown`.
- Produce a unified master pack first, then export audience-specific document views from that master pack.
- Support UI-heavy projects, service-heavy projects, and mixed projects through one workflow.
- Reuse existing Spec Kit Plus brownfield context discipline: handbook, project-map, memory, workflow-state, and staged artifact generation.
- Make completeness auditable through coverage matrices, traceability, and export checks rather than trusting prose quality alone.

## Non-Goals

- This workflow does not replace `sp-specify` as the mainline "new change request -> spec" path.
- This workflow does not default to future-state product redesign or product strategy invention.
- This workflow does not directly implement code changes.
- This workflow does not default to high-fidelity visual design output.
- This workflow does not guarantee that missing business intent can be recovered from every repository; unknowns must remain explicit when the evidence is insufficient.
- This workflow does not automatically hand off into implementation planning. Its default terminal state is a completed PRD suite.

## User-Approved Decisions

The design reflects the following explicit decisions made during design review:

1. The workflow should serve both external PRD output and internal planning / UI-design use.
2. The workflow should prioritize producing a complete PRD suite rather than optimizing around a specific usage ceremony.
3. The default delivery should be a delivery-grade full package rather than a minimal PRD.
4. The primary truth source should be the existing codebase and project assets, not the user's one-line prompt.
5. The default posture should be current-state reconstruction rather than target-state redesign.
6. The workflow should detect project type and branch between UI-oriented and service-oriented output modes when needed.
7. When evidence is incomplete, the workflow should use repository-backed professional inference, but inference must be clearly marked instead of being silently merged into fact.
8. The overall structure should be one unified truth source with multiple exported views, not separate manually maintained document sets.
9. The implementation shape should favor high quality over minimal surface simplicity.

## Decision Summary

Introduce a new independent workflow named `sp-prd` that performs:

1. project-type classification
2. brownfield context loading
3. repository evidence harvesting
4. product-semantic reconstruction
5. unified master-pack synthesis
6. multi-view PRD export

The workflow should produce a two-layer artifact model:

- a workflow artifact layer for evidence, state, reconstruction, and traceability
- an export layer for reader-facing PRD documents

The master pack is the only truth source. Exported documents must be derived from it rather than written independently.

## Approaches Considered

### Approach A: Direct document generator

Run one command that scans the repository and writes finished PRD documents directly.

**Pros**

- smallest apparent user surface
- fast path to visible output

**Cons**

- weak traceability
- easy to omit screens, rules, or service surfaces
- no stable place for evidence or inference tracking
- high risk of cross-document inconsistency

**Decision**

Rejected. This would produce attractive documents without a strong completeness model.

### Approach B: Workflow artifact pack only

Create a rigorous brownfield extraction workspace, but do not produce polished delivery documents by default.

**Pros**

- strongest internal rigor
- best support for iteration and resume

**Cons**

- poor "finished PRD suite" operator experience
- weak external deliverable value without another manual pass

**Decision**

Rejected as the default product shape. Good internal mechanics, incomplete final outcome.

### Approach C: Unified master pack plus exported views

First build a rigorous evidence-backed master pack, then export reader-facing PRD views from that pack.

**Pros**

- preserves rigor and traceability
- supports both external and internal consumers
- allows UI-mode and service-mode exports from one truth source
- best fit for "complete and professional" output expectations

**Cons**

- larger design and implementation surface
- requires explicit export completeness checks

**Decision**

Accepted.

## Workflow Positioning

`sp-prd` should be a peer workflow to the existing mainline, not a new mandatory entry stage inside `specify -> plan`.

The workflow split becomes:

- `sp-specify`: new or changed requirement -> planning-ready specification package
- `sp-prd`: existing project -> current-state PRD suite

This distinction matters because the primary source of truth differs:

- `sp-specify` starts from requested change intent
- `sp-prd` starts from current repository reality

## Primary Workflow Contract

### When To Use

Use `sp-prd` when an existing repository needs to be reverse-extracted into a professional PRD suite grounded in current implementation reality.

### Primary Objective

Produce a delivery-grade PRD suite from an existing project by extracting repository-backed product truth, clearly separating evidence from inference and unknowns.

### Primary Outputs

- `.specify/prd-runs/<run-id>/workflow-state.md`
- `.specify/prd-runs/<run-id>/coverage-matrix.md`
- `.specify/prd-runs/<run-id>/evidence/**`
- `.specify/prd-runs/<run-id>/master/**`
- `.specify/prd-runs/<run-id>/exports/**`

### Default Terminal State

Completed PRD suite export. No automatic handoff into implementation planning.

## Architecture Overview

The workflow has four logical layers.

### 1. Routing and State Layer

This layer decides:

- whether the request is an existing-project PRD extraction problem
- which project mode applies: `ui`, `service`, or `mixed`
- where the run artifacts live
- how the workflow is resumed after interruption

It reuses:

- `PROJECT-HANDBOOK.md`
- project-map freshness and routing
- passive project memory
- `workflow-state.md`

### 2. Evidence Layer

This layer gathers repository truth without prematurely collapsing it into polished prose.

It extracts:

- repository surfaces
- UI surfaces
- service surfaces
- entities and models
- business rules
- integrations
- terminology

### 3. Master-Pack Layer

This is the semantic reconstruction layer. It converts evidence into structured product truth:

- roles
- capabilities
- surfaces
- flows
- entities
- rules
- integrations
- evidence map
- inference log
- unknown register

This layer is the only truth source for exports.

### 4. Export Layer

This layer creates audience-specific documents from the master pack:

- `prd.md`
- `ui-spec.md`
- `service-spec.md`
- `flows-and-ia.md`
- `capability-and-api-flows.md`
- `data-rules-appendix.md`
- `internal-implementation-brief.md`
- optional `wireframes/`

## Recommended Workflow Phases

The workflow should be explicitly staged instead of acting like one monolithic scan.

### Phase 0: Intake and Routing

Responsibilities:

- validate that the request is an existing-project PRD extraction task
- create a PRD run workspace
- initialize `workflow-state.md`
- identify available evidence surfaces
- choose the candidate export track: UI, service, or mixed

Output artifacts:

- `intake.md`
- initial `workflow-state.md`

### Phase 1: Atlas Context Load

Responsibilities:

- read `PROJECT-HANDBOOK.md`
- read the smallest relevant project-map topics
- read shared project memory
- identify owning modules, truth surfaces, reusable terminology, and likely hotspot areas

Output artifacts:

- context notes folded into `intake.md` or a dedicated atlas summary section

### Phase 2: Evidence Harvest

Responsibilities:

- inspect high-value repository surfaces
- separate direct evidence from interpretation
- populate evidence files rather than directly authoring the PRD prose

Output artifacts:

- `evidence/repo-surfaces.md`
- `evidence/ui-surfaces.md`
- `evidence/service-surfaces.md`
- `evidence/entities-and-models.md`
- `evidence/business-rules.md`
- `evidence/integrations.md`
- `evidence/terminology.md`

### Phase 3: Capability Reconstruction

Responsibilities:

- rebuild product semantics from evidence
- infer roles, capabilities, flows, and domain objects where possible
- log all professional inference separately

Output artifacts:

- `master/capability-index.md`
- `master/screen-service-inventory.md`
- `master/flow-index.md`
- `master/data-rule-index.md`
- `master/inference-log.md`
- `master/unknowns-register.md`

### Phase 4: Master-Pack Synthesis

Responsibilities:

- assemble one coherent truth source
- ensure terminology, capability names, scope boundaries, and rule language are consistent
- prepare export manifests

Output artifacts:

- `master/master-pack.md`
- `master/evidence-map.md`
- `master/export-manifest.md`

### Phase 5: View Export

Responsibilities:

- export reader-facing documents from the master pack
- tailor output to project mode
- run completeness checks before marking the suite complete

Output artifacts:

- `exports/prd.md`
- project-mode-specific exports

## Artifact Model

The workflow should use a two-layer artifact structure: durable workflow artifacts plus delivery exports.

Suggested layout:

```text
.specify/prd-runs/<date>-<project-slug>/
  workflow-state.md
  intake.md
  classification.md
  coverage-matrix.md
  evidence/
    repo-surfaces.md
    ui-surfaces.md
    service-surfaces.md
    entities-and-models.md
    business-rules.md
    integrations.md
    terminology.md
  master/
    master-pack.md
    capability-index.md
    screen-service-inventory.md
    flow-index.md
    data-rule-index.md
    evidence-map.md
    inference-log.md
    unknowns-register.md
    export-manifest.md
  exports/
    prd.md
    ui-spec.md
    service-spec.md
    flows-and-ia.md
    capability-and-api-flows.md
    data-rules-appendix.md
    internal-implementation-brief.md
    wireframes/
```

## File Responsibilities

### Root Control Files

#### `workflow-state.md`

Tracks:

- current phase
- project mode
- completed gates
- remaining unknowns
- next safe action
- export completion status

#### `intake.md`

Records:

- user ask
- repository scope
- run assumptions
- excluded areas
- evidence-source notes

#### `classification.md`

Records:

- UI vs service vs mixed decision
- evidence for that decision
- export route selection

#### `coverage-matrix.md`

Controls completeness. This is the explicit "do not omit surfaces silently" ledger.

### Evidence Directory

This directory captures repository fact surfaces before semantic synthesis:

- `repo-surfaces.md`
- `ui-surfaces.md`
- `service-surfaces.md`
- `entities-and-models.md`
- `business-rules.md`
- `integrations.md`
- `terminology.md`

### Master Directory

This directory is the semantic truth source:

- `master-pack.md`
- `capability-index.md`
- `screen-service-inventory.md`
- `flow-index.md`
- `data-rule-index.md`
- `evidence-map.md`
- `inference-log.md`
- `unknowns-register.md`
- `export-manifest.md`

### Export Directory

This directory holds polished reader-facing documents and optional low-fidelity visuals.

## Project Type Classification

`sp-prd` should support three modes:

- `ui`
- `service`
- `mixed`

Classification must be evidence-backed, not purely heuristic narration.

Typical UI indicators:

- route trees
- page components
- navigation structures
- forms, lists, details, dialogs
- visible user-task surfaces

Typical service indicators:

- API handlers
- commands
- jobs and workers
- event consumers
- service orchestration
- runtime config and contract surfaces

Mixed mode applies when a single repository strongly contains both.

## Evidence Priority Model

Not all repository signals should carry equal weight. The workflow should use a stable priority order.

### Tier 1: Runtime and entry-surface evidence

- routes
- pages
- API definitions
- CLI commands
- jobs
- schema wiring
- runtime configuration

### Tier 2: Behavioral evidence

- validation
- permissions
- state branching
- error handling
- side effects
- notifications
- instrumentation

### Tier 3: Verification evidence

- tests
- fixtures
- contract checks
- end-to-end scenarios

### Tier 4: Narrative evidence

- README
- docs
- issues
- comments
- product copy

Lower tiers may clarify meaning, but should not override higher-tier runtime evidence.

## Reconstruction Object Model

The workflow should reconstruct product meaning around stable object types instead of around arbitrary file categories.

Core reconstructed objects:

- `Role`
- `Capability`
- `Surface`
- `Flow`
- `Entity`
- `Rule`
- `Integration`
- `Signal`
- `State`

This makes exports systematic and traceable.

## UI-Mode Extraction Priorities

For UI-heavy repositories, high-value extraction surfaces include:

- route and page trees
- navigation and entry points
- page purposes
- forms, lists, details, dialogs, tabs, wizards
- loading, empty, success, and error states
- search, filter, sort, pagination
- permission differences
- user-task paths

The goal is not to describe implementation widgets exhaustively; it is to recover the actual product surface and behavior.

## Service-Mode Extraction Priorities

For service-heavy repositories, high-value extraction surfaces include:

- API / CLI / job / event entrypoints
- inputs and outputs
- entity changes
- config knobs
- auth, rate-limit, idempotency, retry, and failure behavior
- integration boundaries
- orchestration paths

## Mixed-Mode Handling

Mixed-mode repositories should still use one master pack, not separate truth sources.

A single capability may map to:

- one or more UI screens
- one or more service entrypoints
- shared entities
- shared rules

Exports may branch by audience, but the semantics remain unified.

## Evidence, Inference, and Unknowns

Every consequential conclusion should be classified as one of:

- `Evidence`
- `Inference`
- `Unknown`

### Evidence

Used when the claim is directly supported by repository or artifact proof.

### Inference

Used when:

- repository behavior is clear
- product semantics are incomplete
- a professional reconstruction can be justified from evidence

Every inference must link back to the evidence that enabled it.

### Unknown

Used when:

- the repository does not reliably prove the claim
- a guess would materially reduce trust

Unknowns must remain visible rather than being silently filled.

## Professional Inference Policy

Professional inference is allowed, but only within bounded conditions.

Allowed examples:

- deriving user-task names from consistent UI behavior
- naming a role from permission partitions
- reconstructing page purpose from routes and controls
- describing an entity relationship from stable schema and behavior

Disallowed examples:

- inventing business KPIs
- claiming organizational workflow that the repository does not support
- treating an expected future capability as present
- asserting compliance or SLA guarantees without proof

## Completeness Model

The workflow must not rely on narrative confidence alone. It needs explicit completeness controls.

### 1. Surface Coverage Matrix

The workflow must list the expected surfaces that need review before export.

For UI-oriented work this includes, at minimum:

- routes and pages
- navigation
- forms
- lists and detail views
- states
- auth / permission variation
- error and feedback surfaces

For service-oriented work this includes, at minimum:

- entrypoints
- input/output surfaces
- entities
- config surfaces
- rules
- error branches
- integration boundaries

### 2. Capability Trace Matrix

Each capability should trace to:

- evidence paths
- related screens or services
- related entities or rules
- exported documents where it appears

### 3. Evidence / Inference / Unknown Registry

The master pack must maintain a stable ledger of confidence classifications.

### 4. Export Completeness Check

Before completion, the workflow should verify that:

- every master capability appears in at least one export
- every relevant screen or service surface has a documented home
- rules and entities are not stranded only in evidence notes
- unknowns are retained explicitly where required

## Export Document Set

The export layer should be a document suite, not one overloaded file.

### `prd.md`

Audience:

- stakeholders
- cross-functional readers
- product consumers of the suite

Purpose:

- explain what the project is
- who it serves
- what capabilities exist
- what boundaries and dependencies matter

### `ui-spec.md`

Generated for `ui` and `mixed` projects.

Purpose:

- describe navigational structure
- enumerate pages and user tasks
- document UI states and interaction rules

### `service-spec.md`

Generated for `service` and `mixed` projects.

Purpose:

- describe service capabilities
- document operational entrypoints and flows
- define input/output and operational constraints

### `flows-and-ia.md`

Generated for UI and mixed mode when information architecture matters.

Purpose:

- capture page trees
- task flows
- structural navigation and transitions

### `capability-and-api-flows.md`

Generated for service and mixed mode when service or API flow clarity matters.

Purpose:

- capture capability paths
- invocation or event chains
- operational transitions

### `data-rules-appendix.md`

Purpose:

- centralize entities
- fields
- state rules
- validation rules
- permission rules
- terminology

### `internal-implementation-brief.md`

Purpose:

- map product semantics back to repository structure
- highlight hotspots, risk areas, and verification clues
- serve as an internal bridge to later planning or redesign work

### Optional `wireframes/`

These should remain low-fidelity structural outputs, not polished visual design.

## Suggested Export Structures

### `prd.md`

Recommended sections:

- document summary
- product overview
- users and roles
- scope and boundaries
- capability overview
- key flows
- rule summary
- dependency summary
- unknowns and evidence confidence
- appendix navigation

### `ui-spec.md`

Recommended sections:

- UI scope
- role visibility
- navigation model
- page inventory
- page-by-page responsibilities
- interaction rules
- states and permission differences
- UI unknowns

### `service-spec.md`

Recommended sections:

- service scope
- capability inventory
- entrypoint inventory
- capability details
- runtime and dependency constraints
- service flows
- failure paths
- service unknowns

### `data-rules-appendix.md`

Recommended sections:

- entities
- fields and relationships
- state model
- validation rules
- permission rules
- config surfaces
- terminology
- evidence / inference notes

### `internal-implementation-brief.md`

Recommended sections:

- scope summary
- capability-to-module mapping
- screen/service-to-code mapping
- risk areas
- testing or verification clues
- planning handoff notes

## Quality Gates

The workflow should fail closed when rigor conditions are not satisfied.

### Gate 1: Routing Gate

Confirm this is an existing-project reverse-PRD task. If the user only has a new idea and no current project surface, route elsewhere.

### Gate 2: Classification Gate

The project must be classified as UI, service, or mixed with evidence-backed reasoning.

### Gate 3: Surface Coverage Gate

The coverage matrix must exist and cover the major expected surfaces for the selected project mode.

### Gate 4: Semantic Reconstruction Gate

The workflow must produce roles, capabilities, flows, surfaces, entities, rules, and integrations in the master layer. A repository scan summary alone is insufficient.

### Gate 5: Export Completeness Gate

The workflow must verify that all core master semantics appear in the exported suite.

### Gate 6: Confidence Marking Gate

Consequential conclusions must be explicitly marked as `Evidence`, `Inference`, or `Unknown`.

## Completion Criteria

`sp-prd` is complete only when all of the following are true:

- project mode is classified
- coverage matrix exists and is materially complete
- evidence files are populated for relevant surfaces
- master pack is synthesized
- evidence, inference, and unknown ledgers exist
- export documents for the selected mode are generated
- export completeness checks pass
- no unresolved placeholders or contradictory sections remain in the suite

## Failure and Recovery Model

The workflow should support partial progress and explicit uncertainty.

If evidence is incomplete but the suite can still be responsibly exported:

- continue export
- preserve unknowns
- preserve inference labels

If repository coverage is too weak to responsibly reconstruct core semantics:

- stop before claiming completion
- remain in evidence or coverage phases
- record the blocker in `workflow-state.md`

Interrupted runs should resume from `workflow-state.md` rather than relying on chat memory alone.

## Relationship To Existing Spec Kit Plus Surfaces

`sp-prd` should reuse:

- handbook and project-map routing
- passive learning / project memory
- workflow-state discipline
- staged artifact generation
- brownfield context gate behavior

`sp-prd` should not:

- replace `sp-specify`
- automatically continue into `sp-plan`
- force the mainline `specify -> plan` path to absorb PRD extraction semantics

## Downstream Uses

Although `sp-prd` should terminate at PRD suite delivery, its outputs can become inputs for later flows.

Examples:

- current-state baseline before future change specification
- UI redesign preparation
- service modernization planning
- stakeholder-facing product documentation
- onboarding documentation for operators or internal teams

## Rollout Guidance

The first implementation slice should optimize for:

- rigorous current-state extraction
- stable artifact model
- UI / service / mixed routing
- traceable export generation

It should avoid:

- premature high-fidelity visual generation
- target-state redesign features
- excessive integration-specific behavior in the core workflow contract

## Final Recommendation

Ship `sp-prd` as a new independent workflow with these defaults:

- current-state reconstruction
- repository evidence first
- professional inference allowed but explicitly marked
- unified master pack as the truth source
- UI / service / mixed export modes
- completed PRD suite as the default terminal outcome

That is the most defensible way to satisfy the requirement for a professional, complete, 1:1 PRD suite generated from an existing project without silently inventing product truth.
