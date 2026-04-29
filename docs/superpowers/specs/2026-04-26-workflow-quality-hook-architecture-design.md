# Workflow Quality Hook Architecture Design

**Date:** 2026-04-26  
**Status:** Proposed  
**Owner:** Codex

## Summary

This design introduces a first-party quality-hook architecture for `spec-kit-plus`.

The goal is not to copy GSD's entire hook model. The goal is to convert the
repository's existing workflow contracts from prompt-only guidance into
observable, enforceable runtime checks.

Today, `spec-kit-plus` already has:

- shared workflow templates with strong written rules
- extension hooks stored in `.specify/extensions.yml`
- Codex native hooks through `hooks.json`
- durable state artifacts such as `workflow-state.md`, `implement-tracker.md`,
  quick-task `STATUS.md`, debug session files, `WorkerTaskPacket`, and
  `WorkerTaskResult`

What it does not yet have is a unified quality layer that can:

- verify the required state is present before a workflow continues
- checkpoint recovery context before compaction or loss of chat context
- fail closed when execution tries to skip required gates
- reuse the same quality rules across integrations instead of re-expressing
  them in every template

The approved direction is a state-first hook system with three layers:

1. a shared `specify` quality-hook engine that owns cross-CLI workflow truth
2. native integration adapters that can emit richer event timing when the host
   CLI supports native hooks
3. existing extension hooks preserved as an ecosystem automation surface, not
   as the product's primary quality-enforcement layer

## Problem Statement

The repository already encodes a high workflow quality bar, but much of that
quality bar exists only as text in templates.

Examples:

- `sp-specify`, `sp-plan`, and `sp-tasks` say they must create or resume
  `workflow-state.md`.
- `sp-analyze` says it is the gate before implementation.
- `sp-implement` says it must maintain `implement-tracker.md`, compile and
  validate `WorkerTaskPacket`, and only accept delegated work through validated
  `WorkerTaskResult` handoffs.
- `sp-quick` and `sp-debug` define resumable state files as the source of truth.
- brownfield flows say they must respect project-map freshness.

These are strong rules, but many are not yet enforced by a canonical runtime
surface.

That creates five failure modes:

1. phase drift: a workflow continues even though upstream state says it should
   reopen another stage
2. artifact drift: required artifacts are missing or stale, but the workflow
   continues anyway
3. delegation drift: worker dispatch or join-point acceptance proceeds without a
   complete packet/result contract
4. context loss: the agent approaches compaction or session interruption without
   writing enough state for honest recovery
5. cross-CLI inconsistency: one integration can enforce quality at runtime while
   another only inherits prompt wording

## Goals

- Add a first-party quality-hook system that improves workflow output quality.
- Convert critical prompt rules into machine-checkable state transitions.
- Preserve shared workflow semantics across Codex, Claude, Gemini, Cursor, and
  other supported integrations.
- Introduce explicit checkpoint behavior for context pressure and recovery.
- Keep the design compatible with the current artifact model instead of creating
  a second source of truth.

## Non-Goals

- Do not turn `spec-kit-plus` into a generalized security sandbox first.
- Do not replace extension hooks with product hooks.
- Do not require every integration to support native hooks before quality
  enforcement becomes useful.
- Do not introduce a second project-state tree alongside existing workflow
  artifacts.
- Do not make token-count telemetry a hard requirement for all integrations.

## Current-State Assessment

The repository already contains several hook-like and state-enforcement
surfaces.

### What Already Exists

#### 1. Prompt-Level Workflow Contracts

The shared templates already define strong rules for:

- workflow phase locks through `workflow-state.md`
- brownfield freshness gates through `.specify/project-map/index/status.json`
- execution-state tracking through `implement-tracker.md`
- quick-task resumability through `.planning/quick/<id>-<slug>/STATUS.md`
- debug-session resumability through `.planning/debug/[slug].md`
- delegated execution through `WorkerTaskPacket` and `WorkerTaskResult`

#### 2. Extension Hooks

`HookExecutor` in `src/specify_cli/extensions.py` registers declarative hooks in
`.specify/extensions.yml`.

