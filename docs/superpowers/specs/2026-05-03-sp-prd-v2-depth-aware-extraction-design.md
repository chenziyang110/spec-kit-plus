# sp-prd v2 Depth-Aware Extraction Design

**Date:** 2026-05-03
**Status:** Proposed
**Scope:** `sp-prd` workflow contract, evidence-harvest strategy, coverage semantics, master-pack structure, quality gates, and rollout sequencing
**Primary goal:** Upgrade `sp-prd` from a general current-state PRD extractor into a depth-aware workflow that can distinguish between surface coverage and implementation-grade reconstruction for product-critical capabilities

## Problem

The first `sp-prd` design established the correct workflow position:

- it is a peer workflow to `sp-specify`
- it starts from current repository reality
- it builds a master pack before exporting reader-facing PRD views
- it preserves `Evidence`, `Inference`, and `Unknown`

That baseline is directionally correct, but it still permits a failure mode that is unacceptable for repositories whose value depends on non-trivial internal mechanisms:

- repository surfaces can appear "covered" while the product's core implementation logic is still under-described
- capability inventories can flatten cross-cutting core behavior into shallow feature labels
- configuration or protocol details can be described incorrectly because the workflow only observed file paths or naming, not parsing and write logic
- export completeness can report success even when critical mechanisms, edge cases, and semantic-preservation rules are missing

The result is a PRD suite that looks complete but is only surface-complete. That is the specific defect this v2 design addresses.

## Goals

- Preserve the current positioning of `sp-prd` as an independent current-state PRD workflow.
- Keep `master/master-pack.md` as the only truth source for exports.
- Add an explicit capability-depth model so core product capabilities receive deeper reconstruction than ordinary supporting surfaces.
- Distinguish "mentioned in evidence" from "reconstructed with sufficient implementation depth".
- Add compatibility-safe quality gates that can block shallow PRD suites without requiring a complete artifact-model rewrite on day one.
- Improve traceability from critical PRD claims back to repository evidence, including function-level references when needed.
- Support phased rollout so workflow contracts can tighten before automation complexity increases.

## Non-Goals

- This design does not turn `sp-prd` into a future-state redesign workflow.
- This design does not automatically hand off to `sp-plan`.
- This design does not require a new autonomous analysis engine in the first implementation slice.
- This design does not require new hard-mandatory artifact files on day one if the same contract can be enforced inside existing artifacts.
- This design does not optimize for research-heavy or benchmark-heavy extraction before the workflow contract itself is stronger.

## User-Approved Direction

This design reflects the following explicit decisions from review:

1. The right direction is a contract upgrade, not a cosmetic patch and not a research-engine-first rebuild.
2. The workflow should first become capable of refusing shallow PRD outputs before adding more automation.
3. The first rollout should be compatibility-oriented and should respect the current artifact-validation surface.
4. The workflow should explicitly identify which capabilities deserve implementation-grade reconstruction before broad evidence harvesting continues.

## Decision Summary

Ship `sp-prd v2` as a depth-aware evolution of the existing workflow.

The two most important changes are:

1. add a new **capability triage** phase between project classification and evidence harvesting
2. add explicit **quality gates** after export generation that distinguish surface coverage from depth-qualified reconstruction

The workflow therefore changes from:

1. route
2. classify
3. harvest evidence
4. synthesize master pack
5. export

to:

1. route and initialize
2. atlas context load
3. project classification
4. capability triage
5. targeted evidence harvest
6. master-pack synthesis
7. export generation
8. quality gates and completion

This preserves the original `sp-prd` shape while fixing the missing "what must be deeply understood before we can claim coverage?" contract.

## Approaches Considered

### Approach A: Minimal output-shape patch

Keep the current workflow structure and only add extra sections to the PRD outputs.

**Pros**

- smallest implementation delta
- fast to ship
- low test churn

**Cons**

- mostly fixes output presentation, not evidence discipline
- does not force earlier recognition of critical cross-cutting capabilities
- still allows shallow evidence collection to masquerade as complete reconstruction

**Decision**

Rejected as insufficient.

### Approach B: Contract-upgrade v2

