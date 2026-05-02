# Native Hook and `sp-*` Workflow Enhancement Design

**Date:** 2026-05-02
**Status:** Proposed
**Owner:** Codex

## Summary

This design extends the repository's native-hook model so it can strengthen
`sp-*` workflow execution across every currently supported native-hook surface.

The approved direction is:

- keep shared workflow truth in the first-party `specify hook ...` engine
- treat native hooks as enforcement and injection adapters, not as independent
  policy implementations
- prioritize workflow-discipline enforcement before context-compaction
  enhancements
- support every current native-hook surface in scope, while explicitly
  recognizing that the surfaces have different lifecycle depth
- use a balanced enforcement model: hard-block clear violations and high-risk
  actions, but handle most state or artifact gaps through repairable blocks,
  strong warnings, and resumable recovery artifacts

This is not a Claude-only design and it is not a shared-hooks-only design.

It is a two-layer design:

1. a portable shared policy core that defines workflow truth, compaction
   artifacts, and enforcement outcomes
2. native integration adapters for Claude, Codex, and Gemini that connect host
   lifecycle events to that shared policy core

## Problem Statement

The repository already has a meaningful hook architecture, but the current
system still stops short of the next quality tier for `sp-*` workflows.

Today the codebase already provides:

- a shared `specify hook ...` command surface for workflow state, checkpoint,
  prompt guard, read guard, commit validation, learning signal, and project-map
  freshness
- native Claude adapters that connect `SessionStart`, `UserPromptSubmit`,
  `PreToolUse`, `PostToolUse`, and `Stop` into the shared hook engine
- native Gemini adapters that connect `SessionStart`, `BeforeAgent`, and
  `BeforeTool` into the shared hook engine
- native Codex coverage through the OMX runtime and managed `.codex/hooks.json`
  wiring for `SessionStart`, `PreToolUse`, `PostToolUse`,
  `UserPromptSubmit`, and `Stop`
- durable workflow state artifacts such as `workflow-state.md`,
  `implement-tracker.md`, quick-task `STATUS.md`, debug sessions, lane state,
  and learning signal files

However, the current system still has four structural limits:

1. shared hooks can calculate policy, but by themselves they cannot enforce it
   at runtime
2. native adapters mostly surface the current hook engine as lightweight point
   checks instead of a complete workflow-discipline layer
3. checkpointing exists, but there is no first-class structured compaction
   artifact for resumable workflow recovery
4. native surfaces do not yet share one explicit contract for hard block,
   advisory output, repairable recovery, and compaction injection

The result is that the repository can already block some dangerous prompt or
tool actions, but it cannot yet consistently answer higher-value workflow
questions such as:

- is this prompt trying to jump phases without the required workflow state
- is this active `sp-*` run still safely resumable if the session stops now
- is the current workflow state missing, stale, or contradictory in a way that
  should repair before work continues
- what is the smallest reliable recovery capsule we can inject back into a
  native session without dumping full source-of-truth files into context

## Goals

- Strengthen `sp-*` workflow discipline through native hooks on all currently
  supported native-hook surfaces.
- Keep the shared `specify hook ...` engine as the single source of workflow
  policy truth.
- Introduce a portable structured compaction artifact for resumable workflow
  recovery.
- Define explicit `hard block`, `soft guidance`, and `repairable block`
  behavior so native adapters do not invent their own semantics.
- Preserve compatibility with existing workflow-state, tracker, and quick-task
  state authorities instead of creating a second source of truth.
- Improve long-running session recovery without forcing every integration to
  support identical lifecycle events.

## Non-Goals

- Do not rewrite workflow truth into each native adapter.
- Do not require shared hooks to achieve hard enforcement without a native
  integration surface.
- Do not replace `workflow-state.md`, `implement-tracker.md`, `STATUS.md`, or
  debug session files with compaction artifacts.
- Do not turn `v1` compaction into an LLM-generated freeform summarization
  pipeline.
- Do not make every low-signal quality issue a hard block.
- Do not expand scope to integrations that currently lack native hook support.

## Current-State Assessment

### Shared Hook Engine

The shared Python hook engine already centralizes first-party workflow checks in
`src/specify_cli/hooks/`.

It currently owns:

- workflow preflight and state validation
- artifact validation
- checkpoint generation
- context monitoring
- session-state validation
- statusline rendering
- prompt and read guards
- commit validation
- learning signal, review, capture, and inject flows
- project-map freshness actions

This is already the correct architectural center of gravity. The missing piece
is not a new place for workflow truth. The missing piece is a richer contract
that native adapters can consume consistently.

### Claude Native Hooks

Claude currently has the richest project-local native-hook adapter surface in
`src/specify_cli/integrations/claude/hooks/claude-hook-dispatch.py`.

Current managed Claude coverage:

- `SessionStart`: statusline and active workflow orientation
- `UserPromptSubmit`: prompt-bypass guard
- `PreToolUse`: read-boundary and inline commit-message validation
- `PostToolUse`: advisory session-state drift and learning signal
- `Stop`: context monitor and learning signal

The important architectural observation is that Claude already follows the
desired pattern: native hooks are thin and shared workflow truth stays in the
shared engine.

### Gemini Native Hooks

Gemini currently has an ingress-heavy but lifecycle-light adapter.

Current managed Gemini coverage:

- `SessionStart`: statusline and active workflow orientation
- `BeforeAgent`: prompt guard and soft learning signal
- `BeforeTool`: read-boundary and inline commit-message validation

Gemini therefore supports hard enforcement at entry points, but not the richer
post-tool or stop-time lifecycle currently available to Claude and Codex.

### Codex Native Hooks

Codex native hooks are managed through the OMX runtime rather than
project-local Python hook assets.

Current managed Codex coverage:

- `SessionStart`
- `UserPromptSubmit`
- `PreToolUse`
- `PostToolUse`
- `Stop`

Codex therefore belongs in the same lifecycle tier as Claude, but its adapter
surface is runtime-managed through the bundled engine.

### Existing Checkpoint and Learning Support

The repository already has:

- `workflow.checkpoint`
- `workflow.context.monitor`
- state authorities for implement, quick, and debug
- learning signal derivation from execution friction fields

That is a strong base for structured compaction, but the current system still
uses checkpointing mainly as a recovery hint rather than as a formal compacted
resume artifact.

## Design Principles

### 1. Shared Truth, Native Enforcement

Workflow truth lives in the shared hook engine.
Native integrations enforce or inject that truth where the host runtime allows
it.

### 2. Balanced Enforcement

Hard blocks are reserved for clear violations and high-risk actions.
Most state or artifact issues should remain resumable and repairable.

### 3. Compaction Is a Derived Recovery Layer

Compaction artifacts summarize and package existing source-of-truth state.
They do not replace that source of truth.

### 4. Lifecycle Depth Must Be Honest

Claude and Codex can support fuller lifecycle behavior than Gemini.
The design must embrace that asymmetry rather than pretending every surface can
do the same work.

### 5. Native Adapters Must Stay Thin

The repository should not accumulate one workflow policy per integration.
Adapters translate hook timing and output schema, not product logic.

## Approved Direction

Introduce a `workflow policy core` inside the shared hook layer, plus a
portable structured compaction artifact, then let every current native-hook
surface adopt that contract according to its lifecycle depth.

This produces two coordinated layers:

### Layer A: Shared Policy Core

This layer extends the current `specify hook ...` engine with:

- explicit workflow phase contracts
- explicit enforcement classification
- explicit compaction artifact generation
- explicit normalized hook outcomes that adapters can translate to host-native
  formats

### Layer B: Native Enforcement and Injection Adapters

This layer uses each integration's native event timing to decide:

- where hard enforcement is possible
- where advisory output is more appropriate
- where compaction or resume cues should be injected
- where portable fallback must rely on workflow templates and closeout gates

## Shared Policy Core

The shared policy core is the most important part of the design.

It should extend the current hook engine from "a collection of useful checks"
into "a workflow policy engine with stable outcome semantics."

### 1. Workflow Phase Contract

Each `sp-*` workflow in scope should expose a normalized contract that defines:

- current phase
- allowed next phases
- required source-of-truth state files
- minimum required artifacts for a trustworthy handoff
- high-risk phase-jump actions
- resumability requirements

Examples:

- `sp-specify` must not be treated as planning-ready when its minimum artifact
  contract is incomplete
- `sp-plan` must not be treated as safely resumable when its state authority is
  contradictory or missing
- `sp-implement` must not continue blind execution when
  `workflow-state.md` and `implement-tracker.md` disagree about whether the
  implementation stage is still active

### 2. Enforcement Classification Contract

Each policy result should be classified into one of four outcomes:

- `allow`
- `warn`
- `deny`
- `repairable-block`

The intent is:

- `deny`: clear violation or high-risk action; the host runtime should block
- `warn`: action is allowed, but the session should receive strong guidance
- `repairable-block`: continue only after the smallest explicit recovery step
- `allow`: no intervention needed

This replaces ad hoc adapter-level interpretation with a stable contract.

### 3. Compaction Payload Contract

The policy core should define a structured compaction artifact for resumable
workflow recovery.

This artifact should package:

- workflow identity
- state authorities that were used
- phase state
- artifact digest
- execution signal
- resume cue

It must remain a derivative artifact and never become the canonical authority.

### 4. Hook Outcome Schema

The shared engine should return outcomes that can be translated consistently by
Claude, Codex, and Gemini adapters.

That outcome should include:

- normalized status
- severity
- hard block reason when relevant
- advisory text
- repair steps when relevant
- compaction metadata
- state freshness metadata