This is useful for extension automation, but it is intentionally prompt-facing.
It is not the correct place to store product-critical quality truth.

#### 3. Codex Native Hooks

The Codex/OMX runtime already manages native hook coverage for:

- `SessionStart`
- `PreToolUse`
- `PostToolUse`
- `UserPromptSubmit`
- `Stop`

These hooks already perform real work such as prompt triage, stop blocking,
session overlay, and tool-response inspection.

#### 4. Strong Delegation Validators

The repository already proves that code-level hard-fail contracts work:

- `packet_validator.py` enforces `DP1` and `DP2`
- `result_validator.py` enforces `DP3`

This is the strongest existing evidence that more workflow rules should move out
of prompt prose and into runtime validators.

#### 5. Partial Compaction Support

The repository partially supports recovery after context loss:

- `workflow-state.md` explicitly says it is the resume source after compaction
- `implement-tracker.md`, `STATUS.md`, and debug sessions are resume authorities
- Codex/OMX overlay injects compaction-survival instructions
- Codex/OMX setup can seed `model_auto_compact_token_limit`

But this is still incomplete because there is no unified product hook that
actively checkpoints state when context pressure rises.

## Design Principles

### 1. State First

The hook system should validate or write existing state artifacts rather than
inventing a new state layer.

### 2. Cross-CLI Core, Native Adapters at the Edge

Product quality rules should live in a shared engine.
Native integration hooks should emit earlier or richer signals where available.

### 3. Fail Closed for Integrity, Not for Everything

The system should block when workflow truth would become invalid, for example:

- `sp-implement` without cleared analyze gate
- delegated execution without a validated packet
- success handoff without validation evidence
- stale brownfield navigation where the touched area cannot be trusted

It should warn rather than block for lower-signal advisory events.

### 4. Structural Checkpointing Beats Exact Token Counting

Exact token telemetry is not portable across integrations.
The shared system should support structural checkpoint triggers everywhere and
token-threshold triggers only where the runtime can supply them.

### 5. One Product Quality Surface, One Extension Surface

Extension hooks remain for optional ecosystem automation.
First-party quality hooks remain for product truth and gatekeeping.

## Approved Direction

Introduce a shared `specify hook` quality engine and route the existing
workflow/state contracts through it.

### Quality Hook Layers

#### Layer 1: Shared Workflow Quality Hooks

This is the primary product layer.

It should be implemented as a `specify hook` command surface with canonical
events and validators that can run in any integration.

Example events:

- `workflow.preflight`
- `workflow.state.validate`
- `workflow.artifacts.validate`
- `workflow.gate.validate`
- `workflow.checkpoint`
- `delegation.packet.validate`
- `delegation.join.validate`
- `project_map.refresh.validate`
- `project_map.mark_dirty`

#### Layer 2: Native Integration Adapters

This layer adapts host-native events into the shared engine.

For Codex, the current native events already provide a strong starting point:

- `SessionStart`
- `PreToolUse`
- `PostToolUse`
- `UserPromptSubmit`
- `Stop`

This layer should call into the same shared quality rules instead of embedding a
second copy of product truth inside integration-specific code.

#### Layer 3: Extension Hooks

This layer remains separate and lower-authority.

It is for:

- Jira sync
- external automation
- follow-up commands
- optional workflows

It should not become the source of truth for phase gates, context checkpointing,
or delegated-execution acceptance.

## Hook Operation Model

Each hook should declare:

- `event_name`
- `scope`
- `severity`
- `required_inputs`
- `outputs`
- `failure_mode`

### Scope Types

- `observe`: collect or summarize facts only
- `warn`: surface a non-blocking issue
- `block`: prevent continuation until the state is repaired
- `repair`: write or normalize state before allowing continuation

### Severity Types

- `info`
- `warning`
- `high`
- `critical`

### Failure Modes

- `skip`: no-op because the integration cannot provide the signal
- `warn`: continue but mark reduced confidence
- `block`: stop the workflow
- `repair_then_continue`: write state and continue

## Required Hook Families

### 1. WorkflowPreflightHook

Purpose: stop workflows from entering with missing prerequisites.

