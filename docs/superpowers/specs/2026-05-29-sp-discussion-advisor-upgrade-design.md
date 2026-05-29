# sp-discussion Advisor Upgrade Design

**Date:** 2026-05-29
**Status:** Proposed
**Owner:** Codex

## Summary

This design upgrades `sp-discussion` from a lightweight pre-specification interview
into a senior product-engineering advisory workflow.

The approved direction is to keep the existing `sp-discussion` command and artifact
model, but strengthen its conversational contract in four ways:

- require a truth pass before project-specific technical advice
- answer in a boss-friendly advisory shape that non-technical decision makers can
  understand
- maintain a current discussion compass so long conversations do not lose context
- avoid toothpaste-style interaction where the user must repeatedly pull out every
  useful implication

The change is intentionally a shared prompt, state, and test-contract improvement.
It does not add a new workflow, implementation mode, or project-cognition authority
model.

## Problem Statement

`sp-discussion` already has the right high-level pieces:

- a context boundary gate
- a staged project cognition gate
- live repository evidence as the authority for current project facts
- adaptive question packs
- durable discussion artifacts and handoff review gates

The gap is behavioral. In practice, the workflow can still feel too much like an
ordinary interview:

- it can offer implementation options before it has convincingly established the
  current project truth
- it may sound confident about a direction that is actually an assumption
- it can reply to only the literal point the user raised instead of expanding the
  adjacent product, architecture, workflow, and verification implications
- it can make a non-technical owner work too hard to understand why a technical
  step matters
- after many turns, the user can lose track of what has been confirmed, what changed,
  and what still needs a decision

This creates a trust problem. A technical user may see that the agent does not yet
understand the repository. A non-technical owner may not know enough to detect that
gap, but still needs a professional advisor who avoids unnecessary work and explains
the reasoning in decision-friendly language.

## Goals

- Make `sp-discussion` feel like a senior advisor with deep product and engineering
  judgment.
- Require project-specific advice to be grounded in current project truth.
- Separate confirmed facts, assumptions, recommendations, and user decisions.
- Give boss-friendly explanations before technical detail.
- Preserve technical traceability for engineers.
- Keep the user oriented during long discussions.
- Reduce repeated narrow back-and-forth by proactively surfacing adjacent issues and
  next discussion paths.
- Preserve the existing `sp-discussion` command and handoff lifecycle.

## Non-Goals

- Do not add a new `sp-advisor` workflow.
- Do not make `sp-discussion` edit source code, tests, plans, or specs.
- Do not make project cognition authoritative evidence for current behavior.
- Do not force a heavy repository scan for purely product-framing conversations.
- Do not require a recap after every single turn when the turn is trivial.
- Do not make the workflow verbose by default; the advisory shape should be concise
  and decision-oriented.

## Approved Direction

The approved model adds four protocols to `sp-discussion`.

### 1. Truth Pass

When the user asks for advice that depends on current project reality, the workflow
must complete a bounded truth pass before giving project-specific technical options.

The truth pass applies when a turn involves:

- current project behavior
- command, template, script, test, or documentation surfaces
- implementation path or affected surface claims
- existing capability reuse
- cross-CLI propagation
- compatibility, lifecycle, state, security, or downstream workflow risk

The truth pass records:

- `verified_project_facts`: facts proven from live files, command output, tests,
  docs, or explicitly cited evidence
- `open_assumptions`: claims that are still unproven
- `evidence_checked`: project cognition route, minimal live reads, repository files,
  commands, tests, docs, or user-provided references inspected
- `advice_confidence`: `high`, `medium`, `low`, or `blocked`

Project cognition remains advisory navigation. It helps select minimal live reads,
but live repository evidence proves current project behavior.

Before the truth pass completes, `sp-discussion` may discuss product intent and
decision shape, but must not name affected files, modules, APIs, tests, or
implementation paths as facts.

### 2. Boss-Friendly Advisor Response

`sp-discussion` should answer like a senior product-engineering advisor, not like a
support chatbot.

