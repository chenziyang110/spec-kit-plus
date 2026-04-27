# Workflow Quality Hooks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-party, state-first quality-hook system that turns workflow prompt rules into shared runtime checks, proactive context checkpoints, and delegated-execution integrity gates.

**Architecture:** Keep product truth in a shared `specify hook` engine under `src/specify_cli/` and let native integration adapters call into that engine where richer host events exist. Preserve extension hooks as optional automation, not as the source of workflow integrity.

**Tech Stack:** Python, Typer CLI, Markdown/JSON workflow artifacts, pytest, existing Codex native hooks under `extensions/agent-teams/engine/`

---

## Scope and Release Order

Ship this in four slices:

1. Shared hook engine and command surface
2. Workflow/state/artifact/freshness/checkpoint enforcement
3. Delegation and join-point enforcement
4. Context monitoring, session-state, and operator visibility
5. Read/prompt/boundary/commit guards
6. Codex-native adapter integration and context-pressure checkpointing

Do not start with native-hook-only implementation. The shared engine must exist
first so product rules stay cross-CLI.

### Task 1: Create the Shared Hook Engine and CLI Surface

**Files:**
- Create: `src/specify_cli/hooks/__init__.py`
- Create: `src/specify_cli/hooks/events.py`
- Create: `src/specify_cli/hooks/engine.py`
- Create: `src/specify_cli/hooks/types.py`
- Modify: `src/specify_cli/__init__.py`
- Create: `tests/hooks/test_hook_engine.py`
- Create: `tests/contract/test_hook_cli_surface.py`

**Intent:** Establish one first-party quality-hook engine and a `specify hook`
CLI group before wiring any specific checks into templates or adapters.

- [ ] Define canonical event names and payload shapes for:
  - `workflow.preflight`
  - `workflow.state.validate`
  - `workflow.artifacts.validate`
  - `workflow.gate.validate`
  - `workflow.checkpoint`
  - `delegation.packet.validate`
  - `delegation.join.validate`
  - `project_map.mark_dirty`
  - `project_map.complete_refresh`
- [ ] Implement a shared engine that accepts an event payload and returns a
  normalized result with:
  - `status`
  - `severity`
  - `actions`
  - `errors`
  - `warnings`
  - `writes`
- [ ] Add a new `specify hook` Typer group with subcommands for the shared
  events.
- [ ] Add focused tests that prove:
  - invalid event payloads fail cleanly
  - hook results are deterministic
  - the CLI surface returns parseable JSON
- [ ] Run:
  - `pytest tests/hooks/test_hook_engine.py tests/contract/test_hook_cli_surface.py -q`

### Task 2: Implement Workflow Preflight, State, Artifact, and Freshness Hooks

**Files:**
- Create: `src/specify_cli/hooks/preflight.py`
- Create: `src/specify_cli/hooks/state_validation.py`
- Create: `src/specify_cli/hooks/artifact_validation.py`
- Create: `src/specify_cli/hooks/project_map.py`
- Modify: `src/specify_cli/project_map_status.py`
- Modify: `src/specify_cli/__init__.py`
- Create: `tests/hooks/test_preflight_hooks.py`
- Create: `tests/hooks/test_state_hooks.py`
- Create: `tests/hooks/test_artifact_hooks.py`
- Create: `tests/hooks/test_project_map_hooks.py`

**Intent:** Move the most important workflow integrity rules out of prompt-only
template text and into reusable validators.

- [ ] Implement `WorkflowPreflightHook` rules for:
  - required feature/workspace/session location
  - required upstream gate status
  - required project-map freshness for brownfield work
- [ ] Implement `WorkflowStateHook` rules for:
  - `workflow-state.md`
  - `implement-tracker.md`
  - quick-task `STATUS.md`
  - debug session file
- [ ] Implement `ArtifactCompletenessHook` rules for:
  - `sp-specify`
  - `sp-plan`
  - `sp-tasks`
  - `sp-analyze`
- [ ] Extend the project-map helper layer with hook-friendly classification
  outputs instead of only human-readable status.
- [ ] Add tests that prove:
  - `sp-implement` blocks when analyze is not cleared
  - `sp-fast` and `sp-quick` can fail closed on stale map coverage
  - planning workflows fail when their source-of-truth file is missing
- [ ] Run:
  - `pytest tests/hooks/test_preflight_hooks.py tests/hooks/test_state_hooks.py tests/hooks/test_artifact_hooks.py tests/hooks/test_project_map_hooks.py -q`

