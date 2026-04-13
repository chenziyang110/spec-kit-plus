# Multi-CLI Agent Collaboration Design

**Date:** 2026-04-13
**Status:** Partially Implemented (Milestone 1 slice)
**Owner:** Codex

## Summary

This design defines the target architecture and Milestone 1 rollout direction for expanding `spec-kit-plus` from a largely single-agent integration model with one Codex-specific durable runtime surface toward a multi-CLI collaboration system for analysis, planning, task generation, execution, explanation, and debugging across multiple agent integrations.

The approved direction is not to force every integration through a single product surface. Users should continue entering through the native command or skill surface of their chosen CLI integration. Multi-agent collaboration should be selected automatically by workflow policy, prefer the integration's native delegation model when available, and fall back to a `spec-kit-plus` sidecar runtime when the native runtime cannot provide the required coordination.

The first target integrations are:

- `gemini`
- `claude`
- `copilot`
- `codex`

The key structural decision is to refactor the existing `codex_team` implementation into a generic orchestration core rather than building a parallel system from scratch.

## Milestone 1 Delivery Update (2026-04-13)

Milestone 1 deliverables now present in the codebase:

- generic orchestration core under `src/specify_cli/orchestration/`
- unified strategy language (`single-agent`, `native-multi-agent`, `sidecar-runtime`) routed first through `implement`
- Codex compatibility surface preserved via `specify team`
- first-release adapter skeletons for Claude, Gemini, and Copilot (plus Codex) in integration modules

Remaining milestones in this design (`specify`, `plan`, `tasks`, `explain`, `debug` full migration and runtime maturity) are still future work.

## Problem Statement

`spec-kit-plus` currently supports many AI integrations, but its multi-agent behavior is uneven:

- most integrations install command or skill surfaces only
- `implement` has begun to describe strategy selection, but other workflows do not share a common collaboration policy
- durable runtime behavior is concentrated in the Codex-only `specify team` surface
- runtime state, event handling, backend detection, and worker lifecycle are still shaped around a Codex-specific model

This causes four practical problems:

1. Multi-agent behavior is not a first-class cross-workflow policy.
2. Integrations cannot share a common execution decision model.
3. Existing durable runtime assets are too tightly coupled to Codex naming and state layout.
4. Cross-platform durable fallback is under-specified, especially for Windows-native environments.

The design must address those problems without erasing the value of each integration's native agent system.

## Goals

- Add a multi-agent collaboration architecture that works across multiple CLI integrations.
- Preserve native command or skill entrypoints for each integration.
- Make collaboration auto-triggered by workflow policy rather than opt-in by default.
- Prefer native multi-agent delegation when an integration supports it.
- Fall back to a `spec-kit-plus` sidecar runtime when native delegation is unavailable or insufficient.
- Support cross-platform first-release behavior, including Windows-native environments.
- Refactor `codex_team` into a reusable orchestration core rather than leaving it as an isolated implementation.
- Extend collaboration policy across `specify`, `plan`, `tasks`, `implement`, `explain`, and `debug`.
- Keep `specify team` fully compatible for existing Codex projects while moving its internals onto the new core.

## Non-Goals

- Do not replace each integration's native user-facing command or skill syntax with a single universal surface.
- Do not expose `specify team` as the required primary entrypoint for non-Codex integrations in the first release.
- Do not claim identical collaboration depth for every integration on day one.
- Do not force all workflows into multi-agent execution when the work shape does not justify it.
- Do not discard the current Codex runtime assets and rebuild everything from zero.

## User-Approved Constraints

The design is based on the following explicit decisions:

1. First release scope should cover a broad multi-CLI direction rather than a Codex-only feature.
2. The first milestone focus should be executable backend adaptation rather than only packaging or abstract policy.
3. The primary user-facing surface must remain agent-native rather than a new unified `specify team` surface.
4. Collaboration should eventually cover the full workflow surface, including `specify`, `plan`, `tasks`, `implement`, `explain`, and `debug`.
5. Multi-agent triggering should be automatic by default.
6. Native multi-agent capabilities should be preferred first, with `spec-kit-plus` sidecar/runtime fallback when needed.
7. The sidecar/runtime must support cross-platform first release behavior, including Windows-native support.
8. Existing `codex_team` assets should be refactored into the generic runtime core rather than replaced wholesale.

