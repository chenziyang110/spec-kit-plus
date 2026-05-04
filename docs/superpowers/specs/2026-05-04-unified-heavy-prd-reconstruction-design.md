# Unified Heavy PRD Reconstruction Design

**Date:** 2026-05-04
**Status:** Approved
**Scope:** Upgrade `sp-prd-scan -> sp-prd-build` into a unified heavy
reconstruction workflow that prioritizes near-original product recreation,
adds mandatory multi-subagent orchestration, introduces reconstruction-grade
artifact contracts, and propagates the new standard across workflow templates,
state helpers, validations, export templates, docs, and tests
**Primary goal:** Make the PRD package strong enough that a new engineering
team can recreate a feature-complete product from code-only evidence with
behavior, configuration, error semantics, and runtime behavior preserved as
closely as the repository allows

## Summary

This design keeps the existing two-step workflow:

```text
sp-prd-scan -> sp-prd-build
```

but changes its meaning completely.

The current PRD flow is a depth-aware reverse-documentation lane. That is a
good starting point, but it is still optimized more for "high-quality current
state documentation" than for "reconstruction-grade product archival". When
the goal becomes near-original recreation from code-only evidence, the workflow
must stop behaving like a documentation generator and start behaving like a
forensic reconstruction system.

Under this design:

- `sp-prd-scan` becomes a mandatory-subagent evidence-harvesting engine
- `sp-prd-build` becomes a strict compiler and reverse-validation gate
- `critical` product truth must reach `L4 Reconstruction-Ready`
- missing critical evidence blocks completion instead of leaking into
  prose-heavy exports
- the final PRD package expands from a handful of summaries into a structured
  reconstruction archive with explicit contracts for configuration, protocol,
  state, errors, entrypoints, and verification

This design is intentionally heavy. It prefers refusal over false confidence.
The target outcome is not "usable documentation". The target outcome is
"reconstruction-grade product truth".

## Problem Statement

The current `sp-prd-scan -> sp-prd-build` split fixes a major structural issue
from the earlier one-step flow, but it still leaves four gaps if the product
standard is "near-original recreation from code-only evidence":

1. critical mechanisms can still be under-specified while the package looks
   narratively complete
2. important implementation truth can be flattened into prose instead of
   preserved as field-level or transition-level contracts
3. scan coverage can be capability-aware without being reconstruction-aware
4. multi-subagent work is not yet treated as a first-class execution contract
   comparable to the `map-scan -> map-build` lane

The result is a package that may explain what the product does, but does not
necessarily preserve enough structured truth to rebuild it with near-original
behavior. That is not acceptable for the approved quality bar.

## Approved Product Standard

This design reflects the following explicit direction:

1. Keep a two-step workflow rather than adding a mandatory third phase.
2. Make the PRD standard uniformly heavy across product types.
3. Use only code-internal evidence sources:
   - source code
   - configuration files
   - templates
   - scripts
   - tests
   - repository docs
   - packaging and runtime metadata
4. Target near-original recreation:
   - functionally complete
   - behaviorally close
   - configuration behavior preserved
   - runtime semantics preserved
   - error semantics preserved
   - verification entrypoints preserved
5. Use an extremely conservative gate:
   if critical evidence is missing, the run must be blocked.
6. Treat multi-subagent orchestration as a required part of the workflow,
   following the spirit of `map-scan -> map-build`.

## Goals

- Keep `sp-prd-scan -> sp-prd-build` as the canonical PRD extraction lane.
- Redefine the lane as a reconstruction-grade product archive workflow.
- Establish one unified heavy standard across all product types rather than
  branching the workflow by platform class.
- Introduce a single critical-item model that applies to UI, service, CLI,
  desktop, mobile, and AI-heavy repositories.
- Make `sp-prd-scan` use mandatory subagent orchestration for substantive work.
- Make `sp-prd-build` compile only from the scan package and never from a new
  repository crawl.
- Require `critical` truth to reach `L4 Reconstruction-Ready`.
- Expand the final PRD export set so it preserves config, protocol, state,
  error, and verification truth instead of collapsing those domains into prose.
