# Rule-Carrying Task Execution Design

**Date:** 2026-04-23
**Status:** Proposed
**Owner:** Codex

## Summary

This design upgrades `spec-kit-plus` from a partially rule-aware workflow into a fully rule-carrying multi-agent execution system.

The approved direction is not to copy the full constitution text into every task. Instead, the system should keep `constitution.md` and `plan.md` as the canonical rule sources, preserve task-level guardrails in `tasks.md`, and compile every delegated unit of work into a structured `WorkerTaskPacket` before dispatch.

The central requirement is strict:

- no native child agent
- no delegated lane
- no sidecar runtime worker

may begin work from raw task text alone when the work is subject to architectural, quality, validation, or boundary constraints.

Every delegated execution path must receive a compiled task packet that carries the task objective, applicable hard rules, required references, forbidden drift, validation gates, and done criteria. If a packet cannot be compiled completely, dispatch must fail closed.

This design is shared by default across supported CLI integrations. Integration-specific logic should only render or transport the compiled packet through that integration's native delegation surface.

## Problem Statement

`spec-kit-plus` already contains important guardrail ideas:

- project-level constitution rules under `.specify/memory/constitution.md`
- feature-level `Implementation Constitution` in `plan.md`
- implementation guardrail phases in `tasks.md`
- analysis checks for boundary guardrail drift

However, the execution chain still has a structural gap:

1. The leader agent can know the rules.
2. The planning artifacts can preserve the rules.
3. The delegated child agent can still receive only a task summary or batch summary.
4. The child agent then fills in missing standards from its default instincts or local pattern imitation.

This produces two repeated failures:

1. Code quality varies because task execution rules are not guaranteed to travel with the delegated work unit.
2. Execution efficiency degrades because child agents repeatedly rediscover boundaries, validation expectations, and reference files that should have been precompiled for them.

The root problem is not that the repository lacks constitutions or guardrails. The root problem is that the system does not yet treat rule transmission as a first-class execution requirement.

## Goals

- Make rule transmission mandatory for all delegated execution paths.
- Keep canonical rule authoring in `constitution.md` and `plan.md` rather than duplicating rule text across many tasks.
- Preserve task-level guardrails in `tasks.md` so planning remains inspectable.
- Compile a deterministic `WorkerTaskPacket` for each delegated task before dispatch.
- Fail closed when the packet is incomplete or underspecified.
- Make the packet schema shared across supported CLI integrations.
- Keep integration-specific logic thin and limited to capability detection, packet rendering, and transport.
- Improve child-agent throughput by replacing repeated repository rediscovery with precompiled task context.
- Make delegated execution auditable at both dispatch time and join-point completion time.

## Non-Goals

- Do not copy the full constitution into every task body in `tasks.md`.
- Do not replace `constitution.md`, `plan.md`, or `tasks.md` as the canonical planning artifacts.
- Do not make delegated workers responsible for discovering missing rules from the repository when the leader should have compiled them.
- Do not add a second parallel rules system that drifts from the constitution and plan.
- Do not make this design Codex-only.
- Do not force every integration to expose the same user-facing runtime surface.

## User-Approved Decisions

This design reflects the following explicit decisions made during design review:

1. The solution should be shared across integrations by default rather than implemented as a Codex-only optimization.
2. Rule transmission should use a hard-fail model, not best-effort injection.
3. The best architecture is a compiled worker contract, not full rule duplication inside every task.
4. `constitution.md` remains the global rule source.
5. `plan.md` remains the feature-level rule source through `Implementation Constitution`.
6. `tasks.md` remains the task decomposition and guardrail anchor, but not the final execution payload.
7. Native child agents should receive a compiled task packet rather than a loose task description.

## Architecture Overview

The design has four layers.

### 1. Canonical Rule Sources

These remain the authoring sources for constraints:

- `.specify/memory/constitution.md`
- `plan.md`
- `tasks.md`

Responsibilities:

- `constitution.md` defines project-wide MUST and SHOULD rules.
- `plan.md` defines feature-specific architecture invariants, boundary ownership, forbidden drift, required references, and review focus.
- `tasks.md` defines execution ordering, write-scope hints, validation anchors, and task decomposition.

### 2. Dispatch Compilation Layer

This new shared layer converts planning artifacts into execution-ready packets.

Responsibilities:

- resolve the applicable rules for a given task
- select the minimum required references for that task
- derive task-local hard rules from global and feature-level constraints
- derive validation gates and done criteria
- validate completeness before dispatch

This layer is the architectural center of the design. Rule transmission is no longer an informal prompt-building step. It becomes a typed compilation step.

### 3. Delegation Transport Layer

This layer sends the compiled packet through the active execution surface:

- native delegated subagents
- native multi-agent helpers
- sidecar runtime workers

Responsibilities:

- render the packet into integration-specific transport format
- preserve packet structure and identifiers
- record dispatch artifacts for later audit