Checks:

- correct upstream command and phase progression
- required source-of-truth artifact exists
- project-map freshness is sufficient for the touched area
- required testing/project-memory surfaces are present when the workflow
  contract says they matter

High-value use:

- block `sp-implement` when analyze gate is not cleared
- block brownfield `sp-fast` when the map is stale
- block `sp-quick` or `sp-debug` when their state workspace is missing after
  initialization should already exist

### 2. WorkflowStateHook

Purpose: verify that stage-state artifacts are created and updated when the
workflow contract requires them.

Targets:

- `workflow-state.md`
- `implement-tracker.md`
- `STATUS.md`
- debug session file

This hook should validate:

- source-of-truth file exists
- active command matches the current workflow
- phase mode is compatible
- next action and next command are populated when required

### 3. ArtifactCompletenessHook

Purpose: confirm that a workflow produced the minimum artifact set promised by
its contract.

Examples:

- `sp-specify`: `spec.md`, `alignment.md`, `context.md`, `workflow-state.md`
- `sp-plan`: `plan.md` plus constitution-sensitive companion artifacts
- `sp-tasks`: `tasks.md` with valid task format and downstream analyze handoff
- `sp-analyze`: gate result written back to `workflow-state.md`

### 4. AnalyzeGateHook

Purpose: prevent execution from self-authorizing around `sp-analyze`.

Rules:

- `sp-implement` may proceed only when workflow state records the analyze gate
  as cleared
- if `workflow-state.md` still points to `/sp.analyze`, `/sp.plan`,
  `/sp.tasks`, or `/sp.spec-extend`, execution blocks

### 5. ProjectMapFreshnessHook

Purpose: turn freshness from a template reminder into a real gate.

Shared behavior:

- inspect `.specify/project-map/index/status.json`
- map the touched area to required or review topics
- block or warn according to freshness and touched-area risk

Repair behavior:

- recommend or invoke `project-map complete-refresh` after successful refresh
- mark dirty when completion changes shared truth surfaces

### 6. ContextCheckpointHook

Purpose: proactively persist enough state to survive compaction, interruption,
or runtime loss.

This is the hook family that answers the context-shortage problem directly.

#### Current Support

Current support is partial:

- recovery artifacts exist
- Codex/OMX can seed auto-compact thresholds
- overlay includes compaction survival instructions

What is missing is a first-party checkpoint trigger that turns those facilities
into reliable product behavior.

#### Required Checkpoint Targets

Shared minimum targets:

- active source-of-truth state file
- next action
- authoritative files
- blockers or open gaps
- validation status

Workflow-specific targets:

- `sp-specify` / `sp-plan` / `sp-tasks` / `sp-analyze`
  - write `workflow-state.md`
- `sp-implement`
  - write `implement-tracker.md`
  - ensure current batch, open gaps, blocker evidence, retry attempts, user
    execution notes, and resume decision are current
- `sp-quick`
  - write `STATUS.md`
  - ensure active lane, join point, fallback reason, blockers, recovery action,
    and resume decision are current
- `sp-debug`
  - write debug session file
  - ensure current hypothesis, truth owner, closed-loop break, evidence, and
    next probe are current

Optional native-adapter sinks:

- Codex/OMX notepad via `notepad_write_working`
- Codex/OMX state server via `state_write`
- project memory for high-signal cross-session facts

#### Trigger Model

The shared product layer should support structural triggers:

- before known compaction-risk transitions
- before long validation passes
- before join points
- before delegated fan-out
- before stop/interrupt handling
- after a large artifact synthesis step

Native adapters may add telemetry-aware triggers:

- token watermark crossed
- host emitted compaction or stop warning
- host reports context limit proximity

#### Trigger Policy

- If the runtime provides a trusted context-watermark signal, checkpoint when a
  configured threshold is crossed.
- If the runtime does not provide token telemetry, checkpoint at structural
  boundaries automatically.
- Do not block solely because token telemetry is unavailable.
- Block if the workflow cannot produce a minimal recovery checkpoint before a
  destructive transition.

### 7. DelegationPacketHook

