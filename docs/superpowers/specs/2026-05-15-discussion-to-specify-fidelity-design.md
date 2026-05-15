# Discussion To Specify Fidelity Design

## Summary

Strengthen the handoff from `sp-discussion` into `sp-specify` so the user's confirmed product intent, goals, boundaries, decisions, important references, and technical trade-off rationale cannot be silently lost or rewritten before implementation.

The design introduces a compact **Must-Preserve Ledger** in the discussion handoff, a `sp-specify` coverage gate that proves every ledger item was mapped into the formal specification package, and a hard conflict blocker. If a discussion conclusion conflicts with repository evidence, constitution rules, or established architecture constraints, downstream workflows must stop and ask the user to decide; they may not silently reinterpret the discussion result.

This is intentionally not a full transcript preservation system. It preserves only the semantic units that can materially change the final product or implementation outcome.

## Goals

- Preserve important discussion conclusions across `sp-discussion -> sp-specify -> sp-plan -> sp-tasks -> sp-implement`.
- Prevent confirmed discussion goals, scope, non-goals, references, decisions, and trade-off rationale from being compressed into vague prose or dropped.
- Give `sp-specify` a deterministic way to prove it consumed the discussion handoff.
- Block on conflicts with repository evidence or project rules instead of silently modifying settled user decisions.
- Keep the design compatible with the current artifact chain: `spec.md`, `alignment.md`, `context.md`, `references.md`, `plan.md`, and `tasks.md`.
- Keep workflow overhead proportional by tracking only implementation-shaping semantic items, not every sentence from the discussion.

## Non-Goals

- Do not preserve a verbatim transcript of the whole discussion.
- Do not make `handoff-to-specify.json` a parallel source of truth after `sp-specify` compiles the formal artifacts.
- Do not allow `sp-specify`, `sp-plan`, or `sp-tasks` to automatically rewrite settled discussion decisions when conflicts are found.
- Do not create feature branches, implementation plans, task lists, or source changes as part of this design.
- Do not make the fidelity mechanism Codex-only.

## Current Context

`sp-discussion` already writes resumable artifacts under `.specify/discussions/<slug>/` and creates `handoff-to-specify.md` only when the user explicitly asks for handoff.

`sp-specify` already has a discussion handoff intake section. It treats a discussion handoff as an authoritative input to the brainstorming kernel and says to preserve confirmed requirements, non-goals, settled decisions, selected technical direction, open questions, and evidence.

The gap is that the current contract is mostly prose. It says preservation should happen, but it does not define a field-level preservation checklist or a testable coverage gate. A high-quality handoff needs a small structured layer that answers:

- What exactly must not be lost?
- Which source established it?
- Where did `sp-specify` map it?
- What happens if a later workflow sees contradictory evidence?

## Core Concept: Must-Preserve Ledger

`sp-discussion` should add a **Must-Preserve Ledger** to `handoff-to-specify.md` when the user requests handoff.

Each ledger item is a compact semantic unit that would cause product or implementation drift if dropped. Every item receives an `MP-###` ID.

Ledger item types:

- `goal`: product goal, target user, user value, or intended outcome
- `scope`: behavior included in the current delivery boundary
- `non_goal`: behavior explicitly excluded or deferred
- `scenario`: usage path, success signal, or acceptance-shaping case
- `decision`: confirmed product, workflow, compatibility, or technical direction
- `reference`: important user-supplied reference, repository evidence, policy, spec, external document, or example
- `tradeoff`: selected or rejected technical option and the rationale that should not be rediscovered incorrectly
- `blocking_question`: unresolved question that must be closed before planning or implementation can safely proceed

Each item records:

```yaml
- id: MP-001
  type: goal
  claim: The exact conclusion that must be preserved.
  source: discussion-log.md#..., requirements.md#..., technical-options.md#..., project-context.md#..., or user confirmation.
  downstream_requirement: How later artifacts must carry this forward.
  blocking_level: hard | soft
```

`blocking_level` is required for `blocking_question` and optional for other item types. If omitted, the default is `hard` for decisions, non-goals, scope, and selected trade-offs, and `soft` for contextual references.

The ledger is not meant to track every note. `sp-discussion` should include items marked or implied as:

- confirmed by the user
- selected from a technical options board
- critical to acceptance
- critical to scope or non-goals
- key evidence or reference material
- unresolved and planning-sensitive

## Handoff Artifact Shape

The human-facing artifact remains:

```text
.specify/discussions/<slug>/handoff-to-specify.md
```

It should include:

- frontmatter with `source_command: sp-discussion`, `discussion_slug`, `status: handoff-ready`, `updated_at`, and `source_files`
- short summary of the mature discussion result
- Must-Preserve Ledger
- discussion source map
- unresolved questions
- explicit instructions to `sp-specify`

`sp-discussion` should also create a machine-readable companion:

```text
.specify/discussions/<slug>/handoff-to-specify.json
```

The JSON companion mirrors the ledger IDs and key fields from Markdown. It exists to reduce parsing ambiguity and support tests. The Markdown remains the operator-readable handoff; the JSON is the structured contract.

Example:

```json
{
  "version": 1,
  "source_command": "sp-discussion",
  "discussion_slug": "semantic-fidelity",
  "status": "handoff-ready",
  "source_files": [
    "discussion-state.md",
    "discussion-log.md",
    "requirements.md",
    "technical-options.md",
    "project-context.md",
    "open-questions.md"
  ],
  "must_preserve": [
    {
      "id": "MP-001",
      "type": "goal",
      "claim": "Preserve the user's confirmed product outcome.",
      "source": "requirements.md#feature-goal",
      "downstream_requirement": "Carry into spec.md Feature Goal and plan.md Summary.",
      "blocking_level": "hard"
    }
  ]
}
```

The JSON companion is not a new long-term truth source. Once `sp-specify` consumes it, the formal truth should live in the active feature's `spec.md`, `alignment.md`, `context.md`, `references.md`, and generated brainstorming truth files.

## Handoff Readiness Rule

`sp-discussion` may mark a session `handoff-ready` only when:

- every confirmed goal, scope item, non-goal, scenario, selected decision, critical reference, selected trade-off, and blocking open question has a ledger item
- every ledger item has a stable `MP-###` ID
- every ledger item names a source file or user confirmation
- every blocking open question has `blocking_level`, owner, and latest expected resolution phase
- the handoff includes a clear instruction that `sp-specify` must block rather than rewrite on conflict

If a requirement or technical option is not important enough to appear in the ledger, it may remain in the discussion source files as background context. The ledger is the preservation boundary.

## sp-specify Intake

When invoked with `.specify/discussions/<slug>/handoff-to-specify.md` or a pasted handoff block, `sp-specify` must:

1. Read the Markdown handoff.
2. Read `.specify/discussions/<slug>/handoff-to-specify.json` when present.
3. Extract or reconstruct the Must-Preserve Ledger before parsing the rest of the feature request.
4. Record `entry_source: sp-discussion` and the handoff path in the active feature artifacts.
5. Copy the ledger into `FEATURE_DIR/brainstorming/handoff-to-specify.json` as a preservation checklist.
6. Continue through the normal brainstorming kernel. The ledger seeds facts, route, intent, complexity, unknowns, and final specification artifacts; it does not bypass the kernel.

The active feature copy should track mapping status:

```json
{
  "version": 2,
  "entry_source": "sp-discussion",
  "source_handoff": ".specify/discussions/semantic-fidelity/handoff-to-specify.md",
  "source_handoff_json": ".specify/discussions/semantic-fidelity/handoff-to-specify.json",
  "must_preserve": [
    {
      "id": "MP-001",
      "type": "goal",
      "claim": "Preserve the user's confirmed product outcome.",
      "source": "requirements.md#feature-goal",
      "downstream_requirement": "Carry into spec.md Feature Goal and plan.md Summary.",
      "mapped_to": ["spec.md#Feature Goal", "alignment.md#Domain Closure Log"],
      "status": "mapped"
    }
  ],
  "conflicts": [],
  "coverage_status": "complete"
}
```

## Coverage Gate

Before `sp-specify` can mark the package ready for `/sp.plan`, it must complete a discussion coverage gate when `entry_source` is `sp-discussion`.

Coverage rules:

- Every `MP-*` item must have at least one `mapped_to` target.
- `goal`, `scope`, `scenario`, and acceptance-shaping items must appear in `spec.md`.
- `non_goal` and boundary items must appear in `spec.md` and, when implementation-shaping, in `context.md`.
- `decision` items must appear in `spec.md#Decision Capture` or the equivalent locked-decision section and in `alignment.md` when they affect planning readiness.
- `reference` items must appear in `references.md`; if the reference constrains implementation, it must also be named in `context.md` or `plan.md` later.
- `tradeoff` items must appear in `context.md`, `alignment.md`, or planning constraints according to whether the trade-off affects specification, planning, or execution.
- `blocking_question` items with `hard` blocking level must become hard unknowns and prevent a `/sp.plan` recommendation until resolved by the user or explicit evidence accepted by the user.
- Items may be deferred only when their ledger entry records the downstream phase that owns resolution and the stop-and-reopen condition.

If coverage is incomplete, `sp-specify` must keep `coverage_status: incomplete`, update `workflow-state.md`, and avoid recommending `/sp.plan`.

## Conflict Blocker

The user-selected policy is strict: conflicts block and return to the user.

If `sp-specify`, `sp-plan`, or `sp-tasks` finds that an `MP-*` item conflicts with repository evidence, constitution rules, project rules, project cognition evidence, or architecture constraints, the workflow must stop and ask the user to decide.

Conflict output should name:

- ledger ID
- original discussion conclusion
- source file or user confirmation
- conflicting evidence
- why the conflict matters
- available user decisions: keep, revise, drop, or defer with an explicit risk contract

The workflow may not silently reinterpret, downgrade, or replace the discussion conclusion. It may continue only after the user decides.

## Downstream Propagation

`sp-specify` is the primary compiler, but the fidelity chain must continue.

### sp-plan

`sp-plan` already reads `FEATURE_DIR/brainstorming/handoff-to-specify.json`, `spec.md`, `alignment.md`, `context.md`, and `references.md`.

