# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/.specify/features/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/sp.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Locked Planning Decisions

<!--
  Copy the decisions from spec.md and alignment.md that planners must preserve.
  These should be explicit enough that later task generation and implementation
  do not silently drift away from the agreed requirement shape.
-->

- [Decision that must be preserved in downstream planning]
- [Compatibility, workflow, rollout, or validation decision that cannot be silently dropped]


## Complete-First Delivery Scope

<!--
  Complete-first scope preservation:
  Restate the complete user-confirmed scope that this plan must preserve.
  Execution order, dependency order, and validation order may vary, but planning
  must not reduce delivery scope unless a user-confirmed deferral is recorded in
  the deferral contract below.
-->

- **Scope source files**: `spec.md`, `alignment.md`, `context.md`, `plan-contract.json`, and approved handoff files
- **Delivery rule**: Plan and task the complete confirmed scope; do not shrink scope because the work is complex
- **Complexity rule**: Complexity alone is not a valid reason to split, defer, block, or return upstream
- **Execution phases**: Execution phases are ordering, not delivery deferral
- **Forbidden reductions**: MVP by default, pilot by default, prototype by default, first-release slice, agent-invented `v1/v2`, agent-invented `P0/P1`, or future-work delivery slice
- **Priority labels**: User story priorities such as `P1`, `P2`, and `P3` are ordering labels, not delivery-scope buckets
- **Adaptive blocker carve-out**: Runtime capability limits are blockers only under the adaptive execution policy for heavy, safety-critical, or unpacketizable work, and do not reduce scope

## User-Confirmed Deferral Contract

| Confirmation Source | Exact Excluded Behavior | Residual Risk | Reopen Or Stop Condition | Downstream Artifact |
| --- | --- | --- | --- | --- |
| None | None | None | None | None |

- If the user did not confirm the deferral, keep the behavior in scope through design,
  create a refinement or validation checkpoint, or identify a named valid blocker.

## Must-Preserve Carry-Forward

<!--
  Copy implementation-shaping MP-* items from brainstorming/handoff-to-specify.json,
  spec.md, alignment.md, context.md, and references.md.
  Preserve the MP ID so task generation and implementation can prove the original
  discussion conclusion was not lost.
  If a planning decision conflicts with an MP-* obligation, keep the conflict
  explicit here and route back for a user decision instead of silently replacing
  the protected discussion conclusion.
-->

| MP ID | Type | Planning Obligation | Plan Location | Reopen Or Conflict Condition |
| --- | --- | --- | --- | --- |
| MP-### | [goal | scope | non_goal | scenario | decision | reference | tradeoff] | [what the plan must preserve] | [section anchor] | [condition, conflict decision, or none] |

## Capability Preservation Plan

<!--
  Use this when the spec or discussion handoff names an operation such as
  new, create, scaffold, authoring, template creation, CLI path, or TUI path.

  Command-surface minimization may remap where the user invokes the capability,
  but it must not delete capability. If the public command surface stays small,
  preserve the operation through an explicit TUI route, core API, public CLI
  command, private helper, refinement checkpoint, valid blocker, or
  user-confirmed deferral carrying confirmation source, exact excluded behavior,
  residual risk, reopen or stop condition, and downstream artifact.
-->

| Capability Operation | Upstream Source | Selected Entry Point | Owning Surface | Required Implementation | Acceptance Proof | Reopen Or Conflict Condition |
| --- | --- | --- | --- | --- | --- | --- |
| [create/scaffold operation] | [spec/alignment/handoff source] | [TUI route | core API | public CLI | private helper | user-confirmed deferral] | [module, route, command, contract, or five-field deferral contract row] | [buildable behavior, not just templates/docs, unless valid blocker] | [test, quickstart, contract, manual check, or valid blocker] | [confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact] |

- A static template directory, manual copy docs, or authoring guide may support this plan, but it does not satisfy a confirmed scaffold operation unless manual copy was explicitly selected as the user-facing entry point.
- If this plan removes, narrows, or defers an upstream create/scaffold operation, record the user-confirmed deferral with confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact before task generation proceeds.

## Implementation Target Boundary

- **Current project root**: [copy from `brainstorming/handoff-to-specify.json` `context_boundary.current_project_root`]
- **Current project roles**: [copy role objects with `role`, `scope`, `evidence_source`, and `notes`]
- **Target project root**: [copy from `context_boundary.target_project_root` or record why no external target exists]
- **Target project roles**: [copy role objects with `role`, `scope`, `evidence_source`, and `notes`]
- **Target paths/modules**: [copy verified target paths or required target paths still to verify]
- **Target evidence status**: [target cognition, minimal live reads, user confirmation, external source, or explicit assumption]
- **Reference sources**: [copy discussion `reference_projects` / discussion-state `reference_sources` as reference-only evidence]
- **Cognition scope rule**: Current project cognition cannot prove another project's implementation facts.
- **Stop condition**: If a required target root or target-relative path cannot be confirmed before implementation-shaping design, stop and return to `sp-discussion` or the user for boundary repair.

## Reference Fidelity Inputs

<!--
  Include this section when the upstream spec package carries `Fidelity Requirements`.
  The plan MUST restate the reference object, the required fidelity boundaries,
  and the behavior-level inventory that downstream tasks must preserve or
  explicitly re-approve when they diverge.
-->

### Reference Object

- [Reference implementation or behavior source carried forward from spec.md]

### Behavior-Level Fidelity Inventory

- [Behavior ID] [Preserved / redesigned / user-confirmed deferral] -> [Where the plan preserves it, redesigns it, or records confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact]
- [Behavior ID] [Boundary, lifecycle, failure-path, or compatibility behavior] -> [Where the plan preserves or handles it]

## Scenario Profile Inputs

