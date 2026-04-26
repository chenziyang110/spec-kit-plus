# sp-specify Alignment Hardening Design

**Date:** 2026-04-26  
**Status:** Implemented  
**Owner:** Codex

## Summary

This design hardens the `sp-specify` stage so requirement alignment survives all the
way into the written artifact set, not just the clarification conversation.

The implementation adds three new requirement-shaping controls to the shared
`sp-specify` workflow:

- capability checkpoints for high-risk capabilities
- decision-fork mode for high-impact gray areas
- an artifact review gate before `/sp-plan`

The design is intentionally text-only. It does **not** introduce browser-based
visual clarification, mockup workflows, or a separate visual companion surface.

## Problem Statement

`sp-specify` was already analysis-first and substantially stronger than a shallow
spec recorder, but it still had a gap at the exact point where planning quality can
silently degrade:

- the workflow could clarify well in conversation, but not force those clarified
  decisions into explicit artifact fields
- high-risk capabilities could be decomposed without a compact check that their
  purpose, boundary, and acceptance proof were concrete enough for planning
- high-impact gray areas could still be handled as ordinary follow-up questions even
  when the real need was a clearer requirement-level fork between 2-3 viable shapes
- release readiness focused on current understanding and planning ambiguity, but did
  not explicitly gate on review of the written `spec.md`, `alignment.md`, and
  `context.md` package

That left a downstream failure mode where:

- the conversation was better than the artifacts
- planners had to reconstruct decisions from chat-style clarification history
- requirement-level forks were not always preserved as explicit outcomes
- `/sp-plan` could inherit weak artifact structure even when the verbal alignment was
  strong

## Goals

- Make high-risk capability decomposition more planning-safe.
- Force high-impact requirement forks into explicit option handling when needed.
- Ensure the written artifact set is reviewed before handoff to `/sp-plan`.
- Preserve the current `sp-specify` identity as a requirement-alignment workflow,
  not an implementation workflow.
- Keep the enhancement shared-first across integrations.

## Non-Goals

- Do not add browser or visual clarification flows.
- Do not turn `sp-specify` into open-ended brainstorming.
- Do not shift implementation architecture selection into `sp-specify`.
- Do not require git commits at the end of the specification phase.
- Do not add a new standalone CLI command for specification review.

## Design Principles

The approved direction follows four principles:

1. Clarification quality must survive into artifacts, not remain trapped in the chat
   transcript.
2. Requirement-level ambiguity should be handled as explicit forks when it materially
   changes behavior, scope, compatibility, or acceptance proof.
3. High-risk capability decomposition should fail early when boundaries are still
   fuzzy.
4. `/sp-plan` readiness depends on the written package being reviewable, not just on
   a strong verbal recap.

## Approved Direction

The approved hardening model has three additions.

### 1. Capability Checkpoints

After capability decomposition, `sp-specify` now requires a short checkpoint for each
high-risk capability:

- purpose / outcome
- boundary and non-goals
- acceptance proof

This is deliberately narrow. The checkpoint is not a mini-plan and not a technical
architecture section. It exists to catch capability slices that still sound coherent
at a high level but are too vague for safe downstream planning.

If a checkpoint still depends on fuzzy language, clarification must reopen for that
capability instead of moving on to sibling capability work.

### 2. Decision-Fork Mode

When a high-impact gray area still has multiple viable requirement shapes, the
workflow now switches into decision-fork mode.

Decision-fork mode requires:

- 2-3 concrete options
- option differences that matter at the requirement layer
- one recommended option with a short rationale

This mode is restricted to requirement-shaping decisions such as:

- workflow behavior
- boundary handling
- compatibility or migration expectations
- acceptance-proof shape

This mode must **not** be used for:

- implementation architecture brainstorming
- framework or tool selection
- low-risk defaults that do not materially change planning

The purpose is to convert ambiguous “preferences” into preserved requirement
decisions before planning begins.

### 3. Artifact Review Gate

