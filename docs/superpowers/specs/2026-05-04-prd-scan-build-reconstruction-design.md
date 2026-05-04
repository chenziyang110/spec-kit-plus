# PRD Scan / PRD Build Reconstruction Design

**Date:** 2026-05-04
**Status:** Approved
**Scope:** Replace the current one-step `sp-prd` workflow with a two-step
`sp-prd-scan -> sp-prd-build` workflow, deprecate `sp-prd` as the primary lane,
define reconstruction-grade intermediate contracts, and propagate the new
workflow across templates, CLI routing, validation, docs, and tests
**Primary goal:** Turn repository-first PRD extraction into a reconstruction
pipeline that can support 1:1 implementation recreation by a new engineer

## Summary

This design replaces the current one-step `sp-prd` workflow with a two-step
reverse-documentation flow:

```text
sp-prd-scan -> sp-prd-build
```

The current `sp-prd` contract already asks for capability triage, deep evidence
harvest, master-pack-first synthesis, and depth-aware quality gates. That is
directionally correct, but it still keeps repository investigation and final
document synthesis inside one workflow. In practice, that makes it too easy for
an agent to:

- stop at path-level traceability instead of structure-level reconstruction
- collapse multiple critical mechanisms into one prose summary
- write exports before every reconstruction-critical artifact is captured
- infer missing data in the build phase instead of forcing the scan phase to
  close evidence gaps

The new design separates those responsibilities. `sp-prd-scan` becomes the
read-only reconstruction investigation workflow. `sp-prd-build` becomes the
strict document compiler that consumes only validated scan outputs.

This is not a cosmetic prompt split. The design adds a reconstruction contract
layer so the final PRD suite can be checked for actual recreation readiness
instead of surface completeness.

## Problem Statement

The existing `sp-prd` workflow combines five responsibilities:

1. route and initialize the PRD run
2. classify the project and triage capabilities
3. inspect repository artifacts and collect evidence
4. synthesize current-state product truth
5. export reader-facing PRD documents

That single-workflow shape causes recurring quality failures for projects whose
value depends on non-trivial internal behavior:

- capability coverage can look complete while format mappings, write logic,
  migration rules, or failure behavior remain under-described
- path-level evidence can be mistaken for structure-level understanding
- build-time synthesis can silently invent missing implementation detail
- final exports can omit field-level contracts while still passing prose-heavy
  checklists
- the workflow lacks a durable "reconstruction packet" equivalent to the
  `map-scan` packet model

The result is a PRD suite that may be product-readable but is not recreation-
ready. That is unacceptable for the explicit target of this design: a new
engineer should be able to reconstruct the implementation with high fidelity
from the PRD package.

## Goals

- Replace `sp-prd` as the primary reverse-PRD workflow with explicit
  `sp-prd-scan` and `sp-prd-build` commands.
- Make `sp-prd-scan` produce a complete reconstruction package before any final
  PRD exports are written.
- Make `sp-prd-build` refuse to continue when reconstruction-critical evidence
  is incomplete.
- Add machine-readable intermediate contracts that describe capabilities,
  artifact structures, and recreation readiness.
- Force critical capabilities to reach reconstruction depth, not merely surface
  coverage.
- Preserve `Evidence`, `Inference`, and `Unknown` labeling throughout the new
  workflow.
- Keep `master/master-pack.md` as the only truth source for final exports.
- Provide a migration path that updates templates, CLI routing, docs, tests,
  and state helpers together instead of leaving dual semantics in place.

## Non-Goals

- Do not preserve the current one-step `sp-prd` as the primary documented
  reverse-PRD flow.
- Do not allow `sp-prd-build` to become a second ad hoc repository scan.
- Do not optimize for short output. The target is recreation readiness, not a
  minimal executive summary.
- Do not turn the workflow into future-state redesign or automatic planning.
- Do not require every repository to reach zero unknowns. Unknowns remain
  allowed, but they must stay explicit and they must block recreation-ready
  claims for critical capabilities when unresolved.

## User-Approved Direction

This design reflects the following explicit decisions from review:

1. The workflow should split into two independent commands, not an internal
   two-phase hidden implementation.
2. The existing `sp-prd` command should be deprecated as the primary route
   rather than retained as the main extraction workflow.
3. The target quality bar is "a new engineer can recreate the implementation
   1:1", even if that makes the PRD package longer and more engineering-heavy.
4. The recommended design is the strongest option: hard workflow split plus a
   dedicated reconstruction contract layer.
5. The migration should optimize for high quality, not for minimum code churn.

## Decision Summary

Ship a new two-step reconstruction workflow:

```text
sp-prd-scan -> sp-prd-build
```