Keep the existing independent `sp-prd` workflow, but introduce capability triage, depth policy, targeted evidence harvest, and depth-aware quality gates.

**Pros**

- directly addresses the root cause
- preserves existing workflow identity
- compatible with phased rollout
- improves both evidence quality and export reliability

**Cons**

- requires updates to workflow template language, tests, and validation logic
- expands the semantic expectations of the master pack

**Decision**

Accepted.

### Approach C: Analysis-engine-first rebuild

Lead with automated complexity scanning, format inference, similarity matching, and multi-pass evidence loops before tightening the workflow contract.

**Pros**

- strongest eventual automation ceiling
- could reduce some manual reasoning burden later

**Cons**

- attacks the problem at the wrong layer first
- expensive to validate
- easy to overbuild before the workflow has a strong definition of "enough depth"

**Decision**

Rejected for the first rollout.

## Workflow Positioning

`sp-prd v2` remains:

- a peer workflow to `sp-specify`
- a current-state extraction workflow, not a target-state product-design workflow
- a master-pack-first document workflow
- a no-automatic-planning-handoff workflow

The upgrade is about reconstruction depth, not workflow identity.

## v2 Workflow Contract

### When To Use

Use `sp-prd v2` when an existing repository needs a current-state PRD suite and the product's real value depends on mechanisms, rules, formats, compatibility behavior, or cross-cutting logic that cannot be responsibly described from surface inventory alone.

### Primary Objective

Produce a delivery-grade PRD suite whose critical capabilities are reconstructed with enough implementation depth to distinguish verified product truth from shallow summary.

### Primary Outputs

The primary output set remains compatible with the current contract:

- `.specify/prd-runs/<run-id>/workflow-state.md`
- `.specify/prd-runs/<run-id>/coverage-matrix.md`
- `.specify/prd-runs/<run-id>/evidence/**`
- `.specify/prd-runs/<run-id>/master/master-pack.md`
- `.specify/prd-runs/<run-id>/master/exports/**`
- `.specify/prd-runs/<run-id>/exports/prd.md`

Additional control artifacts may be introduced later, but they are not required to be hard-mandatory in the first rollout if their contract can be expressed in the existing artifact set.

## Recommended Workflow Phases

### Phase 0: Route and Initialize

Responsibilities:

- confirm the task is an existing-project PRD extraction request
- create or resume the PRD run workspace
- initialize or update `workflow-state.md`
- record excluded areas, known blockers, and requested scope

### Phase 1: Atlas Context Load

Responsibilities:

- read `PROJECT-HANDBOOK.md`
- consult project-map freshness and the smallest relevant atlas topics
- capture repository-owned terminology and module boundaries that shape later capability reconstruction

### Phase 2: Project Classification

Responsibilities:

- classify the repository as `ui`, `service`, or `mixed`
- record the evidence for that classification
- identify which export families will be mandatory

### Phase 3: Capability Triage

Responsibilities:

- define the product's core value proposition
- identify the repository-backed capability set
- assign each capability to a depth tier
- decide which capabilities require implementation-grade reconstruction before completion can be claimed

This is the first genuinely new phase and the most important one.

### Phase 4: Targeted Evidence Harvest

Responsibilities:

- retain broad surface evidence collection
- deepen collection selectively for triaged `critical` and `high` capabilities
- collect mechanism, format, compatibility, error-path, and edge-case evidence for those capabilities

This phase changes evidence collection from "uniform scan" to "depth-aware harvest".

### Phase 5: Master-Pack Synthesis

Responsibilities:

- assemble one coherent truth source
- represent all capabilities, but give `critical` and `high` capabilities dedicated implementation-level treatment
- preserve evidence, inference, and unknown separation

### Phase 6: Export Generation

Responsibilities:

- generate `exports/prd.md`
- generate UI-oriented or service-oriented exports as the project mode requires
- ensure exports are derived from the master pack rather than carrying independent facts

### Phase 7: Quality Gates and Completion

Responsibilities:

- verify that depth requirements were met for triaged capabilities
- verify source traceability for key mechanisms
- verify export integrity
- block completion when surface coverage exists but critical capability depth does not