- Upgrade validations and helper state so runs can be machine-checked for
  actual reconstruction readiness.

## Non-Goals

- Do not introduce a mandatory third command such as `sp-prd-certify`.
- Do not rely on screenshots, runtime captures, human walkthroughs, network
  traces, or database dumps as primary evidence sources.
- Do not optimize for minimal output size.
- Do not make best-effort assumptions for missing critical evidence.
- Do not split the workflow into different default standards for "simple" vs
  "complex" product classes.

## Decision Summary

Ship a unified heavy reconstruction standard on top of the existing two-step
lane:

```text
sp-prd-scan -> sp-prd-build
```

with these core rules:

- `sp-prd-scan`
  - mandatory-subagent execution for substantive scanning
  - packetized, read-only evidence collection
  - structured worker result handoffs
  - explicit reconstruction ledgers and contracts
  - critical truth must close to `L4 Reconstruction-Ready`
- `sp-prd-build`
  - build only from scan artifacts
  - packet evidence intake before export synthesis
  - field-level and transition-level preservation
  - reverse reconstruction validation before completion
  - blocked completion when critical truth is incomplete

This is the recommended path because it preserves the already-correct two-step
mental model while materially increasing reconstruction fidelity.

## Approaches Considered

### Approach A: Keep two steps and lightly deepen existing ledgers

**Pros**

- smallest implementation cost
- low disruption to current templates and helpers

**Cons**

- still too easy for critical evidence to remain prose-only
- weak support for near-original recreation
- does not elevate subagent orchestration to a real contract

**Decision**

Rejected.

### Approach B: Keep two steps and make them uniformly heavy

**Pros**

- preserves the clean scan/build split
- aligns with the successful `map-scan -> map-build` product shape
- strongest path to reconstruction-grade output without adding another phase
- lets validation and tests lock the standard into place

**Cons**

- higher rollout cost
- more blocking runs
- larger artifact surface and test matrix

**Decision**

Accepted.

### Approach C: Add a third mandatory certification phase

**Pros**

- very explicit staging
- clean separation between synthesis and certification

**Cons**

- significantly more workflow complexity
- larger state surface
- harder operator adoption
- not necessary until the heavy two-step standard proves insufficient

**Decision**

Rejected for now.

## Workflow Model

### `sp-prd-scan`

`sp-prd-scan` becomes a reconstruction evidence engine, not a narrative
summary. It produces a complete scan package that is strong enough for
`sp-prd-build` to compile the PRD suite without rereading the repository.

The scan package continues to include:

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

and is expanded with these required machine-readable artifacts:

```text
.specify/prd-runs/<run-id>/entrypoint-ledger.json
.specify/prd-runs/<run-id>/config-contracts.json
.specify/prd-runs/<run-id>/protocol-contracts.json
.specify/prd-runs/<run-id>/state-machines.json
.specify/prd-runs/<run-id>/error-semantics.json
.specify/prd-runs/<run-id>/verification-surfaces.json
```

### `sp-prd-build`

`sp-prd-build` becomes a strict compiler. It validates the scan package,
creates a packet evidence intake, compiles `master/master-pack.md`, renders the
final exports, and proves reverse reconstruction coverage.

It must not reread the repository to patch missing facts. If critical truth is
missing, it routes back to `sp-prd-scan`.

## Unified Critical Item Families

The heavy standard does not branch by product type. Instead, every repository
must be evaluated against the same critical-item families whenever those
surfaces exist.

### 1. Main Capability Chains

The core user or system flows that define the product's value.

Required truth:

- entry
- prerequisites
- main steps
- success outcome
- failure outcome
- relevant state changes
- relevant side effects
- configuration or boundary influence

### 2. External Entrypoints and Command Surfaces

Any surface through which an external caller can trigger product behavior.

Examples:

- CLI commands
- HTTP, RPC, IPC, and message handlers
- exported SDK or library entrypoints
- background jobs, schedulers, hooks, and webhooks

Required truth:

- name
- parameters
- return shape
- error shape or branches
- permission or guard rules
- downstream state impact