### Task 3: Add ContextCheckpointHook and Recovery Serializers

**Files:**
- Create: `src/specify_cli/hooks/checkpoint.py`
- Create: `src/specify_cli/hooks/checkpoint_serializers.py`
- Modify: `src/specify_cli/learnings.py`
- Modify: `src/specify_cli/__init__.py`
- Modify: `templates/workflow-state-template.md`
- Create: `tests/hooks/test_checkpoint_hooks.py`
- Create: `tests/hooks/test_checkpoint_serializers.py`

**Intent:** Provide a product-level answer to context pressure and recovery,
instead of relying only on prompt reminders and integration-specific overlay
text.

- [ ] Implement a shared checkpoint serializer contract for:
  - `workflow-state.md`
  - `implement-tracker.md`
  - quick-task `STATUS.md`
  - debug session file
- [ ] Add support for structural checkpoint triggers:
  - before join points
  - before delegated fan-out
  - before long validation phases
  - before stop/interrupt-like transitions
  - after major artifact synthesis
- [ ] Add a generic checkpoint output that can be written even when the
  integration does not expose token telemetry.
- [ ] Keep Codex/OMX-specific sinks optional for later adapter work:
  - state server
  - notepad working section
  - project memory
- [ ] Add tests that prove:
  - checkpoint results carry enough state for resume
  - serializers refuse empty or contradictory state
  - structural triggers work without token-count data
- [ ] Run:
  - `pytest tests/hooks/test_checkpoint_hooks.py tests/hooks/test_checkpoint_serializers.py -q`

### Task 4: Replace Prompt-Only Workflow Gates With Hook Calls

**Files:**
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/analyze.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/fast.md`
- Modify: `templates/commands/debug.md`
- Modify: `templates/commands/map-codebase.md`
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_quick_template_guidance.py`
- Modify: `tests/test_fast_template_guidance.py`
- Modify: `tests/test_debug_template_guidance.py`

**Intent:** Make the templates call canonical helpers for product integrity
instead of hand-expanding the same checks in prose.

- [ ] Replace duplicated prompt-only checks with explicit helper invocation
  guidance such as:
  - `specify hook preflight`
  - `specify hook validate-state`
  - `specify hook validate-artifacts`
  - `specify hook checkpoint`
- [ ] Preserve human-readable workflow intent, but move the authoritative
  pass/fail logic into the helper commands.
- [ ] Ensure the shared templates remain integration-neutral.
- [ ] Update template guidance tests so they assert the new helper-contract
  language instead of only prose repetition.
- [ ] Run:
  - `pytest tests/test_alignment_templates.py tests/test_quick_template_guidance.py tests/test_fast_template_guidance.py tests/test_debug_template_guidance.py -q`

### Task 5: Harden Delegation Through Shared Packet and Result Hooks

**Files:**
- Modify: `src/specify_cli/execution/packet_compiler.py`
- Modify: `src/specify_cli/execution/packet_validator.py`
- Modify: `src/specify_cli/execution/result_handoff.py`
- Modify: `src/specify_cli/execution/result_normalizer.py`
- Modify: `src/specify_cli/execution/result_validator.py`
- Create: `src/specify_cli/hooks/delegation.py`
- Create: `tests/hooks/test_delegation_hooks.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/integrations/test_integration_codex.py`

**Intent:** Promote the existing packet/result validators into explicit
join-point hook boundaries that the workflow engine can call consistently.

- [ ] Implement `DelegationPacketHook` around packet compilation and validation.
- [ ] Implement `JoinPointAcceptanceHook` around result normalization and
  validation.
- [ ] Ensure failures keep the current `DP1`, `DP2`, and `DP3` semantics rather
  than inventing a second error taxonomy.
- [ ] Add tests that prove:
  - dispatch cannot proceed from raw task text alone
  - placeholder or stale worker results cannot close a join point
  - blocked worker results must include blocker evidence and recovery guidance
- [ ] Run:
  - `pytest tests/hooks/test_delegation_hooks.py tests/integrations/test_integration_codex.py -q`

### Task 6: Add Quick/Debug Session Integrity Hooks

**Files:**
- Create: `src/specify_cli/hooks/quick_session.py`
- Create: `src/specify_cli/hooks/debug_session.py`
- Modify: `scripts/bash/quick-state.sh`
- Modify: `src/specify_cli/__init__.py`
- Create: `tests/hooks/test_quick_session_hooks.py`
- Create: `tests/hooks/test_debug_session_hooks.py`
- Modify: `tests/test_quick_cli.py`