## Capability Triage Model

The workflow needs a stable way to say "this repository has many features, but only some of them define what the product fundamentally is."

### Core Principle

Capabilities should be triaged by product significance and reconstruction depth, not only by UI menu structure, endpoint categories, or module names.

### Recommended Capability Tiers

- `critical`: core product-defining capabilities; must be reconstructed with implementation depth
- `high`: major differentiators or high-risk behaviors; must include key mechanisms and failure behavior
- `standard`: ordinary user or service capabilities; may be reconstructed primarily through flows and surface behavior
- `auxiliary`: supporting or incidental functionality; may remain surface-level unless the repository proves otherwise

### Capability Triage Outputs

The workflow must at least capture:

- capability ID
- display name
- tier
- why the capability matters
- main evidence sources
- required depth expectation

In the first rollout, this can live inside `master-pack.md` and `coverage-matrix.md`. Later rollouts may break it out into a dedicated `capability-triage.md`.

### Why This Matters

Without triage, the workflow naturally equalizes effort across all observed features. That is precisely how core mechanisms disappear while the document still claims strong coverage.

## Depth Policy

`sp-prd v2` needs an explicit depth policy so "covered" means something operationally real.

### `critical` Capabilities Must Include

- overview and capability purpose
- implementation mechanisms
- relevant format or protocol matrix when applicable
- edge cases and failure paths
- source traceability down to files, and to functions when needed
- explicit unknowns and inference notes

### `high` Capabilities Must Include

- overview
- mechanism summary
- important rules and compatibility behavior
- main failure paths
- source traceability at least to the owning modules and key routines

### `standard` Capabilities Must Include

- overview
- user flow or service flow
- main surfaces
- related rules or entities when applicable

### `auxiliary` Capabilities May Include

- surface inventory
- short purpose statement
- export placement

Depth policy is what turns capability tiering into a completion rule rather than a taxonomy exercise.

## Evidence Harvest Strategy

The evidence model should stay additive rather than disruptive.

### Surface Evidence

All runs should still collect standard repository surfaces:

- types and models
- routes and pages
- API and CLI entrypoints
- jobs and runtime surfaces
- tests and fixtures
- docs and terminology

### Targeted Evidence

For triaged `critical` and `high` capabilities, the workflow must additionally collect:

- implementation files
- key functions
- parsers and serializers
- compatibility and normalization logic
- error-handling branches
- edge-case handlers
- config and write-path behavior

### Compatibility Principle

The first rollout should prefer stronger evidence requirements over brand-new evidence-directory taxonomy. If existing evidence files can carry deeper content safely, do that first.

## Coverage Matrix v2 Semantics

The existing coverage matrix should become depth-aware rather than purely binary.

### Summary Table

The top-level coverage view should include:

- capability
- tier
- evidence status
- depth status
- export destinations
- overall status

### Depth Breakdown for `critical` and `high`

These capabilities should also record a structured depth breakdown covering:

- format or protocol coverage
- implementation mechanism coverage
- edge-case coverage
- traceability coverage
- unresolved unknowns

### Recommended Status Vocabulary

Replace simple "covered / uncovered" semantics with:

- `surface-covered`
- `partially-reconstructed`
- `depth-gap`
- `blocked-by-unknowns`
- `depth-qualified`

The workflow should only use a strong success term for a critical capability after both evidence presence and depth expectations are satisfied.

## Master Pack v2 Structure

`master/master-pack.md` remains the only truth source, but its internal structure must become more depth-aware.

### 1. Product Frame

Must include:

- product overview
- core value proposition
- project classification
- roles and major boundaries

### 2. Capability Inventory

Must include:

- capability IDs
- tier
- coverage state
- evidence confidence

### 3. Critical Capability Dossiers

Each `critical` capability and, where needed, each `high` capability should receive a dedicated dossier with:

- overview
- implementation mechanisms
- format or spec matrix when relevant
- edge cases and failure paths
- source traceability
- unknowns and inference notes

### 4. Surface Inventory

UI and service surface inventories remain important, but they should map back to capabilities rather than acting as the primary narrative spine.