### 3. State Machines and Flow Control

Any explicit or implicit lifecycle logic that governs product behavior.

Examples:

- status transitions
- retries
- rollbacks
- failover
- circuit breakers
- initialization
- recovery
- migration phases

Required truth:

- states
- transition triggers
- guard conditions
- failure transitions
- recovery logic
- start and terminal conditions

### 4. Data and Persistence Contracts

Any durable truth surface.

Examples:

- database schema
- document schema
- local files
- on-disk metadata
- cache checkpoints when behavior depends on them

Required truth:

- structures
- fields and types
- defaults and constraints
- relationships and indexes
- lifecycle semantics
- migration and repair behavior

### 5. Configuration and Behavior Switches

Any configuration surface that materially changes runtime behavior.

Examples:

- config files
- environment variables
- feature flags
- provider settings
- mode switches

Required truth:

- path or key
- schema
- default value
- precedence or override order
- behavioral scope
- failure behavior on bad config

### 6. Protocol and Boundary Contracts

Any seam where the product maps, transforms, or constrains information across
subsystems or external dependencies.

Required truth:

- boundary sides
- payload shapes
- field mappings
- compatibility differences
- serialization or deserialization rules
- abnormal boundary behavior

### 7. Error Semantics and Recovery Behavior

Any error surface visible to a user, operator, or caller.

Required truth:

- trigger condition
- classification
- visibility
- retryability
- rollback, degrade, or abort path
- residual state or logging implications

### 8. Verification and Regression Entrypoints

The surfaces that make recreated behavior checkable.

Required truth:

- existing test entrypoints
- minimum meaningful verification commands
- behaviors already locked by tests
- critical behaviors lacking automation
- useful parity checkpoints for reconstruction teams

## Evidence Depth Model

All critical-item families use the same evidence depth scale.

- `L1 Exists`
  - surface existence known
- `L2 Surface`
  - entrypoints, owning files, or basic responsibilities identified
- `L3 Behavioral`
  - behavior, constraints, and side effects captured
- `L4 Reconstruction-Ready`
  - enough structured detail exists to directly support recreation

Heavy standard requirements:

- `critical` items must reach `L4`
- `high` items must reach at least `L3`, and should reach `L4` whenever the
  mechanism materially affects product fidelity
- `standard` items must reach at least `L2`
- `auxiliary` items may remain at `L1` or `L2`

If a `critical` item does not reach `L4`, the run must be blocked.

## Minimum Reconstruction-Ready Depth

### Main Capability Chains

To count as reconstruction-ready, a capability chain must capture:

- entry
- prerequisites
- step sequence
- success result
- failure result
- state impact
- side effects
- relevant config or boundary influence

### External Entrypoints

To count as reconstruction-ready, an entrypoint must capture:

- callable name
- parameter structure
- return structure
- error structure or error branches
- guard or permission checks
- downstream effects

### State Machines

To count as reconstruction-ready, a state machine must capture:

- state set
- transition triggers
- guard conditions
- failure transitions
- retry or recovery behavior
- initialization and terminal behavior

### Data and Persistence

To count as reconstruction-ready, a persistence contract must capture:

- entity or structure name
- fields and types
- defaults and constraints
- relationships and indexes when present
- create, update, delete, and migration semantics
- initialization or repair behavior when present

### Configuration

To count as reconstruction-ready, a configuration contract must capture:

- path or variable name
- schema
- defaults
- precedence or override rules
- runtime effect
- failure semantics on invalid values

### Protocol and Boundaries

To count as reconstruction-ready, a protocol contract must capture:

- producer and consumer sides
- message or payload structure
- field mapping
- compatibility branches
- translation rules
- abnormal path behavior

### Error Semantics

To count as reconstruction-ready, an error contract must capture:

- trigger
- classification
- exposure path
- retry or recovery semantics
- rollback or degrade behavior
- residual impact

### Verification Surfaces

To count as reconstruction-ready, a verification surface must capture:

- automated entrypoints
- minimum meaningful command
- what behavior is locked
- what critical behavior is not locked
- what reconstruction teams can use as parity checks

## Multi-Subagent Orchestration

The heavy standard makes subagent orchestration mandatory for substantive work.

### `sp-prd-scan`

Use:

```text
execution_model: subagent-mandatory
dispatch_shape: one-subagent | parallel-subagents
execution_surface: native-subagents
```

The leader is responsible for:

- selecting lanes
- preparing `PrdScanPacket` task contracts
- dispatching read-only subagents
- waiting at defined join points
- merging results into ledgers and contracts
- deciding whether reconstruction readiness is achieved

Subagents are responsible for:

- reading only the paths in scope
- answering required questions
- returning structured evidence
- not making final completion decisions

Recommended scan lanes:

- `capability-and-user-flow`
- `interface-and-protocol`
- `data-and-state`
- `config-and-runtime`
- `integration-and-boundary`
- `verification-and-regression`

### `PrdScanPacket`

Every lane must have a structured packet before dispatch. At minimum:

- `lane_id`
- `mode: read_only`
- `objective`
- `owned_capabilities`
- `owned_artifacts`
- `owned_boundaries`
- `required_reads`
- `required_questions`
- `expected_outputs`
- `evidence_targets`
- `forbidden_actions`
- `minimum_verification`
- `result_handoff_path`
- `blocked_conditions`

### `sp-prd-build`

`sp-prd-build` also uses mandatory subagents, but for compilation review rather
than repository scanning.

Recommended build lanes:

- `contract-landing-review`
- `cross-artifact-consistency-review`
- `field-level-preservation-review`
- `unknown-leak-review`

The build leader owns final synthesis and completion decisions. Build subagents
review the scan package and draft export landing concerns; they do not fill
critical evidence gaps by rereading the repository.

## Worker Result Contracts

Each scan lane must return a structured handoff under:

```text
.specify/prd-runs/<run-id>/worker-results/<lane-id>.json
```

At minimum:

- `lane_id`
- `reported_status`
- `paths_read`
- `facts`
- `key_contracts`
- `state_transitions`
- `config_keys`
- `error_semantics`
- `unknowns`
- `confidence`
- `reconstruction_risk`
- `recommended_ledger_updates`

If `paths_read` or `unknowns` are missing for a substantive lane, the scan is
not ready for build.

## Expanded Build Outputs

The heavy standard preserves the existing exports and adds new required
exports.

Existing exports retained:

- `exports/prd.md`
- `exports/reconstruction-appendix.md`
- `exports/data-model.md`
- `exports/integration-contracts.md`
- `exports/runtime-behaviors.md`

New required exports:

- `exports/config-contracts.md`
- `exports/protocol-contracts.md`
- `exports/state-machines.md`
- `exports/error-semantics.md`
- `exports/verification-surface.md`
- `exports/reconstruction-risks.md`

The final package is not a single PRD plus a few appendices. It is a
reconstruction archive.

## Master Pack Expansion

`master/master-pack.md` remains the single export truth source, but it must
become materially heavier.

It should explicitly preserve:

- critical capability dossiers
- entrypoint dossiers
- config dossiers
- protocol dossiers
- state machine dossiers
- error semantic dossiers
- verification dossiers
- export landing map
- reconstruction readiness and remaining risks

No export may invent facts not present in the scan package or master pack.

## Quality Gates

### `sp-prd-scan`

The current gates stay directionally correct, but the heavy standard adds and
strengthens these gates:

- `Critical Reconstruction Gate`
  - every critical item must reach `L4`
- `Config Contract Gate`
  - critical configuration must have key-level schema, defaults, and precedence
- `Protocol Contract Gate`
  - critical boundaries must preserve field mappings and compatibility rules
- `State Machine Gate`
  - critical states must preserve triggers, guards, failures, and recovery
- `Error Semantic Gate`
  - critical errors must preserve trigger and caller-visible behavior
- `Verification Surface Gate`
  - critical behavior must map to verification or an explicit gap
- `Subagent Evidence Gate`
  - worker results must include paths read, unknowns, confidence, and updates