## Architecture Overview

The proposed architecture has three layers.

### 1. Workflow Policy Layer

This layer decides whether a workflow invocation should stay single-agent, use native multi-agent delegation, or escalate to a sidecar runtime.

It is responsible for:

- command-specific collaboration eligibility
- workload-shape evaluation
- conflict and join-point analysis
- environment-aware strategy selection
- fallback recording when a native route fails

This layer should be shared across:

- `specify`
- `plan`
- `tasks`
- `implement`
- `explain`
- `debug`

### 2. Orchestration Core

This is the generic collaboration kernel extracted from the current `codex_team` implementation.

It is responsible for:

- canonical state and event models
- session, batch, lane, and task coordination
- join-point handling
- structured results and recovery
- sidecar/runtime lifecycle
- backend abstraction across platforms

This core must not encode integration-specific command syntax or assume one runtime model.

### 3. Runtime Adapters

Each integration gets an adapter that translates the generic collaboration model into that integration's native delegation model when possible.

Initial adapters:

- `GeminiAdapter`
- `ClaudeAdapter`
- `CopilotAdapter`
- `CodexAdapter`

Each adapter is responsible for:

- capability detection
- native delegation planning
- native task dispatch
- result collection
- fallback reasoning

## Execution Decision Model

Every collaboration-aware workflow should produce exactly one execution strategy decision:

- `single-agent`
- `native-multi-agent`
- `sidecar-runtime`

The decision should be based on a consistent set of inputs:

- integration capability snapshot
- command type
- workload shape
- write-scope and shared-surface conflict analysis
- backend availability and runtime health

The decision order is fixed:

1. Determine whether the work justifies multi-agent execution at all.
2. If yes, attempt native multi-agent delegation first.
3. If native delegation is unavailable or unsuitable, attempt sidecar/runtime execution.
4. If that also fails, downgrade to `single-agent` and record the downgrade reason.

Every decision should be persisted as an inspectable record so later explanation, debugging, and auditing do not depend on prompt inference.

## Orchestration Core Boundaries

The new generic core should live under a namespace such as:

- `src/specify_cli/orchestration/`

Recommended modules:

- `capabilities.py`
- `policy.py`
- `models.py`
- `events.py`
- `state_store.py`
- `sidecar/`

Suggested canonical models:

- `CapabilitySnapshot`
- `ExecutionDecision`
- `Session`
- `Batch`
- `Lane`
- `TaskUnit`
- `ArtifactResult`
- `JoinPoint`

The critical abstraction change is to model generic execution channels as `lanes`, not `workers`.

That keeps the core neutral:

- in native delegation mode, a lane can represent a native subagent or delegated task handle
- in sidecar mode, a lane can represent a real worker process

The existing Codex-specific concept of a worker should become a projection in the Codex compatibility layer, not the canonical runtime model.

## State Model and Persistence

The new canonical runtime state root should be:

- `.specify/orchestration/`

Recommended subtrees:

- `sessions/`
- `batches/`
- `lanes/`
- `tasks/`
- `artifacts/`
- `events/`
- `checkpoints/`

The event stream should be append-only and minimally cover:

- `session.created`
- `policy.selected`
- `batch.planned`
- `lane.started`
- `task.delegated`
- `task.progress`
- `artifact.emitted`
- `join.waiting`
- `batch.completed`
- `fallback.invoked`
- `session.completed`
- `session.failed`

This event model becomes the shared truth for runtime resumes, explanation output, failure analysis, and future UI surfaces.

## Compatibility Strategy for Existing Codex Projects

`specify team` remains the official Codex surface for compatibility.

In the first migration stages:

- `src/specify_cli/codex_team/` remains present
- the CLI surface and generated assets remain compatible
- the implementation progressively redirects to the generic orchestration core

This may temporarily require dual-read or dual-write compatibility between:

- `.specify/codex-team/`
- `.specify/orchestration/`

The important release contract is:

- existing Codex projects keep working
- new generic runtime behavior is introduced without breaking the current Codex interface

## Cross-Platform Backend Strategy

The durable fallback runtime must not be designed as `tmux-only`.

The backend model should support three levels:

### 1. Native Adapter Execution

Preferred whenever the integration can host multi-agent delegation reliably.

### 2. Interactive Sidecar Backend

For visible pane-based durable coordination:

- `tmux` on macOS, Linux, and WSL
- `psmux` on Windows-native where available

### 3. Portable Process Backend

A pane-free managed-process backend that can run across platforms, including Windows-native, when pane-based tooling is unavailable or unsuitable.

This portable backend is essential to satisfy the approved cross-platform first-release requirement.

## Workflow Integration

Each collaboration-aware workflow should define three things:

- eligibility
- lane plan
- join policy

### `specify`

Purpose of collaboration:

- analyze the feature from multiple perspectives before writing the spec package

Candidate lanes:

- repository and local context analysis
- external references and supporting material analysis
- ambiguity, risk, and gap analysis

Required join points:

- before capability decomposition
- before writing `spec.md` and `alignment.md`

### `plan`

Purpose of collaboration:

- split design work into parallel design-analysis lanes

Candidate lanes:

- research
- data model
- contracts
- quickstart and validation scenarios

Required join points:

- before final constitution and risk re-check
- before writing the consolidated implementation plan

### `tasks`

Purpose of collaboration:

- split planning decomposition and safety analysis

Candidate lanes:

- story and phase decomposition
- dependency graph analysis
- write-set and parallel safety analysis

Required join points:

- before writing `tasks.md`
- before emitting canonical parallel batches and join points

### `implement`

Purpose of collaboration:

- execute ready task batches with explicit join-point coordination

Candidate lanes:

- direct execution lanes derived from `tasks.md` ready batches

Required join points:

- after every parallel batch
- before shared registration surfaces are touched
- before stage completion and final verification

This is the main command that should use durable sidecar/runtime behavior most aggressively.

### `explain`

Purpose of collaboration:

- validate explanation accuracy across related artifacts when needed

Candidate lanes:

- primary artifact reading
- supporting artifact cross-check

Required join points:

- before rendering the final explanation

Default behavior should remain conservative and often single-agent.

### `debug`

Purpose of collaboration:

- collect evidence and compare hypotheses in parallel when useful

Candidate lanes:

- reproduction
- code-path inspection
- hypothesis comparison

Required join points:

- before any code-modifying fix path begins
- before final verification and human confirmation

Debug must remain more conservative than implementation. Investigation can fan out; fixing should converge back to a single writer path.

## Adapter Design

### `GeminiAdapter`

Role:

- native-first adapter for Gemini task and agent delegation

Expected strengths:

- multi-agent analysis
- planning decomposition
- moderate execution fan-out

Fallback triggers:

- missing stable native delegation
- insufficient result collection
- complex durable join-point coordination

### `ClaudeAdapter`

Role:

- native-first adapter with strong support for structured delegation and controlled execution

Expected strengths:

- full workflow coverage
- strong planning and execution delegation

Fallback triggers:

- missing runtime support in the current surface
- durable coordination or recovery requirements beyond the native path

### `CopilotAdapter`

Role:

- native-first but conservative adapter

Expected strengths:

- analysis and planning collaboration
- lighter explanation and evidence-gathering workflows

More limited first-release scope:

- heavy durable implementation coordination should fall back sooner than Gemini or Claude

### `CodexAdapter`

Role:

- compatibility-focused adapter that continues to support the existing Codex surface while adopting the generic core internally

Expected strengths:

- strongest early durable runtime support
- first adapter to fully exercise sidecar/runtime coordination