### 4. Join-Point Verification Layer

This layer validates child-agent outputs against the packet that authorized the work.

Responsibilities:

- ensure the child stayed inside write scope
- ensure validation gates were run
- ensure required references were acknowledged
- reject results that violate forbidden drift or omit required evidence

## Canonical Execution Principle

Delegated workers must execute from compiled task contracts, not from inferred background context.

In practice this means:

- the leader may read the constitution, plan, and tasks
- the child may receive only the relevant compiled subset
- the child must not be expected to reconstruct the rule set from repository exploration

The leader remains responsible for compiling the contract. The child remains responsible for honoring it.

## WorkerTaskPacket Schema

Every delegated task must compile into one structured packet.

Recommended canonical schema:

```yaml
packet_version: 1
feature_id: "123-auth"
task_id: "T017"
story_id: "US1"
objective: "Implement login/logout service while preserving the existing session authority boundary"
scope:
  write_scope:
    - "src/services/auth_service.py"
    - "tests/unit/test_auth_service.py"
  read_scope:
    - "src/contracts/auth.py"
    - "src/services/session_store.py"
required_references:
  - path: "src/contracts/auth.py"
    reason: "public contract compatibility must be preserved"
  - path: "src/services/session_store.py"
    reason: "authoritative session lifecycle pattern"
hard_rules:
  - "Every public function added or changed must have direct test coverage"
  - "External calls must include explicit timeout and failure handling"
  - "Do not introduce a parallel service path outside the declared boundary owner"
forbidden_drift:
  - "Do not bypass session_store as the authority for session lifecycle"
  - "Do not create a second authentication stack or adapter chain"
validation_gates:
  - "pytest tests/unit/test_auth_service.py"
  - "ruff check src/services/auth_service.py tests/unit/test_auth_service.py"
done_criteria:
  - "login/logout behavior implemented"
  - "happy path and edge-case tests pass"
  - "no new lint warnings"
handoff_requirements:
  - "return changed files"
  - "return validation command results"
  - "return blockers or known limitations"
dispatch_policy:
  mode: "hard_fail"
  must_acknowledge_rules: true
```

The packet should stay compact, but every field above exists for a different failure mode:

- `objective` prevents ambiguous task interpretation
- `write_scope` prevents overlapping, wandering edits
- `required_references` prevents boundary rediscovery overhead
- `hard_rules` prevents rule loss
- `forbidden_drift` prevents parallel architecture creation
- `validation_gates` prevents unverifiable completion claims
- `done_criteria` prevents soft completion drift

## Compilation Model

The compiler should merge constraints in a fixed precedence order.

### Precedence Order

1. Task-specific guardrails from `tasks.md`
2. Feature-specific rules from `plan.md` `Implementation Constitution`
3. Project-wide rules from `.specify/memory/constitution.md`

This ordering allows a task to become more specific without weakening a higher-level rule.

### Compilation Inputs

For each task, the compiler should read:

- the task record and phase metadata from `tasks.md`
- the feature's `Implementation Constitution`
- any `Locked Planning Decisions`
- applicable validation notes from `quickstart.md`, `contracts/`, `research.md`, or `references.md`
- the project constitution if present

### Compilation Outputs

For each task, the compiler must produce:

- `objective`
- `write_scope`
- `required_references`
- `hard_rules`
- `forbidden_drift`
- `validation_gates`
- `done_criteria`

If any mandatory field cannot be produced with repository-backed evidence, compilation must fail.

## Hard-Fail Dispatch Contract

The system must fail closed on missing rule transmission.

Dispatch must be blocked when any of the following is true:

- the task has no reliable `write_scope`
- the task touches a boundary-sensitive area but lacks `required_references`
- the task has feature-level forbidden drift but the packet omits it
- the packet still relies on indirect wording such as "see constitution.md" instead of carrying the applicable rules directly
- the task requires validation but `validation_gates` are empty
- the packet cannot identify completion criteria that the leader can verify at join point

This should be treated as a runtime error, not a warning.

Recommended stable issue family for execution-time auditing:

- `DP1`: dispatch packet missing compiled hard rules
- `DP2`: dispatch packet missing required references or forbidden drift
- `DP3`: child completion missing required validation evidence

## Child-Agent Execution Contract

Every child agent must explicitly acknowledge the packet before substantive work begins.

Minimum required acknowledgements:

- objective understood
- write scope understood
- required references inspected
- forbidden drift understood
- validation gates understood

The child agent must not treat packet rules as optional suggestions.

### Required Child Result Shape

Every child completion should return a structured result equivalent to:

```yaml
status: success | blocked | failed
task_id: "T017"
changed_files:
  - "src/services/auth_service.py"
  - "tests/unit/test_auth_service.py"
rule_acknowledgement:
  required_references_read: true
  forbidden_drift_respected: true
validation_results:
  - command: "pytest tests/unit/test_auth_service.py"
    status: "passed"
  - command: "ruff check src/services/auth_service.py tests/unit/test_auth_service.py"
    status: "passed"
summary: "Implemented login/logout flow and tests"
blockers: []
```