with these semantics:

- `sp-prd-scan`
  - read-only repository investigation
  - capability-first reconstruction planning
  - artifact-structure extraction
  - scan packet generation
  - recreation readiness ledger production
- `sp-prd-build`
  - scan-package validation
  - master-pack compilation
  - export rendering
  - reverse coverage validation
  - refusal and rescan routing when readiness fails

Deprecate `sp-prd` as a primary workflow. In the rollout target state it should
exist only as a compatibility lane that routes users toward the new two-step
workflow and no longer presents itself as the canonical implementation-quality
reverse-PRD command.

## Approaches Considered

### Approach A: Hard split only

Create `sp-prd-scan` and `sp-prd-build`, but keep the intermediate contract
surface thin and mostly prose-driven.

**Pros**

- cleaner workflow boundaries
- lower implementation effort than a full contract layer
- already better than the current single-step workflow

**Cons**

- still too easy for `sp-prd-build` to summarize loosely structured evidence
- difficult to enforce field-level coverage and recreation readiness
- weaker refusal mechanics for missing schema, mapping, or state-transition
  detail

**Decision**

Rejected as insufficient for the approved quality bar.

### Approach B: Hard split plus reconstruction contract layer

Split the workflow and add explicit machine-readable ledgers for capabilities,
artifacts, and recreation readiness.

**Pros**

- strongest support for 1:1 recreation
- enables hard validation of field-level and producer-consumer coverage
- keeps build outputs grounded in durable structured facts
- best alignment with the `map-scan -> map-build` pattern already adopted in
  the product

**Cons**

- larger implementation surface
- more state artifacts to define and validate
- requires coordinated rollout across docs, tests, helpers, and routing

**Decision**

Accepted.

### Approach C: Hard split but allow controlled build-time repository rereads

Allow `sp-prd-build` to reread selected files when the scan package is almost
complete.

**Pros**

- smoother operator experience
- fewer explicit rescan loops in some cases

**Cons**

- collapses the workflow boundary over time
- weakens traceability
- invites the exact failure mode this design is meant to eliminate

**Decision**

Rejected.

## Workflow Overview

### 1. `sp-prd-scan`

`sp-prd-scan` is the reconstruction-investigation workflow. It must not write
the final PRD suite. Its job is to produce a complete reconstruction package:

```text
.specify/prd-runs/<run-id>/workflow-state.md
.specify/prd-runs/<run-id>/prd-scan.md
.specify/prd-runs/<run-id>/coverage-ledger.md
.specify/prd-runs/<run-id>/coverage-ledger.json
.specify/prd-runs/<run-id>/capability-ledger.json
.specify/prd-runs/<run-id>/artifact-contracts.json
.specify/prd-runs/<run-id>/reconstruction-checklist.json
.specify/prd-runs/<run-id>/scan-packets/<lane-id>.md
.specify/prd-runs/<run-id>/evidence/**
.specify/prd-runs/<run-id>/worker-results/**
```

The scan workflow identifies what must be reconstructed, how deep each area
must go, which repository paths own that truth, and what facts must exist
before the PRD suite can be compiled responsibly.

### 2. `sp-prd-build`

`sp-prd-build` is the reconstruction-PRD compiler. It validates the scan
package, compiles `master/master-pack.md`, renders final exports, and proves
reverse coverage closure.

If the scan package is incomplete, `sp-prd-build` must not guess and continue.
It must produce a reconstruction gap report and route back to `sp-prd-scan`.

## Run Workspace Contract

The PRD run directory evolves from a loose evidence workspace into a structured
reconstruction workspace:

```text
.specify/prd-runs/<run-id>/
  workflow-state.md
  prd-scan.md
  coverage-ledger.md
  coverage-ledger.json
  capability-ledger.json
  artifact-contracts.json
  reconstruction-checklist.json
  scan-packets/
  evidence/
  worker-results/
  master/
    master-pack.md
  exports/
    prd.md
    reconstruction-appendix.md
    data-model.md
    integration-contracts.md
    runtime-behaviors.md
```

Three new files are central to the contract:

- `capability-ledger.json`
  - capability identity, tier, owning evidence, reconstruction depth, and final
    landing expectations
- `artifact-contracts.json`
  - recreation-critical structures such as DDL, config schema, protocol
    mappings, state transitions, presets, compatibility rules, and error models
- `reconstruction-checklist.json`
  - machine-readable recreation readiness gates for critical capabilities and
    artifacts

## `sp-prd-scan` Contract

### Hard Boundary

- `sp-prd-scan` must not write `master/master-pack.md` or `exports/**`.
- `sp-prd-scan` must not claim the PRD suite is complete.
- `sp-prd-scan` writes only the scan package and supporting evidence under the
  run workspace.