Special requirement:

- preserve `specify team` compatibility and generated asset behavior

## Proposed Adapter Interface

Each adapter should implement a common interface such as:

- `detect_capabilities(project_root)`
- `supports_command(command_name, workload_shape)`
- `plan_native_lanes(command_name, lane_plan)`
- `dispatch_native(plan)`
- `poll_native(handle)`
- `collect_results(handle)`
- `should_fallback(error, workload_shape)`

This keeps the orchestration core integration-neutral while still allowing each adapter to describe real runtime limits.

## Migration of Existing `codex_team` Modules

The following current responsibilities should move into the generic orchestration core:

- state paths
- runtime state models
- event persistence
- session lifecycle coordination
- task, lane, and mailbox-like coordination primitives
- backend detection and lifecycle management

The following should remain in a Codex compatibility namespace initially:

- `specify team` command surface
- Codex-specific installer assets
- Codex-specific notify-hook behavior

This keeps release risk lower while still moving the actual runtime brain into a reusable core.

## Testing Strategy

The design requires a broader test matrix than the current Codex-only surface.

Minimum coverage should include:

- orchestration core model and state tests
- event-log and recovery tests
- backend registry tests, including Windows-native detection behavior
- adapter capability-detection tests for Gemini, Claude, Copilot, and Codex
- workflow policy tests for each collaboration-aware command
- fallback tests from native delegation to sidecar/runtime to single-agent
- Codex compatibility tests for existing `specify team` behavior
- non-Codex isolation tests proving `specify team` is still not advertised as the primary surface elsewhere

## Risks

### 1. Premature Symmetry Risk

If all integrations are forced into identical collaboration depth too early, the architecture will describe parity that the actual runtimes cannot deliver.

### 2. Migration Risk

Refactoring `codex_team` into a generic core can break existing Codex behavior if state-path and CLI compatibility are not handled carefully.

### 3. Windows Runtime Risk

Cross-platform first release is more demanding than the current tmux-centric design. The portable process backend is not optional if Windows-native support must be real.

### 4. Over-Eager Auto-Parallelism Risk

If the workflow policy escalates too easily, users will see unnecessary fan-out, more moving pieces, and harder-to-understand failures.

## Recommended Delivery Sequence

### Milestone 1: Generic Orchestration Skeleton

Build the shared runtime skeleton before broad feature behavior changes.

Deliverables:

- generic orchestration core
- canonical models and event flow
- backend registry
- Codex compatibility layer wired to the new core
- adapter skeletons for Gemini, Claude, Copilot, and Codex
- first command integrated with unified policy, starting with `implement`

### Milestone 2: Analysis and Planning Workflows

Extend the shared policy and adapter model into:

- `specify`
- `plan`
- `tasks`
- `explain`

### Milestone 3: Execution and Debug Runtime Maturity

Deepen:

- durable `implement` execution
- debug evidence fan-out with single-writer convergence
- portable process backend support

### Milestone 4: Expansion and Documentation

Extend the pattern to additional integrations and finish user-facing guidance, upgrade documentation, and test coverage.

## Initial Implementation Cut

The recommended first implementation cut is intentionally smaller than the full design:

- create the orchestration namespace and core models
- refactor current Codex runtime state and backend logic into the generic core
- keep `specify team` compatible
- add capability snapshots and adapter skeletons for Gemini, Claude, Copilot, and Codex
- wire `implement` into the unified strategy-selection path first

This is the smallest change set that moves the repository toward the approved architecture without pretending the entire surface has already been migrated.

## Decision

Proceed with a generic orchestration core plus runtime adapters.

The approved end state is:

- native agent entrypoints remain primary
- collaboration is auto-triggered by shared workflow policy
- native delegation is preferred when available
- a `spec-kit-plus` sidecar/runtime provides durable fallback
- the runtime is cross-platform from the first release, including Windows-native support
- the current `codex_team` implementation is refactored into the generic collaboration core rather than replaced outright