Purpose: guarantee delegated execution starts from a real packet, not raw task
text.

Behavior:

- compile packet
- validate packet
- block dispatch on `DP1` or `DP2`

This should generalize the current `packet_validator.py` contract into a
workflow hook boundary.

### 8. JoinPointAcceptanceHook

Purpose: guarantee downstream work only continues after a valid delegated
handoff.

Behavior:

- normalize result
- validate against packet
- reject stale, placeholder, or incomplete result envelopes
- block join-point closure on `DP3`

This should generalize the current `result_validator.py` behavior into an
explicit orchestration gate.

### 9. QuickSessionHook

Purpose: keep quick-task resumability truthful.

Checks:

- `STATUS.md` exists once the task is initialized
- `STATUS.md` updates before major phase transitions
- leader-local fallback records concrete reason
- `index.json` remains derived, never the primary truth source

### 10. DebugSessionHook

Purpose: keep debug sessions evidence-led and resumable.

Checks:

- debug session file exists
- observer framing completed before deeper investigation
- next action and current hypothesis are current
- transition memo and truth-ownership state are preserved before code changes

### 11. CompletionDirtyMarkHook

Purpose: ensure quality workflows feed brownfield freshness truth back into the
navigation system.

Triggers:

- shared surface changed
- route/contract boundary changed
- runtime invariant changed
- verification surface changed

Behavior:

- mark project map dirty or require refresh completion

## Additional Hook Families From the Initial GSD-Inspired Backlog

The original backlog also included a more GSD-like hook set. Those hooks should
be included in the architecture, but they should not displace the quality-core
layers above.

They belong in a second band: security, operational recovery, and native-runtime
enhancement hooks.

### 12. ReadBoundaryGuardHook

Purpose: prevent agents from reading outside the intended repository or from
pulling sensitive local files that do not belong in normal workflow context.

Target behavior:

- deny or warn on attempts to read secrets, SSH keys, auth tokens, `.env`
  variants, or unrelated home-directory files
- enforce repository-root and declared worktree boundaries where the host
  integration exposes pre-tool-use events
- support path allowlists for canonical workflow/state artifacts that are always
  safe to read

Placement:

- native-adapter-first for integrations with pre-tool-use hooks
- shared policy configuration in the product layer so the denylist and
  allowlist are not duplicated per integration

### 13. PromptGuardHook

Purpose: detect prompt-level attempts to override workflow contracts, disable
required guardrails, or inject hostile instructions into native routing
surfaces.

Target behavior:

- detect high-confidence attempts to skip workflow gates such as
  "ignore analyze", "do not write state", or "bypass the testing gate"
- distinguish between benign user phrasing and true prompt-override attempts
- default to warn for low-confidence matches and block only for clear hostile
  override patterns

Placement:

- best-effort shared classifier
- stronger native integration at `UserPromptSubmit` where available

### 14. WorkflowBoundaryHook

Purpose: make phase transitions explicit and executable instead of relying only
on template prose.

Target behavior:

- enforce transition rules between planning-only, design-only, task-generation,
  analysis, and execution phases
- trigger required environment setup or cleanup when a phase boundary is crossed
- coordinate worktree/runtime initialization when execution moves from planning
  into active delegated work

This hook extends the narrower `WorkflowPreflightHook` and `AnalyzeGateHook`
from phase validation into transition management.

### 15. ContextMonitorHook

Purpose: watch context pressure and trigger `ContextCheckpointHook` before the
session loses critical execution truth.

Target behavior:

- consume token-watermark or auto-compact signals when the host runtime exposes
  them
- fall back to structural heuristics when token telemetry is unavailable
- emit advisory state for HUD/statusline surfaces and trigger proactive
  checkpoint writes

This hook is the monitor; `ContextCheckpointHook` remains the writer.

### 16. StatuslineHook

Purpose: expose current workflow state, batch, blockers, and context pressure in
a compact operator-facing status surface.

Target behavior:

- summarize active command, phase, current batch or lane, validation state,
  blocker count, and checkpoint urgency
- stay informational rather than becoming the source of workflow truth
- integrate naturally with Codex/OMX HUD-style surfaces while remaining
  optional for other integrations