Adapters then map that to host-native response schemas without altering the
meaning.

## Native Adapter Tiers

The integrations in scope do not all support the same lifecycle depth.

The design therefore uses two adapter tiers.

### Tier A: Full Lifecycle Adapters

Applies to:

- Claude
- Codex

These adapters support:

- `SessionStart`
- prompt ingress
- tool ingress
- post-tool review
- stop-time review

They should therefore implement:

- startup orientation and bounded resume guidance
- prompt-level hard blocks for clear workflow bypass attempts
- tool-level hard blocks for sensitive reads, invalid commits, and explicit
  high-risk workflow violations
- post-tool advisory checks for state drift, artifact freshness, and compaction
  refresh triggers
- stop-time checkpoint and compaction finalization, with blocking only when the
  active workflow can no longer be safely resumed

### Tier B: Ingress-Only Adapters

Applies to:

- Gemini

These adapters support:

- `SessionStart`
- prompt ingress
- tool ingress

They should therefore implement:

- startup orientation and bounded resume guidance
- prompt-level hard blocks for clear workflow bypass attempts
- tool-level hard blocks for sensitive reads and invalid commits
- portable fallback through workflow templates and closeout gates for
  checkpointing and compaction finalization

Gemini should not pretend to offer the same stop-time or post-tool guarantees
as Claude and Codex until the host runtime actually exposes them.

## Context Compaction Model

Compaction is designed as a recovery enhancement layer, not a replacement for
the current state authorities.

### Artifact Shape

`v1` should produce two parallel outputs per active workflow scope:

- `.specify/runtime/compaction/<scope-key>/latest.json`
- `.specify/runtime/compaction/<scope-key>/latest.md`

`latest.json` is the canonical machine-readable compaction payload.
`latest.md` is a human-readable fallback and manual recovery surface.

### Scope Keys

Compaction scope keys should align with workflow authorities:

- feature scope for `specify`, `clarify`, `deep-research`, `plan`, `tasks`,
  `analyze`, `implement`, `map-*`, and `test-*`
- workspace scope for `quick`
- session scope for `debug`

### Payload Sections

The compaction payload should contain six sections.

#### Identity

- workflow command
- feature, workspace, or session identifier
- lane or session metadata
- generation timestamp
- trigger reason

#### Truth Sources

- source-of-truth file paths
- file existence
- modification times
- short hashes or digests when helpful

This lets adapters detect staleness rather than trusting an old compaction
artifact blindly.

#### Phase State

- current phase
- workflow status
- next command
- next action
- blocked reason
- resume decision

#### Artifact Digest

This is the minimum structured summary of the current artifact state.

Examples:

- `specify` or `plan`: locked decisions, unresolved questions, scope boundaries
- `implement`: current batch, write scope, recent verification result
- `debug`: current hypothesis, ruled-out paths, next evidence step
- `quick`: active lane, completed work, next lane action

#### Execution Signal

- retry attempts
- hypothesis changes
- validation failures
- artifact rewrites
- command failures
- user corrections
- route changes
- scope changes
- false starts
- hidden dependencies
- learning pain score

#### Resume Cue

This is the smallest safe native-session reinjection payload:

- where the workflow currently is
- what not to redo
- what to do next
- which file or state authority to inspect first

### Trigger Model

Compaction refresh should happen in three ways.

#### Always-On Read

At session start, adapters may read the latest compaction artifact and inject a
small bounded resume cue.

#### Threshold Refresh

Compaction should refresh when:

- context monitor warns
- a phase boundary changes
- state drift appears
- a learning signal crosses the configured threshold

#### Terminal Refresh

At stop time on full lifecycle adapters, the system should attempt a final
compaction refresh before session close.

### Injection Discipline

Compaction must stay bounded.

The native session should not receive the full compaction artifact inline.

`v1` injection limits should look like:

- statusline: one compact line
- resume cue: a few short bullets or short sentences
- artifact digest: stored on disk by default, not injected inline

The injection goal is to orient the agent, not to dump the entire state package
back into chat context.

## Enforcement Matrix

The enforcement model should be explicit and stable.

### Global Rules

1. block clear workflow-bypass intent and high-risk actions
2. do not block purely because compaction is stale
3. prefer repairable blocks over blind denial when the issue is recoverable
4. use `Stop` as a recovery gate, not as the primary daily enforcement surface

### Prompt Ingress

Prompt ingress should:

- hard-block explicit workflow bypass requests
- warn on softer instruction-override language
- prefer resume-cue injection when the user is trying to continue an active
  workflow

### Tool Ingress

Tool ingress should:

- hard-block sensitive reads and high-risk boundary violations
- hard-block invalid commit messages
- repairably block when source-of-truth state is missing and a safety decision
  cannot be made without it