Join-point logic must reject completions that do not satisfy the result schema.

## Artifact and Module Design

The shared implementation should live outside any one integration.

Recommended modules:

- `src/specify_cli/execution/packet_schema.py`
- `src/specify_cli/execution/packet_compiler.py`
- `src/specify_cli/execution/packet_validator.py`
- `src/specify_cli/execution/packet_renderer.py`
- `src/specify_cli/execution/result_schema.py`
- `src/specify_cli/execution/result_validator.py`

Recommended responsibilities:

- `packet_schema.py`: canonical packet types and enums
- `packet_compiler.py`: merge artifact inputs into packets
- `packet_validator.py`: hard-fail completeness and rule-carry checks
- `packet_renderer.py`: integration-neutral render helpers plus integration handoff primitives
- `result_schema.py`: canonical delegated-result types
- `result_validator.py`: join-point validation against packet expectations

## Template Changes

The planning templates should change only where they strengthen compilation quality.

### `plan-template.md`

Keep `Implementation Constitution` as the feature rule source and add a compact `Dispatch Compilation Hints` section that captures:

- boundary owner
- required references
- forbidden drift
- mandatory validation gates
- feature-level quality floor when it materially shapes delegated work

This section should exist to improve deterministic compilation, not to duplicate the rest of the plan.

### `tasks-template.md`

Keep `Phase 0: Implementation Guardrails`, but strengthen task generation so every implementation task has enough information for compilation:

- objective
- write-scope hints
- dependency gate
- validation anchor
- applicable guardrail mapping

Do not inline the full constitution under every task. Instead, add a task-level guardrail registry or index so the compiler can resolve which rule set attaches to which task.

### `implement.md`

Strengthen the current pre-dispatch logic so the leader is not merely asked to think through guardrails. The leader must compile and validate the packet before any delegated work begins.

The new hard rule should be:

- dispatch only from validated `WorkerTaskPacket`
- never dispatch from raw task text alone

### `analyze.md`

Keep existing `BG1`, `BG2`, and `BG3` checks. Extend the analysis family to report dispatch-compilation failures and missing execution evidence using the `DP1` to `DP3` codes.

## Integration Responsibilities

Integrations should share the same packet schema and compilation logic.

They should differ only in:

- capability detection
- native delegation transport
- packet rendering format
- result collection mechanism

Examples:

- Codex native delegation can render the packet into a structured `spawn_agent` payload.
- Cursor or other delegated systems can render the same packet into their own task transport format.
- Sidecar runtime workers can receive the same packet serialized to runtime state or work-item files.

No integration should invent its own packet semantics.

## Efficiency Model

This design is a quality improvement and an efficiency improvement at the same time.

Without compiled packets, child agents repeatedly spend time on:

- rediscovering which files define the current boundary
- guessing which quality rules apply
- guessing which validation commands matter

With compiled packets:

- repository reading narrows to `required_references`
- rule application narrows to `hard_rules`
- validation narrows to `validation_gates`
- join-point review narrows to packet-backed done criteria

This reduces duplicated reasoning and makes parallel execution less wasteful.

## Risks

### 1. Over-Compilation

If packets are too large, the system can recreate the same context bloat it is trying to avoid.

Mitigation:

- compile only task-relevant rules
- preserve file references where the child truly must inspect code
- keep the packet schema narrow and typed

### 2. Under-Specified Write Scope

If write scopes are too vague, the packet cannot safely support delegation.

Mitigation:

- require stronger write-scope derivation in `tasks.md`
- fail closed when write scope is not sufficiently precise

### 3. Rule Drift Between Artifacts

If the constitution, plan, and tasks disagree, packet compilation becomes unstable.

Mitigation:

- keep `analyze` responsible for detecting drift before implementation
- make compilation report the exact missing or conflicting source layer

## Rollout Recommendation

The rollout should happen in this order:

1. Add shared packet schema, compiler, and validator modules.
2. Strengthen `plan-template.md` and `tasks-template.md` so compilation inputs are explicit.
3. Update `implement` to require validated packets before dispatch.
4. Update one native integration path and one sidecar/runtime path to prove the shared contract.
5. Extend `analyze` with `DP1` to `DP3`.
6. Expand remaining integrations onto the shared packet transport model.

This order keeps the canonical rule sources stable while moving dispatch logic onto the new architecture incrementally.

## Decision

The approved architecture is `Compiled Worker Contract` with hard-fail rule transmission.

`constitution.md`, `plan.md`, and `tasks.md` remain the canonical planning sources. Delegated execution must operate on a compiled `WorkerTaskPacket` generated from those sources. Any delegated task lacking a complete packet must be rejected before dispatch.