### 5. Data, Rules, and Integrations

Entities, rules, permissions, config surfaces, and integrations should remain first-class and should be linkable from capability dossiers.

### 6. Coverage and Export Map

The master pack must show:

- where each capability appears in exports
- which items remain master-pack-only detail
- which unknowns still affect export confidence

## Quality Gates

The first rollout should add stronger completion gates without overcomplicating the artifact model.

### Gate 1: Capability Triage Gate

Completion is blocked if the run never explicitly identifies core capabilities and their depth tiers.

### Gate 2: Critical Depth Gate

Completion is blocked if a `critical` capability lacks implementation-grade reconstruction.

### Gate 3: Traceability Gate

Completion is blocked if master-pack mechanism claims for `critical` capabilities cannot be traced back to repository evidence.

### Gate 4: Export Integrity Gate

Completion is blocked if an export introduces consequential facts not grounded in the master pack, or if a critical capability has no export landing point where one is required.

### Gate 5: Unknown Visibility Gate

Completion is blocked if missing evidence is silently narrated as fact rather than preserved as `Unknown` or bounded `Inference`.

## Artifact and Validation Strategy

Current validation surfaces already enforce a minimum PRD artifact set:

- `workflow-state.md`
- `coverage-matrix.md`
- `master/master-pack.md`
- `master/exports/`
- `exports/prd.md`

That existing contract is an important implementation constraint.

### v2.1 Rule

Do not make new files hard-required if the same contract can be enforced by extending the structure and validation of the existing required artifacts.

This keeps rollout safer and prevents premature breakage across generated surfaces and tests.

### Possible v2.2 Extensions

Once the contract is stable, the workflow may add dedicated artifacts such as:

- `capability-triage.md`
- `depth-policy.md`
- `quality-check.md`

Those should be introduced only when they materially improve operability rather than just increasing file count.

## Rollout Plan

### v2.1: Contract Hardening

Primary work:

- update `templates/commands/prd.md`
- add capability-triage language to the workflow process
- add depth-aware evidence and coverage expectations
- add quality-gate requirements
- expand master-pack structure guidance
- extend tests for the new workflow contract
- extend artifact validation to catch shallow-but-complete-looking PRD suites

Primary principle:

compatibility-first contract strengthening

### v2.2: Assistive Automation

Possible additions:

- complexity pre-scan
- format inference
- dedicated triage artifacts
- incremental update logic
- stronger automated depth checks

Primary principle:

automation after the workflow has a trustworthy definition of completeness

## Testing and Verification Impact

At minimum, the rollout should update:

- `tests/test_prd_template_guidance.py`
- `tests/test_prd_hook_contract.py`
- `src/specify_cli/hooks/artifact_validation.py`

Recommended new verification scenarios:

- PRD run with surface coverage but missing critical mechanism detail should fail validation
- PRD run with missing traceability for critical capability claims should fail validation
- PRD run with depth-qualified critical capabilities should pass
- PRD export that contains facts absent from `master-pack.md` should fail

## What Not To Do First

The first rollout should explicitly avoid:

- similarity-project benchmarking as a required workflow step
- mandatory multi-pass autonomous evidence loops
- heavy pre-scan intelligence as a prerequisite for correctness
- new hard-required artifact files unless they are necessary

Those ideas may become useful later, but they are not the first-order fix.

## Completion Criteria

`sp-prd v2` is ready to ship when:

- the workflow template explicitly requires capability triage
- depth policy is expressible in the contract
- coverage semantics distinguish surface coverage from depth-qualified reconstruction
- the master pack can carry critical capability dossiers
- validation can reject shallow completion for critical capabilities
- the workflow remains a peer current-state PRD lane with no automatic planning handoff

## Final Recommendation

Adopt `sp-prd v2` as a contract-hardening release centered on one rule:

**A PRD suite is not complete merely because repository surfaces were scanned and exported. It is complete only when the product-defining capabilities have been reconstructed at the depth their importance requires.**

That rule is the missing backbone. Once it exists, later automation can improve speed and consistency without weakening trust.