For substantive turns, the response should use this shape, scaled to the complexity
of the turn:

```text
Judgment:
The decision-level answer in plain language.

Evidence:
What is known from the project or from the user's confirmed intent.

Risk:
What can go wrong if we choose the obvious or premature path.

Recommendation:
The advised direction, including when not to choose it.

Next discussion paths:
The most useful adjacent decisions or checks to consider next.
```

The first sentence should be understandable to a non-technical owner. Technical
detail follows only after the decision-level judgment is clear.

If evidence is insufficient, the workflow should say that directly:

```text
I cannot responsibly recommend an implementation path yet because this depends on
the current project shape. I need to verify the existing command, template, and test
surfaces first.
```

That response is not a deflection. It is the professional answer when the risk is
premature solutioning.

### 3. Discussion Compass

Long discussions need a durable "where we are" view so the user does not have to
remember earlier turns.

`sp-discussion` should maintain a compact current discussion compass in
`discussion-state.md` and refresh it at semantic checkpoints.

The compass answers:

- what are we solving now?
- what has been confirmed?
- what changed from earlier thinking?
- what remains undecided?
- what is the current recommended direction?
- what is the next useful decision?

In normal replies, the workflow may include a short `Where we are` section when it
helps orientation, especially after:

- several turns on the same topic
- a topic change
- a confirmed product decision
- a newly proven project fact
- a changed recommendation
- a handoff-readiness discussion
- the user signals that context is becoming hard to track

The compass is not a transcript. It is a decision-oriented summary.

### 4. Anti-Toothpaste Protocol

The workflow should not make the user extract value one tiny answer at a time.

When the user raises a point, `sp-discussion` should infer the broader decision
surface and proactively identify:

- the literal issue the user raised
- the deeper decision or risk behind it
- adjacent product, technical, workflow, or verification implications
- which items can be discussed together
- which item requires a clear user decision
- a recommended order for the next discussion steps

It should still avoid overwhelming the user. The rule is not "ask many questions."
The rule is:

- show the map
- recommend a next path
- ask only the highest-impact question when user judgment is needed

This extends the existing Adaptive Question Pack. Adaptive questions reduce narrow
back-and-forth, but the anti-toothpaste protocol also requires the agent to surface
the surrounding decision map and avoid passively waiting for the user to discover
every implication.

## Interaction Model

For a substantive product or technical turn, the ideal reply is:

```text
Judgment:
...

What I know / need to verify:
...

Why this matters:
...

Recommendation:
...

Next useful directions:
1. ...
2. ...
3. ...

One decision I need from you:
...
```

For a short or low-risk turn, this can collapse into a few sentences. The point is
not format rigidity; the point is professional advisory behavior.

## State Model Changes

Add or strengthen these fields in `templates/discussion-state-template.md`:

- `truth_pass_status: not-needed | needed | in-progress | complete | blocked`
- `verified_project_facts: []`
- `open_assumptions: []`
- `evidence_checked: []`
- `advice_confidence: high | medium | low | blocked | none`
- `discussion_compass_status: current | stale | missing`
- `current_decision_frame: one-sentence decision-level framing`
- `confirmed_decisions: []`
- `changed_recommendations: []`
- `next_discussion_paths: []`

These fields are not a new source of truth separate from the discussion artifacts.
They are the compact current-state index used to resume and orient the conversation.

## Artifact Model Changes

The existing artifact set stays the same:

- `discussion-state.md`
- `discussion-log.md`
- `requirements.md`
- `technical-options.md`
- `project-context.md`
- `open-questions.md`
- handoff files only after explicit handoff request

The contents become stricter:

- `project-context.md` should record truth-pass evidence, not only cognition route
  notes.
- `technical-options.md` should distinguish evidence-backed options from assumption-
  backed options.
- `open-questions.md` should separate user decisions from evidence gaps.
- `discussion-state.md` should carry the discussion compass and advice confidence.