- warn when the tool action looks safe locally but appears inconsistent with the
  current phase or next action

### Post-Tool

Post-tool hooks should remain advisory.

They should trigger:

- state drift checks
- artifact freshness checks
- learning signal checks
- compaction refresh suggestions or generation

They should not become a second hard-block surface for routine work.

### Stop

Stop should:

- hard-block only when an active workflow is no longer safely resumable because
  required state or recovery artifacts are broken
- otherwise generate or refresh checkpoint and compaction artifacts
- emit resume guidance and learning review reminders

### Workflow-Specific Intensity

The workflows should not all enforce with the same intensity.

#### Highest Intensity

- `implement`
- `quick`
- `debug`

These depend most heavily on durable execution state and resumability.

#### Medium Intensity

- `specify`
- `deep-research`
- `plan`
- `tasks`
- `analyze`

These should enforce phase truth and minimum artifact contracts, but most issues
should remain repairable.

#### Medium Intensity with Different Focus

- `map-scan`
- `map-build`
- `test-scan`
- `test-build`

These should focus on coverage truth, packet integrity, and handoff
correctness.

#### Lowest Intensity

- `fast`

`fast` stays lightweight, but it must still honor prompt guard, read guard, and
commit validation.

## Rollout Plan

This design should land in three implementation waves.

### Wave 1: Shared Policy Core Expansion

First extend the shared engine with:

- workflow policy outcome classification
- compaction artifact generation and read helpers
- unified phase contract and artifact-minimum checks
- normalized output schema additions

This wave should avoid changing existing adapter block behavior unless a clear
bug is being fixed.

### Wave 2: Native Adapter Adoption

Then adopt the new shared policy core on:

- Claude project-local hook adapter
- Codex OMX native hook runtime
- Gemini ingress-only adapter

The rule for this wave is simple:

- adapters translate policy
- adapters do not define policy

### Wave 3: Workflow Template Integration

Finally update shared workflow templates so non-native or lifecycle-light
surfaces still benefit from:

- explicit checkpoint recommendations
- compaction artifact references
- closeout-time learning review
- consistent portable recovery guidance

## Compatibility Requirements

- Preserve the existing `specify hook ...` command names.
- Preserve existing top-level JSON compatibility for hook CLI output.
- Add new fields in an append-only way where possible.
- Keep existing state authorities canonical.
- Keep Codex hook installation managed through OMX and `.codex/hooks.json`.
- Keep Claude and Gemini adapters project-local and thin.

## Verification Plan

Verification should cover four layers.

### 1. Unit Tests

Add or extend tests for:

- phase contract classification
- repairable-block behavior
- compaction payload generation
- compaction staleness detection
- enforcement matrix decisions

### 2. Hook CLI Contract Tests

Extend `tests/contract/test_hook_cli_surface.py` to prove:

- new outputs remain parseable JSON
- old fields still exist where callers expect them
- compaction and repair outcomes follow a stable schema

### 3. Integration Tests

Extend native integration tests for:

- Claude adapter lifecycle mapping
- Gemini ingress-only mapping
- compaction injection behavior
- hard-block versus advisory mapping

### 4. Runtime Tests

Extend Codex runtime tests for:

- managed `.codex/hooks.json` generation and merge behavior
- OMX native hook dispatch parity with the shared policy core
- stop-time compaction and advisory behavior

## Risks and Mitigations

### Risk 1: Over-Blocking Routine Work

If too many quality issues become hard blocks, users will treat native hooks as
friction rather than support.

Mitigation:

- keep the balanced model
- reserve hard block for explicit violations and high-risk actions
- use repairable blocks and strong guidance for most workflow truth issues

### Risk 2: Compaction Drift Becomes a Fake Source of Truth

If compaction artifacts become more trusted than the state files they summarize,
recovery quality will degrade.

Mitigation:

- make compaction explicitly derivative
- include truth-source metadata
- treat stale compaction as a refresh signal, not as a hard enforcement reason

### Risk 3: Integration Drift Across Native Surfaces

If Claude, Codex, and Gemini adapters each evolve their own semantics, the
shared product story breaks down.

Mitigation:

- centralize policy in the shared core
- define a normalized hook outcome schema
- test adapter translations explicitly

### Risk 4: Scope Creep Into a Generalized Summarization System

It would be easy to turn compaction into an open-ended LLM summarization
feature.

Mitigation:

- keep `v1` structured-first
- add narrative summary only when a later design proves it is needed

## Recommendation

The recommended implementation strategy is:

1. build the shared policy core first
2. integrate it into Claude, Codex, and Gemini according to their lifecycle
   depth
3. update `sp-*` templates afterward so portable fallback behavior stays aligned

This order preserves architectural clarity, minimizes adapter drift, and gives
the repository a credible path to stronger `sp-*` workflow discipline without
pretending shared hooks alone can hard-enforce behavior.