### `sp-prd-build`

The heavy standard strengthens build-time refusal:

- `No New Facts Gate`
  - no new repository rereads
- `Reconstruction Landing Gate`
  - every critical item must land in final outputs
- `Field-Level Preservation Gate`
  - key fields, params, config keys, and transitions must not be flattened
- `Cross-Artifact Consistency Gate`
  - artifacts must not contradict one another
- `Critical Unknown Refusal Gate`
  - unresolved critical unknowns block completion
- `Traceability Gate`
  - critical facts must trace back to concrete `paths_read`
- `Reconstruction Readiness Gate`
  - final outputs must support recreation, not merely explanation

## Readiness Refusal Rules

`sp-prd-build` must route back to `sp-prd-scan` when any of the following are
true:

- a critical item has not reached `L4`
- a critical entrypoint lacks param or return structure
- a critical configuration surface lacks key-level schema
- a critical protocol surface lacks field mapping or compatibility truth
- a critical state surface lacks transition conditions
- a critical error surface lacks trigger or exposure semantics
- a worker result lacks `paths_read`
- a worker result omits `unknowns`
- scan packets are missing or not executable
- final exports cannot land every critical item without flattening

## Implementation Blueprint

This design should be implemented in staged batches.

### Batch 1: Rewrite workflow contracts and public guidance

Primary files:

- `templates/commands/prd-scan.md`
- `templates/commands/prd-build.md`
- `templates/commands/prd.md`
- `templates/passive-skills/project-to-prd/SKILL.md`
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- `README.md`
- `PROJECT-HANDBOOK.md`
- `src/specify_cli/__init__.py`

Outcome:

- heavy standard defined in public contracts
- mandatory subagent model documented
- new critical families and evidence levels documented

### Batch 2: Expand run-state helpers and artifact surfaces

Primary files:

- `scripts/bash/prd-state.sh`
- `scripts/powershell/prd-state.ps1`
- `src/specify_cli/hooks/state_validation.py`

Outcome:

- run helpers initialize and report the expanded artifact surface
- workflow state documents reflect the new authoritative files

### Batch 3: Expand PRD template assets

Primary files:

- `templates/prd/master-pack-template.md`
- existing export templates
- new export templates for config, protocol, state, error, verification, risk

Outcome:

- the export surface matches the heavy standard

### Batch 4: Strengthen artifact validation and refusal rules

Primary files:

- `src/specify_cli/hooks/artifact_validation.py`

Outcome:

- machine validation enforces the heavy standard

### Batch 5: Integrate mandatory subagent orchestration guidance

Primary files:

- integration prompt/rendering surfaces
- command-generation surfaces

Outcome:

- generated integrations preserve packetized subagent guidance

### Batch 6: Expand regression coverage

Primary files:

- PRD template tests
- helper tests
- hook contract tests
- integration text-generation tests
- packaging tests

Outcome:

- the heavy standard is locked in by tests

## Rollout Risks

- existing PRD runs will no longer meet the upgraded completion standard
- helper and validation changes will break tests until the expanded artifact
  surface is wired through
- integration tests asserting generated text will need broad updates
- the build failure rate will rise because shallow evidence no longer passes

These are acceptable consequences of changing the product standard from
"high-quality reverse documentation" to "reconstruction-grade archival".

## Recommended Delivery Order

1. command template contract rewrite plus template tests
2. helper and workflow-state expansion
3. export template expansion plus packaging tests
4. artifact validation hardening
5. integration prompt updates
6. README and handbook cleanup after the technical surfaces are stable

## Acceptance Criteria

This design is considered successfully implemented when:

- `sp-prd-scan` and `sp-prd-build` both describe the heavy standard
- new run helpers initialize the expanded artifact surface
- validation rejects runs that fail the new critical reconstruction rules
- export templates cover config, protocol, state, error, verification, and
  reconstruction risk
- generated integration guidance explicitly supports packetized subagent
  orchestration for PRD scan and build
- the PRD package can no longer claim success when critical evidence is shallow
- tests prove the new contract surface end to end