- `sp-prd-scan` may use read-only subagents, but those lanes must return
  structured handoffs rather than freeform summaries.

### Primary Objective

Produce enough structured evidence that a later build step can compile a
recreation-ready PRD suite without rereading the repository.

### Investigation Model

`sp-prd-scan` no longer treats directories or modules as the only unit of work.
It works across three reconstruction objects:

- `capability`
  - a repository-backed product behavior or system promise
- `artifact`
  - a concrete structure such as a table, config file, schema, mapping layer,
    preset catalog, or state machine
- `boundary`
  - a seam where data, control, or compatibility crosses from one owner to
    another

The scan must answer, for each critical area:

- what capability exists
- which artifacts make it real
- what those artifacts contain
- who produces them
- who consumes them
- which fields, transitions, or constraints must remain stable
- how the system behaves when inputs are invalid or dependent systems fail

### Capability Triage

The scan begins by triaging capabilities into depth tiers:

- `critical`
  - must be reconstructable before build completion can be claimed
- `high`
  - needs strong structural capture, but may allow bounded unknowns
- `standard`
  - should be documented well, but not with the same refusal threshold
- `auxiliary`
  - useful but not defining for product recreation

Critical and high capabilities must name their required artifacts and required
reconstruction dimensions before broad synthesis continues.

### Coverage States

The current depth-oriented states should be replaced by stricter reconstruction
states:

- `inventory-only`
- `surface-understood`
- `structure-captured`
- `producer-consumer-traced`
- `reconstruction-ready`
- `blocked-by-gap`

`critical` capabilities cannot be handed to `sp-prd-build` unless they reach
`reconstruction-ready` or remain explicitly blocked with named unresolved gaps.

### Required Artifact Contracts

`artifact-contracts.json` must support at least these artifact families:

- `database_table`
  - full DDL, indexes, constraints, migration history, read/write entrypoints
- `config_file`
  - schema, field meanings, defaults, write timing, sample fragments
- `protocol_mapping`
  - source-to-target field mapping, drops, normalization, compatibility rules,
    failure behavior
- `state_machine`
  - states, triggers, legal and illegal transitions, rollback or retry logic
- `preset_catalog`
  - preset identity, key differences, representative full examples
- `error_contract`
  - error code or shape, trigger conditions, consumer handling behavior

The goal is not to catalog everything uniformly. The goal is to capture the
structures without which faithful recreation is impossible.

### PRD Scan Packets

Like `sp-map-scan`, `sp-prd-scan` must generate executable packet contracts.
These packets are reconstruction-focused rather than navigation-focused.

Each packet must expose:

- `lane_id`
- `mode: read_only`
- `capability_ids`
- `artifact_ids`
- `boundary_ids`
- `required_reads`
- `required_questions`
- `expected_outputs`
- `forbidden_actions`
- `result_handoff_path`
- `minimum_verification`
- `blocked_conditions`

Expected outputs should be structural, such as:

- field mapping table
- schema fragment
- producer-consumer chain
- error payload contract
- representative config example
- migration rule summary

### Refusal Rules

`sp-prd-scan` must refuse build handoff when any critical recreation surface is
still shallow. Refusal cases include:

- a critical table is named but its fields or constraints are missing
- a critical config file is traced by path but not by schema and sample content
- a protocol conversion is described but lacks a field-level mapping table
- presets are counted or mentioned without representative full examples
- a capability exists without a producer-consumer chain
- failure behavior is noted generically without contract shape or trigger
  semantics

## `sp-prd-build` Contract

### Hard Boundary

- `sp-prd-build` must not become a second repository scan.
- `sp-prd-build` must not silently fill critical evidence gaps by rereading the
  codebase.
- `sp-prd-build` may validate that scan artifacts exist and are internally
  coherent, but when critical reconstruction data is missing it must stop and
  route back to `sp-prd-scan`.

### Required Inputs

Before synthesis begins, `sp-prd-build` must read and validate:

- `workflow-state.md`
- `prd-scan.md`
- `coverage-ledger.json`
- `capability-ledger.json`
- `artifact-contracts.json`
- `reconstruction-checklist.json`
- `scan-packets/*.md`
- `worker-results/**` or equivalent structured scan outputs
- `evidence/**`

Missing or invalid inputs are a build refusal, not a recoverable suggestion.

### Core Flow

`sp-prd-build` should execute these phases:

1. **Readiness validation**
   - prove that critical capabilities and artifact contracts meet the minimum
     recreation threshold
2. **Master pack compilation**
   - write `master/master-pack.md` as the only truth source
