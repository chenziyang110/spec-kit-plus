# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

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
  Promote architecture and boundary rules that implementation must not violate.
  This section turns "technical background" into explicit execution constraints.
  Use it for framework ownership, boundary patterns, forbidden rewrites, required
  reference files, and review checks that downstream task generation must preserve.
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

## Dispatch Compilation Hints

<!--
  Record the minimum data a subagent execution packet compiler needs so
  downstream execution never has to infer boundary rules from loose context.
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
specs/[###-feature]/
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
  represented in the plan summary, technical context, design artifacts, or
  explicit follow-up work. If something is intentionally deferred, say so here
  instead of silently dropping it.
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