No new required artifact is introduced in the first implementation cut. A future
`discussion-brief.md` could be added only if the compact compass in
`discussion-state.md` proves insufficient.

## Response Quality Rules

`sp-discussion` should follow these rules:

1. Do not recommend implementation work before the relevant truth pass.
2. Do not make the user correct avoidable project ignorance when the repository can
   answer the question.
3. Do not hide uncertainty inside confident prose.
4. Do not ask the user for facts that bounded project reads can discover.
5. Do not answer only the narrow literal question when the broader decision surface
   matters.
6. Do not overload the user with a question list; show the decision map and ask the
   one question that needs human judgment.
7. Start with the decision-level meaning, then give technical evidence.
8. Explicitly call out unnecessary or premature work when that is the professional
   recommendation.

## Implementation Surfaces

The first implementation should update shared surfaces:

- `templates/commands/discussion.md`
- `templates/command-partials/discussion/shell.md`
- `templates/discussion-state-template.md`
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md` when advisor
  behavior changes route recommendations, handoff readiness wording, or discussion
  selection guidance
- `tests/test_alignment_templates.py`
- generated integration tests that assert shared command/skill output where needed,
  especially generated passive skill output
- `tests/test_specify_guidance_docs.py` when README, quickstart, or handbook wording
  changes
- `tests/integrations/test_cli.py` and `src/specify_cli/__init__.py` only if CLI help,
  command descriptions, skill descriptions, or user-facing entrypoint text changes
- `README.md`, `PROJECT-HANDBOOK.md`, `docs/quickstart.md`,
  `docs/installation.md`, and `templates/project-handbook-template.md` when
  user-facing or generated-project workflow descriptions need to mention the
  upgrade

Because this is a shared workflow behavior, implementation should avoid
Codex-specific wording unless a Codex integration surface needs separate generated
coverage.

If an implementation intentionally leaves any of these surfaces unchanged, it should
record the stand-down reason in the implementation plan so the omission is an
explicit decision rather than accidental drift.

## Testing Strategy

Add template-contract regression coverage for:

- truth pass required before project-specific technical advice
- project cognition remains advisory and live evidence remains authoritative
- boss-friendly advisor response shape exists in the command and shell partial
- discussion compass fields exist in the state template
- anti-toothpaste protocol requires broader decision mapping without asking many
  required questions
- state fields distinguish verified facts, assumptions, evidence checked, advice
  confidence, and next discussion paths

Existing tests for context boundary, staged cognition, adaptive question packs,
handoff integrity, and discussion-state independence should continue to pass.

## Risks

### 1. Over-Verbose Replies

The advisor shape could become too long if applied mechanically.

Mitigation: require scaling to turn complexity. Short turns can use a compressed
version as long as they preserve judgment, evidence status, and next step.

### 2. Over-Blocking on Truth Pass

The workflow could refuse useful product framing because it is waiting for project
evidence.

Mitigation: product framing may continue without project cognition. Only
project-specific technical advice and affected-surface claims require truth pass.

### 3. Duplicate State

The discussion compass could drift from `requirements.md`, `technical-options.md`,
or `project-context.md`.

Mitigation: treat the compass as a compact index and refresh it only at semantic
checkpoints. Durable decisions still live in the appropriate artifacts.

### 4. False Professionalism

Adding senior-language labels is not enough. The workflow must actually change
decision behavior.

Mitigation: tests should assert the evidence threshold, fact/assumption separation,
and anti-toothpaste decision mapping, not just wording like "senior advisor."

## Decision

Proceed with a shared `sp-discussion` advisor upgrade.

The workflow should keep its current command, artifacts, and explicit handoff model,
but add:

- Truth Pass
- Boss-Friendly Advisor Response
- Discussion Compass
- Anti-Toothpaste Protocol

This directly addresses the trust gap: the agent should first understand the current
project truth, then explain the decision in owner-friendly language, preserve the
conversation state, and proactively surface the next useful directions instead of
making the user pull out each point one turn at a time.