### 17. SessionStateHook

Purpose: normalize cross-process state persistence so recovery does not depend
on chat memory or a single in-process runtime.

Target behavior:

- keep session-scoped and root-scoped state consistent
- persist ownership metadata for active workflow sessions
- support clean resume after compaction, crash, or process handoff

Much of this overlaps the current `implement-tracker.md`, `STATUS.md`, debug
session files, and OMX state/notepad surfaces. The hook formalizes when those
surfaces must be reconciled.

### 18. PhaseBoundaryHook

Purpose: execute explicit setup/cleanup behavior at workflow boundary changes.

Target behavior:

- initialize worktree/runtime state when execution begins
- finalize or prune temporary state when phases complete
- write boundary metadata that later hooks can inspect

This hook is especially relevant for sidecar runtime and multi-worker flows.

### 19. CommitValidationHook

Purpose: enforce last-mile quality rules before a commit is finalized.

Target behavior:

- validate commit message contract
- ensure required quality checks have actually run
- ensure the current workflow state is compatible with a commit attempt
- optionally refuse commits that still carry unresolved blocked state or stale
  dirty-map truth

Placement:

- repo-side git hook integration where available
- `specify` CLI pre-commit helper fallback for environments where git hook
  installation is not available or not desired

## Workflow Hook Map

### `sp-specify`

Recommended hooks:

- `workflow.preflight`
- `workflow.state.validate`
- `project_map.refresh.validate`
- `workflow.checkpoint`
- `workflow.artifacts.validate`

Checkpoint moments:

- immediately after `FEATURE_DIR` is known
- after capability decomposition
- before final artifact handoff

### `sp-plan`

Recommended hooks:

- `workflow.preflight`
- `workflow.state.validate`
- `project_map.refresh.validate`
- `workflow.checkpoint`
- `workflow.artifacts.validate`

Additional planning-specific checks:

- `Implementation Constitution` exists when boundary sensitivity is detected
- locked planning decisions are preserved

### `sp-tasks`

Recommended hooks:

- `workflow.preflight`
- `workflow.state.validate`
- `project_map.refresh.validate`
- `workflow.checkpoint`
- `workflow.artifacts.validate`

Additional checks:

- task checklist format valid
- analyze is the next command
- guardrail index exists when delegation-sensitive rules exist

### `sp-analyze`

Recommended hooks:

- `workflow.preflight`
- `workflow.state.validate`
- `project_map.refresh.validate`
- `workflow.gate.validate`
- `workflow.checkpoint`

Additional checks:

- gate outcome persisted
- recommended re-entry path is explicit

### `sp-implement`

Recommended hooks:

- `workflow.preflight`
- `workflow.state.validate`
- `project_map.refresh.validate`
- `workflow.checkpoint`
- `delegation.packet.validate`
- `delegation.join.validate`
- `workflow.completion.mark_dirty`

Additional checks:

- analyze gate cleared
- current batch and next action present in tracker
- packet/result contracts complete

### `sp-quick`

Recommended hooks:

- `workflow.preflight`
- `workflow.state.validate`
- `project_map.refresh.validate`
- `workflow.checkpoint`
- `delegation.packet.validate`
- `delegation.join.validate`
- `workflow.completion.mark_dirty`

Additional checks:

- constitution gate passed before broad analysis
- quick workspace initialized before lane selection

### `sp-fast`

Recommended hooks:

- `workflow.preflight`
- `project_map.refresh.validate`
- `workflow.checkpoint` only when the runtime indicates compaction risk or the
  change unexpectedly escalates

Additional checks:

- touched area still qualifies as local
- redirect to `sp-quick` when shared-surface risk is detected

### `sp-debug`

Recommended hooks:

- `workflow.preflight`
- `workflow.state.validate`
- `project_map.refresh.validate`
- `workflow.checkpoint`
- `delegation.join.validate` for evidence lanes
- `workflow.completion.mark_dirty`

Additional checks:

- observer gate before code/log/test deep dive
- debug session remains authoritative

### `sp-map-codebase`

