# sp Workflow Hook Deescalation Design

**Date:** 2026-05-12  
**Status:** Proposed  
**Scope:** Shared `sp-*` workflow templates, passive skills, integration-projected guidance, hook documentation, and regression tests  
**Primary goal:** Stop generated `sp-*` workflows from spending agent context on first-party hook commands while preserving the useful hook runtime as an internal, diagnostic, and native-adapter surface.

## Context

The first-party workflow quality hook system was added to make generated workflows more recoverable and enforceable. Over time, hook commands became embedded directly in the `sp-*` workflow prompts. Core templates now instruct agents to run commands such as `specify hook preflight`, `validate-state`, `validate-artifacts`, `checkpoint`, `workflow-policy`, `monitor-context`, `signal-learning`, and `review-learning` as normal workflow steps.

This has created the opposite failure mode: instead of making the workflow lighter and safer, the prompts push the agent into frequent hook calls, repeated JSON payloads, and repeated hook explanations. The result is high context consumption, noisy transcripts, and lower practical throughput for ordinary `sp-*` usage.

The hook runtime still has valuable pieces. Some commands are useful as low-level validators, compatibility aliases, native adapter helpers, or test/debug tools. The problem is not the existence of hook code. The problem is that generated workflows treat hooks as user-facing execution choreography.

## Problem

`sp-*` prompts currently overuse hooks in four ways:

- Workflow entry and phase progression are expressed as hook calls instead of plain state and artifact requirements.
- Context recovery and statusline helpers are written into the agent's main prompt even though they are only valuable for native hook adapters or explicit diagnostics.
- Learning capture is presented through hook gates, adding more command surfaces to an already complex closeout path.
- Project cognition refresh fallback is routed through `specify hook mark-dirty` and `complete-refresh` even though `project-map` / `project-cognition` commands are clearer public surfaces.

This makes generated workflows feel hook-driven rather than task-driven. It also obscures which checks are essential and which are optional diagnostics.

## Goals

- Remove routine `specify hook ...` usage from generated `sp-*` workflow prompts.
- Preserve the hook runtime for compatibility, tests, native adapters, and explicit operator diagnostics.
- Keep essential quality guarantees by expressing them as durable state, artifact, packet, result, and verification requirements rather than as repeated hook invocations.
- Make public docs describe `specify hook` as an internal/diagnostic compatibility surface, not a daily workflow surface.
- Keep project cognition dirty/fresh finalization available through stable public commands.
- Reduce generated prompt size and live context usage without deleting useful validator code.

## Non-Goals

- Do not delete `src/specify_cli/hooks/**` in this change.
- Do not remove hook CLI commands that existing generated projects, tests, or native adapters may still call.
- Do not redesign native Claude/Gemini hook behavior in detail; only make it opt-in or clearly separated from normal `sp-*` prompt guidance.
- Do not replace the `WorkerTaskPacket` / `WorkerTaskResult` contracts.
- Do not remove project cognition freshness semantics.

## Proposed Design

### 1. Reclassify Hook Surfaces

Classify hook commands into three support tiers.

**Tier A: Keep as important low-level validators or compatibility aliases**

- `validate-packet`
- `validate-result`
- `validate-state`
- `validate-session-state`
- `mark-dirty`
- `complete-refresh`

These commands remain available because they protect real contracts or preserve compatibility. Generated `sp-*` prompts should not tell agents to run them as routine steps. Instead:

- `WorkerTaskPacket` and `WorkerTaskResult` validation remains a contract requirement.
- Code paths that already have packet/result files may call validators internally.
- Operators can still run these commands for diagnosis.
- `mark-dirty` and `complete-refresh` are retained as hook aliases, but public guidance should prefer `project-map mark-dirty`, `project-map complete-refresh`, `project-cognition mark-dirty`, or `project-cognition complete-refresh`.

**Tier B: Keep for native adapters and explicit diagnostics**

- `read-guard`
- `prompt-guard`
- `validate-commit`
- `workflow-policy`
- `render-statusline`
- `build-compaction`
- `read-compaction`

These commands remain useful when an integration has native hook events. They should not appear in normal `sp-*` workflow steps. Installation and docs should frame them as native-adapter internals or opt-in diagnostics.

**Tier C: Remove from `sp-*` prompt choreography**

- `preflight`
- `validate-artifacts`
- `checkpoint`
- `monitor-context`
- `signal-learning`
- `review-learning`
- `capture-learning`
- `inject-learning`

These are the highest-noise commands in generated prompts. Keep the runtime initially for backward compatibility, but remove their routine invocation instructions from command templates and passive skills.

### 2. Rewrite Workflow Prompt Guidance Around Outcomes

Every affected `templates/commands/*.md` file should describe the required outcome rather than the hook command used to check it.

Examples:

- Replace "run `hook preflight`" with "confirm project cognition and workflow-entry prerequisites before source-level work".
- Replace "run `hook validate-state`" with "keep the workflow state file current and internally consistent".
- Replace "run `hook validate-artifacts`" with "before handoff, verify the required artifact set exists and matches this workflow's output contract".
- Replace "run `hook checkpoint` / `monitor-context`" with "update durable state before risky transitions, subagent fan-out, long validation, or stopping".
- Replace "run `hook signal-learning` / `review-learning`" with "capture reusable project learning through the passive learning layer when the run exposes reusable friction".