3. **Export rendering**
   - render the final PRD package from the master pack
4. **Reverse coverage validation**
   - prove that every critical capability and artifact landed in the final
     package
5. **Completion report**
   - report what is complete, what remains unknown, and what blocks recreation

### Output Contract

The final export package should include at minimum:

- `exports/prd.md`
  - primary reader-facing current-state PRD
- `exports/reconstruction-appendix.md`
  - implementation recreation appendix
- `exports/data-model.md`
  - persistent structures, migrations, and data constraints
- `exports/integration-contracts.md`
  - protocol, API, config-write, and boundary contracts
- `exports/runtime-behaviors.md`
  - state transitions, failure handling, retry or rollback behavior

`master/master-pack.md` remains the only truth source. No export may introduce
new consequential facts that do not first appear in the master pack and trace
back to accepted scan evidence.

### Build Quality Gates

Add these explicit gates:

- **No New Facts Gate**
  - exports may not invent consequential facts absent from scan outputs
- **Artifact Landing Gate**
  - each critical artifact must land in the final package
- **Field-Level Coverage Gate**
  - critical schemas, configs, and mappings require field-level detail
- **Example Presence Gate**
  - critical capabilities need at least one concrete structural example when
    applicable
- **Traceback Gate**
  - important claims must map back to capability IDs, artifact IDs, or evidence
    IDs
- **Inference Ceiling Gate**
  - a critical capability cannot be declared recreation-ready if it remains
    mostly inferred

### Build Failure Contract

When `sp-prd-build` refuses to continue, it must report:

- the failed readiness check
- affected capability IDs or artifact IDs
- the missing structure, example, or producer-consumer fact
- the smallest safe `sp-prd-scan` repair packet or repair area

## Migration Strategy

### Target Workflow Shape

The product should converge on this shape:

- `sp-prd-scan`
- `sp-prd-build`
- `sp-prd` as a deprecated compatibility entrypoint

The deprecated `sp-prd` surface should no longer present itself as the primary
workflow. It should route users to the explicit two-step flow and explain that
the old one-step semantics are obsolete for high-fidelity reconstruction.

### Surfaces That Must Change Together

This is not a template-only change. The rollout must cover:

- command templates
  - `templates/commands/prd-scan.md`
  - `templates/commands/prd-build.md`
  - deprecated routing guidance in `templates/commands/prd.md`
- state helpers
  - `scripts/bash/prd-state.sh`
  - `scripts/powershell/prd-state.ps1`
- CLI routing and help
  - `src/specify_cli/__init__.py`
- passive routing skills
  - `templates/passive-skills/project-to-prd/`
  - `templates/passive-skills/spec-kit-workflow-routing/`
- docs
  - `README.md`
  - `PROJECT-HANDBOOK.md`
  - `docs/quickstart.md`
  - `docs/installation.md`
- validation and tests
  - PRD workflow contract tests
  - state helper tests
  - artifact validation tests
  - deprecated entrypoint tests

### Recommended Implementation Phases

1. **Workflow contract phase**
   - add the new workflow templates and artifact contracts
2. **CLI and state phase**
   - add command registration, state initialization, and resume behavior
3. **Validation and test phase**
   - enforce build refusal and reconstruction gates in tests
4. **Docs and deprecation phase**
   - update the public and internal docs, then demote `sp-prd`

### Completion Standard

The migration is complete only when:

- `sp-prd-scan` and `sp-prd-build` have clear, enforced boundaries
- `sp-prd` is no longer the effective primary path
- structured reconstruction artifacts are validated by tests
- `sp-prd-build` cannot report success on a shallow scan package
- docs, CLI help, templates, passive routing, and tests all converge on the new
  semantics

## Risks And Mitigations

### Risk: The design becomes too heavy for ordinary repositories

**Mitigation**

Use tiered reconstruction depth. Only `critical` capabilities require the
strongest recreation contract.

### Risk: `sp-prd-build` drifts back into ad hoc scanning

**Mitigation**

Keep the hard "no build-time repository reread for missing critical evidence"
rule and test it explicitly.

### Risk: rollout leaves two conflicting meanings of `sp-prd`

**Mitigation**

Update docs, passive routing, CLI help, and deprecated entrypoint behavior in
the same rollout sequence rather than leaving the old surface undocumented but
operationally preferred.

### Risk: operators see more artifacts and assume complexity for its own sake

**Mitigation**

Keep the rationale explicit: the new artifacts exist to make recreation
readiness auditable, not to increase prose volume.

## Recommended Next Step

After this design is approved in-repo, the implementation planning step should
produce a phased execution plan that starts with workflow contracts and state
helpers before touching broader docs or passive routing.