**Intent:** Make quick/debug resumability truthful even when the conversation is
interrupted or compacted aggressively.

- [ ] Add `QuickSessionHook` checks for:
  - `STATUS.md` existence after initialization
  - required fields before lane selection and before terminal close
  - derived `index.json` consistency
- [ ] Add `DebugSessionHook` checks for:
  - observer gate completion
  - explicit next hypothesis and next probe
  - truthful terminal status
- [ ] Extend the quick helper path so close/archive cannot silently preserve
  malformed status state.
- [ ] Run:
  - `pytest tests/hooks/test_quick_session_hooks.py tests/hooks/test_debug_session_hooks.py tests/test_quick_cli.py -q`

### Task 7: Integrate the Shared Engine With Codex Native Hooks

**Files:**
- Modify: `extensions/agent-teams/engine/src/scripts/codex-native-hook.ts`
- Modify: `extensions/agent-teams/engine/src/config/codex-hooks.ts`
- Modify: `extensions/agent-teams/engine/src/hooks/agents-overlay.ts`
- Modify: `extensions/agent-teams/engine/src/scripts/codex-native-pre-post.ts`
- Create: `extensions/agent-teams/engine/src/hooks/specify-quality-adapter.ts`
- Modify: `extensions/agent-teams/engine/src/scripts/__tests__/codex-native-hook.test.ts`

**Intent:** Reuse the shared product rules from native Codex timing points
without forking product truth inside the adapter layer.

- [ ] Add an adapter that can call the shared `specify hook` engine or its
  equivalent library entrypoints from:
  - `UserPromptSubmit`
  - `PreToolUse`
  - `PostToolUse`
  - `Stop`
- [ ] Keep `UserPromptSubmit` routing advisory, but allow it to request a
  structural checkpoint when the turn shape implies high context pressure or a
  risky workflow transition.
- [ ] Extend `Stop` handling so it can enforce checkpoint-before-exit behavior
  for active workflow state.
- [ ] Keep adapter-specific logic small; shared hook rules remain the primary
  authority.
- [ ] Run:
  - `pnpm test -- codex-native-hook`
  - or the repository's existing focused Codex-native hook test command

### Task 8: Documentation, Self-Review, and Operator Surfacing

**Files:**
- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Modify: `AGENTS.md`
- Modify: `extensions/EXTENSION-USER-GUIDE.md`
- Create or Modify: `docs/superpowers/specs/2026-04-26-workflow-quality-hook-architecture-design.md`

**Intent:** Make the new hook model understandable to operators, contributors,
and future workflow authors.

- [ ] Document the split between:
  - first-party quality hooks
  - extension hooks
  - native integration adapters
- [ ] Document the new context-checkpoint story clearly:
  - what is persisted
  - when checkpointing happens
  - what remains integration-specific
- [ ] Add operator guidance for common failures:
  - stale project map
  - missing workflow state
  - blocked analyze gate
  - packet/result validation failure
  - malformed checkpoint state
- [ ] Re-run focused documentation and contract tests that mention the workflow
  integrity model.

### Task 9: Add Read Boundary and Prompt Guard Hooks

**Files:**
- Create: `src/specify_cli/hooks/read_guard.py`
- Create: `src/specify_cli/hooks/prompt_guard.py`
- Create: `tests/hooks/test_read_guard_hooks.py`
- Create: `tests/hooks/test_prompt_guard_hooks.py`
- Modify: `extensions/agent-teams/engine/src/scripts/codex-native-pre-post.ts`
- Modify: `extensions/agent-teams/engine/src/scripts/codex-native-hook.ts`
- Modify: `extensions/agent-teams/engine/src/scripts/__tests__/codex-native-hook.test.ts`

**Intent:** Bring the originally requested GSD-style read and prompt guard
surfaces into the product roadmap without letting them replace the workflow
quality core.

- [ ] Implement a shared read-boundary policy with:
  - repository-root boundary checks
  - sensitive-path deny rules
  - explicit allow rules for workflow artifacts and known safe surfaces
- [ ] Implement a shared prompt-guard classifier for clear workflow-override or
  guardrail-bypass attempts.
- [ ] Keep low-confidence matches advisory and reserve hard block for explicit
  hostile override language.