Before `/sp-plan` handoff, `sp-specify` now performs an explicit artifact review gate.

The review gate checks the written artifact set, not just the current understanding.
The minimum checks are:

- placeholders or TODOs
- contradictions or capability drift
- missing capability checkpoints
- weak acceptance proof
- requirement-vs-implementation drift

If collaboration is justified and available, the workflow may use one read-only
reviewer lane to inspect the artifact set. This is intentionally a review lane, not a
second authoring lane.

After review, the user is asked to choose the next path explicitly:

- proceed to `/sp.plan`
- revise current artifacts
- continue analysis with `/sp.spec-extend`

This closes the gap between “the conversation sounds aligned” and “the artifact set
is genuinely ready for planning.”

## Artifact Model Changes

The hardening work changes two shared templates and the `sp-specify` command
contract.

### `alignment.md`

The alignment report now carries:

- capability checkpoints
- high-impact decision forks
- artifact review gate outcome

This makes `alignment.md` the explicit record of why the written package was judged
safe enough for planning.

### `context.md`

The context artifact now carries:

- capability checkpoints
- decision fork outcomes

This keeps downstream planning from reconstructing those decisions from the
clarification transcript or from the alignment report alone.

### `requirements.md` checklist

The generated specification checklist now validates:

- high-risk capabilities have checkpoints
- high-impact decision forks are resolved or explicitly force-carried

This extends readiness from “artifact files exist” to “artifact structure captures the
new contract.”

## Workflow Shape

The enhanced `sp-specify` flow is still:

```text
specify -> plan
```

The hardening does **not** insert a new mandatory stage. Instead, it strengthens the
exit contract of `sp-specify`.

The relevant internal shape becomes:

1. whole-feature analysis
2. capability decomposition
3. capability checkpoints for high-risk slices
4. gray-area clarification with decision-fork mode where needed
5. current-understanding confirmation gate
6. artifact generation
7. artifact review gate
8. explicit handoff choice

## Why This Is Not Brainstorming

The enhancement is inspired by stronger design-stage discipline, but it intentionally
does not import a full brainstorming workflow.

Specifically:

- `sp-specify` remains requirement-alignment-first
- clarification stays bounded to planning-critical ambiguity
- the workflow still prohibits turning the stage into open-ended ideation
- no visual companion or browser lane is introduced

This preserves the repository’s existing rule that `sp-specify` should not degrade
into freeform brainstorming.

## Implementation Surfaces

The implementation is shared-template-first and lands in these files:

- `templates/commands/specify.md`
- `templates/alignment-template.md`
- `templates/context-template.md`
- `tests/test_alignment_templates.py`

Because `sp-specify` skill mirrors derive from the shared templates, the design
propagates across skills-based integrations without introducing Codex-only wording in
the shared contract.

## Testing Strategy

The implementation was test-driven at the template-contract layer.

The regression coverage now asserts that:

- `sp-specify` includes decision-fork mode language
- `sp-specify` includes capability checkpoint language
- `sp-specify` includes the artifact review gate contract
- `alignment-template.md` exposes sections for capability checkpoints, high-impact
  decision forks, and artifact review gate
- `context-template.md` exposes sections for capability checkpoints and decision fork
  outcomes

## Implementation Resolution

The implementation shipped with these concrete resolutions:

- capability checkpoints are recorded only for high-risk capabilities, not every
  capability by default
- decision-fork mode is requirement-layer only and explicitly excludes
  implementation-architecture brainstorming
- artifact review is a gate before `/sp-plan`, not a post-plan audit
- reviewer-lane usage stays read-only and optional based on collaboration strategy
- the user-facing flow remains text-only

## Decision

Proceed with `sp-specify` alignment hardening as a shared text-only enhancement:

- add capability checkpoints
- add decision-fork mode
- add an artifact review gate before `/sp-plan`

This raises planning safety without adding a new mainline stage, without introducing
visual clarification, and without changing `sp-specify` into a generic brainstorming
workflow.