<!--
  Copy the active scenario profile and profile obligations from spec.md,
  alignment.md, and context.md.

  The generated plan MUST record:
  - exactly one active profile
  - the source artifact that established that profile
  - every profile-driven implementation constraint that downstream tasks and implementation must preserve

  If no special profile applies, record `Standard Delivery` explicitly.
  Do not omit this section or replace it with general prose.
-->

### Active Profile

- [Active profile name, routing reason, and whether it imposes reference fidelity obligations]
- [Source artifact that records the profile decision, such as alignment.md or context.md]

### Profile-Driven Implementation Constraints

- [Profile obligation that MUST change implementation shape, task sequencing, validation evidence, or completion criteria]
- [Reference fidelity contract, required evidence, or deviation rule that downstream tasks and implementation MUST preserve]

## Design System Adoption

- Source and status:
- Token strategy:
- Component reuse and extension policy:
- Platform adaptation strategy:
- Accessibility requirements:
- Evidence strategy:
- Forbidden styling drift:

## Feature UI Brief Adoption

- UI brief source:
- UI work type and real entry points:
- Experience intent and visual/interaction signature:
- UI reference notes:
- Visual target:
- Fidelity mode:
- Reference-Implementation profile:
- Required evidence:
- Must preserve:
- May adapt:
- Must not:
- Required states and viewport matrix:
- Visual verification strategy:

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]  
**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]  
**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]  
**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]  
**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]
**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]  
**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]  
**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]  
**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Implementation Constitution

<!--
  This section is the execution-rule surface for downstream task generation and implementation.

  If the feature hits a boundary-sensitive or profile-sensitive condition, this section MUST make the constraint explicit.
  Do not leave boundary rules, forbidden drift, required references, or fidelity obligations implicit in surrounding prose.

  Downstream `sp-tasks` and `sp-implement` MUST be able to consume this section without reconstructing the rules from other artifacts.
-->

### Architecture Invariants

- [Boundary/framework invariant that implementation must preserve]
- [Compatibility or contract invariant that cannot be replaced by a parallel pattern]

### Boundary Ownership

- [Owning module/class/layer for the touched boundary]
- [Truth-owning or integration-owning surface that must remain authoritative]

### Forbidden Implementation Drift

- [Raw rewrite, parallel adapter, compatibility shim, or replacement pattern that is not allowed]
- [Architecture shortcut that would bypass the established boundary or contract]

### Required Implementation References

- [File, contract, or example implementation every implementer must inspect before touching this boundary]
- [Additional repository reference that anchors the existing pattern]

### Review Focus

- [Specific architecture-drift check reviewers must perform]
- [Compatibility, framework, or boundary check that must be verified before completion]

## Operational Consequence Design

| Obligation ID | State Machine / Ordering Decision | Concurrency And Idempotency | Recovery Path | Validation Evidence |
| --- | --- | --- | --- | --- |
| CA-### | [decision] | [lock, lease, queue, or ordering rule] | [retry, rollback, de-scope, or reopen path] | [command or manual check] |

## Dispatch Compilation Hints

<!--
  Record the minimum mandatory data a subagent execution packet compiler needs.
  Downstream execution MUST NOT infer these rules from loose context or surrounding prose.
-->

### Boundary Owner

- [Truth-owning module, service, or boundary that subagent execution must preserve]

### Required Packet References

- [File every subagent must inspect before changing this area]

### Packet Validation Gates

- [Command that must run before a subagent can claim completion]

### Task-Level Quality Floor

- [Feature-specific quality rule every subagent must inherit]

## Alignment Inputs

### Canonical References

- [Spec, ADR, policy, or repository document that shaped the plan]
- [Reference example or contract planners must keep in view]

### Input Risks From Alignment

- [Risk carried forward from alignment.md, or remove if none]
- [Unresolved item that planning is explicitly accepting or mitigating]

## Research Inputs

<!--
  Summarize only the research findings that materially changed the plan.
  This section exists to prove the plan consumed research.md instead of
  treating it as background reading.
-->

### Standard Stack

- [Chosen library / tool / framework and why it is the default for this plan]

### Don't Hand-Roll

- [Problem the plan must solve with an existing library, platform primitive, or repository pattern]

### Common Pitfalls

- [Failure mode or anti-pattern the plan is explicitly designed to avoid]

### Assumptions To Validate

- [Research assumption still not fully verified and how the plan contains or validates it]

### Environment / Dependency Notes

- [Tooling, runtime, service, or system dependency the plan assumes, including fallback if relevant]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

[Gates determined based on constitution file]

## Project Structure

### Documentation (this feature)

```text
.specify/features/[###-feature]/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output (/sp.plan command)
├── data-model.md        # Phase 1 output (/sp.plan command)
├── quickstart.md        # Phase 1 output (/sp.plan command)
├── contracts/           # Phase 1 output (/sp.plan command)
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Decision Preservation Check

<!--
  Before finalizing the plan, verify that every locked planning decision is
  represented in the plan summary, technical context, design artifacts,
  refinement checkpoint, valid blocker, or user-confirmed deferral contract.
  If something is covered by a user-confirmed deferral, record confirmation
  source, exact excluded behavior, residual risk, reopen or stop condition, and
  downstream artifact instead of silently dropping it.
-->

- [Locked decision] -> [Where it appears in the plan]
- [Locked decision] -> [Mitigation, defer note, or follow-up artifact]
- [Implementation constitution rule] -> [Where tasks and implementation must preserve it]

## Research Adoption Check

<!--
  Before finalizing the plan, verify that the consequential findings from
  research.md are represented in technical context, design artifacts, task
  sequencing assumptions, or explicit validation work.
-->

- [Research finding] -> [Where the plan uses it]
- [Research warning or pitfall] -> [How the plan mitigates it]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