- [ ] Wire native Codex `PreToolUse` and `UserPromptSubmit` handling so they can
  call into these guards.
- [ ] Run:
  - `pytest tests/hooks/test_read_guard_hooks.py tests/hooks/test_prompt_guard_hooks.py -q`
  - focused Codex native-hook tests covering read/prompt guard decisions

### Task 10: Add Context Monitor, Session-State, and Statusline Hooks

**Files:**
- Create: `src/specify_cli/hooks/context_monitor.py`
- Create: `src/specify_cli/hooks/session_state.py`
- Create: `src/specify_cli/hooks/statusline.py`
- Create: `tests/hooks/test_context_monitor_hooks.py`
- Create: `tests/hooks/test_session_state_hooks.py`
- Create: `tests/hooks/test_statusline_hooks.py`
- Modify: `extensions/agent-teams/engine/src/hooks/agents-overlay.ts`
- Modify: `extensions/agent-teams/engine/src/hud/render.ts`

**Intent:** Productize the currently partial compaction/recovery story and make
context pressure visible before it becomes a silent quality failure.

- [ ] Implement `ContextMonitorHook` with:
  - structural checkpoint triggers available in all integrations
  - optional token-watermark support when the host runtime exposes it
- [ ] Implement `SessionStateHook` to reconcile resume-critical workflow state
  across markdown state files and native runtime surfaces.
- [ ] Implement `StatuslineHook` as an informational hook output that can feed
  operator HUD/statusline surfaces without becoming the truth source.
- [ ] Extend the Codex/OMX overlay and HUD path to consume the shared monitor
  outputs rather than only static compaction advice.
- [ ] Run:
  - `pytest tests/hooks/test_context_monitor_hooks.py tests/hooks/test_session_state_hooks.py tests/hooks/test_statusline_hooks.py -q`

### Task 11: Add Workflow/Phase Boundary and Commit Validation Hooks

**Files:**
- Create: `src/specify_cli/hooks/workflow_boundary.py`
- Create: `src/specify_cli/hooks/phase_boundary.py`
- Create: `src/specify_cli/hooks/commit_validation.py`
- Create: `tests/hooks/test_workflow_boundary_hooks.py`
- Create: `tests/hooks/test_phase_boundary_hooks.py`
- Create: `tests/hooks/test_commit_validation_hooks.py`
- Modify: `scripts/bash/create-new-feature.sh`
- Modify: `scripts/bash/setup-plan.sh`
- Modify: `scripts/bash/check-prerequisites.sh`
- Modify: `scripts/bash/quick-state.sh`
- Modify: `src/specify_cli/__init__.py`

**Intent:** Cover the remaining GSD-style operational hooks that act at
workflow transitions, setup/cleanup boundaries, and commit finalization.

- [ ] Implement `WorkflowBoundaryHook` and `PhaseBoundaryHook` so phase
  transitions can trigger required setup, cleanup, and transition validation.
- [ ] Implement `CommitValidationHook` with:
  - commit message contract checks
  - unresolved blocked-state protection
  - optional required-quality-check confirmation
- [ ] Wire the boundary helpers into the script edges where workflow state moves
  from setup to planning to execution.
- [ ] Keep git-hook integration optional, with a `specify` CLI fallback when
  repo-side hook installation is unavailable.
- [ ] Run:
  - `pytest tests/hooks/test_workflow_boundary_hooks.py tests/hooks/test_phase_boundary_hooks.py tests/hooks/test_commit_validation_hooks.py -q`

## Verification Matrix

Before declaring the work complete, run at least:

- `pytest tests/hooks -q`
- `pytest tests/contract/test_hook_cli_surface.py -q`
- `pytest tests/test_alignment_templates.py tests/test_quick_template_guidance.py tests/test_fast_template_guidance.py tests/test_debug_template_guidance.py -q`
- focused Codex-native hook tests for adapter integration

## Review Checklist

- Every first-party workflow gate that previously lived only in prompt prose now
  has one canonical validator path.
- Context checkpointing works even when exact token telemetry is unavailable.
- Native Codex integration deepens enforcement without becoming the only source
  of product truth.
- Extension hooks remain an automation surface rather than a workflow-integrity
  dependency.
- `DP1`, `DP2`, and `DP3` remain the delegation integrity language everywhere.
- The original GSD-inspired backlog is fully represented across:
  - quality-core hooks
  - context/recovery hooks
  - read/prompt guards
  - boundary hooks
  - commit validation