This preserves the intent while removing command spam.

### 3. Move Learning Away From Hook Gates

Generated workflows should use the passive learning layer directly:

- `learning start` remains acceptable for heavier workflows when available.
- `learning capture-auto` is the preferred low-noise closeout path when durable state already captures false starts, hidden dependencies, validation gaps, or reusable constraints.
- Manual learning capture remains available but should not be presented as a required hook gate.

Passive skills such as `spec-kit-project-learning` and shared command partials should stop advertising hook-based learning as the normal path.

### 4. Keep Delegation Contracts Strong Without Hook Choreography

`sp-implement`, `sp-quick`, worker prompts, and passive subagent skills should continue to require validated execution contracts. The language should emphasize:

- compile a `WorkerTaskPacket` or equivalent execution contract before delegation
- include objective, authoritative inputs, read/write scope, forbidden paths, validation checks, and done criteria
- accept only structured handoffs compatible with `WorkerTaskResult` semantics
- reject incomplete handoffs or missing validation evidence

Where a runtime writes actual packet/result JSON files, it may use the validator code. The generated prompt should not force every human-visible workflow pass through `specify hook validate-packet` and `validate-result`.

### 5. Prefer Public Project Cognition Commands

Generated workflow prompts should stop teaching `specify hook mark-dirty` and `specify hook complete-refresh`. Public/operator guidance should use:

- `specify project-map mark-dirty`
- `specify project-map complete-refresh`
- `specify project-cognition mark-dirty`
- `specify project-cognition complete-refresh`

The hook aliases remain for backward compatibility and native/internal call sites.

### 6. Native Hook Adapter Policy

Claude and Gemini native hook adapters may continue to call shared hook commands internally, but normal generated workflow prompts should not instruct agents to do the same.

Follow-up implementation should evaluate whether native adapters should be:

- installed by default but quieter
- installed only when a user explicitly opts into native hooks
- installed with fewer events enabled by default

That decision can be staged after prompt deescalation. The first implementation should not break current adapter tests unless the chosen implementation explicitly updates installation semantics.

## Affected Surfaces

At minimum, implementation should sweep:

- `templates/commands/*.md`
- `templates/command-partials/common/*.md`
- `templates/passive-skills/spec-kit-project-learning/SKILL.md`
- `templates/passive-skills/subagent-driven-development/SKILL.md`
- `templates/passive-skills/dispatching-parallel-agents/SKILL.md`
- `src/specify_cli/integrations/base.py`
- integration-specific injected guidance under `src/specify_cli/integrations/**`
- `README.md`
- `PROJECT-HANDBOOK.md`
- hook guidance tests such as `tests/test_hook_template_guidance.py`
- command surface and integration projection tests that currently assert hook command text appears in generated templates

The required repo search before implementation is:

```text
rg -n "specify hook|hook preflight|hook validate|hook checkpoint|hook workflow-policy|hook monitor-context|hook signal-learning|hook review-learning|hook capture-learning|hook inject-learning|hook mark-dirty|hook complete-refresh|{{specify-subcmd:hook" templates src scripts tests README.md PROJECT-HANDBOOK.md .github pyproject.toml
```

## Testing Strategy

Regression coverage should prove both sides of the change:

- Generated `sp-*` prompts no longer include routine `{{specify-subcmd:hook ...}}` instructions.
- Hook CLI commands still exist and produce parseable JSON for compatibility.
- Packet/result validation logic remains covered through execution and hook CLI tests.
- Project cognition public commands remain covered, with hook aliases preserved as compatibility tests.
- README and quickstart no longer present hook commands as normal user workflow steps.
- Native adapter tests are updated only if installation/default behavior changes.

## Acceptance Criteria

- `templates/commands/{specify,plan,tasks,implement,quick,debug,analyze,deep-research,constitution}.md` no longer instruct routine first-party hook calls as mandatory workflow steps.
- Learning guidance no longer requires hook-based `signal-learning` or `review-learning` closeout.
- Public documentation describes `specify hook` as internal, diagnostic, compatibility, or native-adapter oriented.
- `validate-packet`, `validate-result`, state validation, and project cognition freshness commands remain available.
- Integration-generated assets do not reintroduce routine hook choreography through shared projection helpers.
- Tests prove hook deescalation without deleting the hook runtime.

## Risks and Mitigations

- **Risk:** Removing hook instructions weakens workflow discipline.  
  **Mitigation:** Keep outcome requirements explicit: state files must stay current, artifact sets must be checked, packets/results must carry evidence, and verification must run.

- **Risk:** Existing generated projects still contain old hook-heavy prompts.  
  **Mitigation:** Preserve hook CLI compatibility and let `specify integration repair` or regeneration refresh assets.

- **Risk:** Native adapters still produce context noise even after prompt cleanup.  
  **Mitigation:** Treat adapter quieting as a follow-up lane after template deescalation is measured.

- **Risk:** Tests overfit to exact hook command text.  
  **Mitigation:** Replace those assertions with checks for durable quality requirements and absence of routine hook choreography.

## Open Decisions

- Whether Claude/Gemini native hooks should remain default-installed after prompt deescalation.
- Whether Tier C hook commands should eventually be deprecated from the public CLI help while remaining callable for compatibility.
- Whether `validate-state` should move under a non-hook diagnostic namespace in a later compatibility-preserving release.