It should treat mapped `MP-*` items as preservation obligations:

- goals inform `plan.md#Summary`
- decisions enter `plan.md#Locked Planning Decisions`
- implementation-shaping references enter `plan.md#Alignment Inputs` or `Implementation Constitution`
- architecture-sensitive decisions enter `Implementation Constitution`
- unresolved hard items block planning
- any conflict blocks and returns to the user

`plan.md` should include a compact `Must-Preserve Carry-Forward` section or extend `Locked Planning Decisions` to include the relevant `MP-*` IDs.

### sp-tasks

`sp-tasks` should preserve implementation-shaping `MP-*` IDs through task generation:

- decisions and non-goals map to task guardrails
- references map to required references on affected tasks
- scenario and acceptance items map to user story tasks or validation checkpoints
- trade-offs map to forbidden drift or explicit review checkpoints
- conflicts block and return to the user

`tasks.md` should not need every `MP-*` item. It only carries items that affect execution shape, validation, task ordering, references, or forbidden drift.

### sp-implement

`sp-implement` should inherit the relevant `MP-*` IDs from `tasks.md` and task packets.

The implementation leader or worker should not need to reconstruct the whole discussion. Each task should carry the preservation obligations that apply to that task:

- required references
- forbidden drift
- user-visible acceptance signals
- non-goal boundaries
- conflict/reopen conditions

Completion evidence should prove the relevant obligations were honored or identify the user-approved change that revised them.

## Tests And Verification

Regression coverage should focus on contracts, not end-to-end natural-language perfection.

Template tests:

- `discussion.md` requires a Must-Preserve Ledger in `handoff-to-specify.md`.
- `discussion.md` requires a JSON companion `handoff-to-specify.json`.
- `discussion.md` forbids `handoff-ready` unless confirmed and critical items are represented in the ledger.
- `specify.md` consumes discussion handoff ledgers before normal parsing.
- `specify.md` requires coverage status before recommending `/sp.plan`.
- `specify.md`, `plan.md`, and `tasks.md` all contain conflict-blocker language for `MP-*` items.

Artifact validation tests:

- `FEATURE_DIR/brainstorming/handoff-to-specify.json` accepts the new ledger shape.
- every `must_preserve` item requires `id`, `type`, `claim`, `source`, `downstream_requirement`, `status`, and `mapped_to` once coverage is complete.
- `coverage_status: complete` is invalid when any item is unmapped.
- hard `blocking_question` items prevent compile readiness unless resolved.

Integration tests:

- Markdown, TOML, and skills-based integrations generate the updated discussion and specify contracts.
- Generated Codex, Claude, Gemini, Cursor, and other supported surfaces preserve the same cross-workflow semantics.

Documentation tests:

- README and project handbook explain that `discussion` is for shaping rough ideas and that handoff uses a fidelity ledger.
- Docs distinguish discussion background context from must-preserve obligations.

## Acceptance Criteria

- `sp-discussion` handoff packages include a Must-Preserve Ledger.
- `sp-specify` consumes the ledger as authoritative input without bypassing its own brainstorming kernel.
- `sp-specify` cannot recommend `/sp.plan` until every must-preserve item is mapped, resolved, or explicitly deferred with a downstream contract.
- Conflicts with repository or constitution evidence block and return to the user.
- `sp-plan` and `sp-tasks` carry relevant `MP-*` IDs into planning decisions, implementation constitution, guardrails, required references, validation checkpoints, or task packets.
- Downstream implementation work can see the applicable preservation obligations without reading the entire discussion archive.
- Tests prove that unmapped hard ledger items cannot silently disappear.

## Risks And Mitigations

- Risk: The ledger becomes too heavy for ordinary discussions.
  Mitigation: Include only confirmed, critical, selected, acceptance-shaping, or blocking items.

- Risk: Agents treat the JSON companion as a new permanent source of truth.
  Mitigation: Define it as an intake and coverage checklist; downstream truth remains the compiled feature artifacts.

- Risk: Conflicts block too often.
  Mitigation: Block only when an `MP-*` item materially conflicts with evidence or project rules. Background context may be corrected without escalation if it is not marked must-preserve.

- Risk: Important references are copied but not used.
  Mitigation: Require reference items to map to `references.md`, and when implementation-shaping, to `context.md`, `plan.md`, or task required references.

- Risk: Downstream artifacts become noisy with IDs.
  Mitigation: Carry IDs only where they shape planning, tasking, validation, or implementation guardrails.

## Rollout Surface

Implementation should update the normal workflow change surface:

- `templates/commands/discussion.md`
- `templates/command-partials/discussion/shell.md`
- `templates/commands/specify.md`
- `templates/brainstorming-handoff-specify-template.json`
- `templates/commands/plan.md`
- `templates/commands/tasks.md`
- `templates/plan-template.md`
- `templates/tasks-template.md`
- `templates/project-handbook-template.md`
- README and project handbook workflow guidance
- artifact validation tests and integration template tests

This should be treated as a cross-CLI workflow contract change because it affects generated workflows, not a single integration.