Recommended hooks:

- `workflow.preflight`
- `workflow.checkpoint`
- `workflow.artifacts.validate`
- `project_map.complete_refresh`

Additional checks:

- canonical outputs all present
- refresh metadata finalized

## Separation From Extension Hooks

The product hook engine and extension hooks must stay separate.

### First-Party Quality Hooks

Use for:

- workflow integrity
- artifact integrity
- delegated execution integrity
- checkpoint and recovery integrity
- brownfield freshness truth

### Extension Hooks

Use for:

- optional integrations
- post-processing automation
- external system sync
- ecosystem add-ons

The product should not require `.specify/extensions.yml` to preserve its own
quality bar.

## Proposed Command Surface

Introduce a new CLI group:

- `specify hook preflight --command <name> ...`
- `specify hook validate-state --command <name> ...`
- `specify hook validate-artifacts --command <name> ...`
- `specify hook checkpoint --command <name> ...`
- `specify hook validate-packet ...`
- `specify hook validate-result ...`
- `specify hook mark-dirty ...`

The shared templates should gradually replace large prompt-only gate sections
with calls to these helpers.

That keeps integration-neutral workflow semantics while reducing reliance on
chat-only compliance.

## Rollout Plan

### Phase 1: Shared Gatekeeping

Ship:

- `WorkflowPreflightHook`
- `WorkflowStateHook`
- `ArtifactCompletenessHook`
- `AnalyzeGateHook`
- `ProjectMapFreshnessHook`
- structural `ContextCheckpointHook`

This phase should be fully useful even without native hooks.

### Phase 2: Execution Hardening

Ship:

- `DelegationPacketHook`
- `JoinPointAcceptanceHook`
- `QuickSessionHook`
- `DebugSessionHook`
- `CompletionDirtyMarkHook`

This phase hardens the highest-risk quality failures in execution.

### Phase 3: Recovery and Context Monitoring

Ship:

- `ContextMonitorHook`
- `SessionStateHook`
- `StatuslineHook`
- richer structural checkpoint triggers around compaction and join points

This phase improves long-session survivability and operator visibility without
changing the phase-gating model.

### Phase 4: Boundary and Security Enhancements

Ship:

- `ReadBoundaryGuardHook`
- `PromptGuardHook`
- `WorkflowBoundaryHook`
- `PhaseBoundaryHook`
- `CommitValidationHook`

These hooks matter, but they should land after the core workflow-truth and
execution-integrity layers are stable.

### Phase 5: Native Adapter Deepening

Ship:

- Codex adapter calls into the shared hook engine from native events
- richer pre/post tool validation
- stop-time checkpoint enforcement
- prompt-submit routing that can trigger quality checkpointing earlier

This phase is adapter-specific and should remain optional for integrations that
do not expose native hooks.

## Acceptance Criteria

The design is successful when all of the following are true:

1. `sp-implement` cannot proceed past a missing analyze gate.
2. `sp-specify`, `sp-plan`, `sp-tasks`, and `sp-analyze` cannot silently finish
   without their required state artifacts.
3. delegated execution cannot start without a validated packet.
4. delegated execution cannot close a join point without a validated result.
5. quick and debug workflows remain resumable without depending on chat memory.
6. brownfield workflows no longer rely only on prompt wording for map freshness.
7. when context pressure rises or a risky transition occurs, the current state is
   checkpointed into the proper artifact before continuation.

## Risks

- Over-blocking could make workflows feel brittle if the first release treats
  advisory cases as fatal.
- Re-encoding too much logic in native Codex hooks would recreate the current
  prompt-drift problem in another form.
- Trying to require token telemetry everywhere would make the system integration-
  dependent and fragile.

These risks are why the approved model is state-first, shared-core, and
structurally checkpointed.

## Decision

Proceed with a state-first quality-hook architecture.

The first implementation wave should target:

- workflow preflight
- workflow-state validation
- analyze gate enforcement
- project-map freshness enforcement
- context checkpointing for compaction and recovery

Then extend the same engine into delegated execution acceptance, context
monitoring, and the richer GSD-style native/runtime enhancement hooks.
