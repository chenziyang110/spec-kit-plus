---
name: spec-kit-discussion-handoff-review
description: Use when reviewing a Spec Kit Plus discussion handoff, checking whether an `sp-discussion` draft can become `handoff-ready`, or assessing whether a handoff-ready closeout summary is complete enough for downstream `sp-specify`.
origin: spec-kit-plus
---

# Spec Kit Discussion Handoff Review

This passive skill supplies a fixed review protocol for `sp-discussion` handoff
packages. It is not a user-invoked workflow and it does not replace
`sp-discussion` or `sp-specify`.

Use it when:

- the user asks to review, approve, or repair a discussion handoff
- an agent is about to mark a discussion `handoff-ready`
- an agent is summarizing a newly ready handoff for the user
- another workflow consumes `.specify/discussions/<slug>/handoff-to-specify.md`
  or `.specify/discussions/<slug>/handoff-to-specify.json`

## Required Inputs

Read these files before issuing a verdict when they exist:

- `.specify/discussions/<slug>/discussion-state.md`
- `.specify/discussions/<slug>/handoff-to-specify.md`
- `.specify/discussions/<slug>/handoff-to-specify.json`
- `.specify/discussions/<slug>/handoff-assessment.md`
- `.specify/discussions/<slug>/requirements.md`
- `.specify/discussions/<slug>/technical-options.md`
- `.specify/discussions/<slug>/project-context.md`
- `.specify/discussions/<slug>/open-questions.md`
- `.specify/discussions/<slug>/discussion-log.md` only when state, handoff,
  or review evidence appears stale or inconsistent

If either handoff file is missing, stop with `block-handoff`. Do not reconstruct
the missing file outside `sp-discussion`.

## Review Verdicts

Use exactly one verdict:

- `approve-handoff-ready`: the handoff can be or remain `handoff-ready`.
- `request-changes`: the handoff is close, but specific draft corrections are
  needed before user approval or ready marking.
- `block-handoff`: the package is unsafe for downstream `sp-specify` because a
  hard blocker, missing companion file, unresolved boundary, evidence conflict,
  or Markdown/JSON integrity failure exists.

## Fixed Review Output

Every review response must use these top-level sections in this order:

1. Review Verdict
2. What This Means
3. Evidence Read
4. Readiness Checks
5. Carry-Forward Coverage
6. Blocking Issues
7. Required Changes
8. Next Action

Do not answer with only file paths, status counters, or "looks good". The user
needs the reviewer judgment, the preservation risk, and the exact next action.

## Readiness Checks

Approve only if all required checks pass:

- `handoff_goal` is concrete and matches the user's confirmed intent.
- `context_boundary` is locked, including current project role, target project
  role, reference source, external systems, and evidence authority.
- Cross-project requests name `target_project_root` or explicitly state why the
  current project is the implementation target.
- `implementation_target` identifies the actual project or target surface to
  change and names any still-unverified target paths.
- `source_evidence` distinguishes live repository evidence, project cognition
  advisory routes, user confirmation, external sources, explicit assumptions,
  missing evidence, and conflicts.
- `blocking_unknowns` has `hard_unknown_count = 0` before ready marking.
- `open_conflict_count = 0` before ready marking.
- Soft unknowns have owner, latest resolve phase, and stop-and-reopen condition.
- `quality_gate.self_reviewed_at` is populated or `handoff_review_status` is
  `self-review-passed` before user approval.
- `quality_gate.status` is `user_confirmed` or `user-confirmed` before final
  `handoff-ready`.
- `planning_gate_status` is `ready` before downstream planning is recommended.
- `coverage_status` records what is proven, assumption-backed, deferred, or not
  applicable.
- `discussion_decision_digest` carries locked direction, rejected alternatives,
  accepted tradeoffs, experience commitments, review criteria carried forward,
  and must-not-dilute constraints when those signals appear in the discussion.
- Markdown/JSON agree on `handoff_goal`, `discussion_slug`, context boundary,
  implementation target, quality gate status, Must-Preserve IDs, consequence
  obligations, `hard_unknown_count`, and `open_conflict_count`.
- The Markdown handoff includes a `Handoff Reviewer Guide` with approval and
  change-request criteria for reviewers who do not know Spec Kit internals.
- The Markdown handoff includes a `Must-Preserve Ledger`.
- The ready summary quality check passes without needing `Ready Summary Quality`
  as a user-visible heading.

## Carry-Forward Coverage

Check that the Must-Preserve Ledger carries every semantic item that would cause
downstream drift if lost:

- goal
- selected scope
- non-goals and deferred scope
- user-visible scenarios or acceptance signals
- selected product and technical decisions
- critical references and reference-role boundaries
- trade-offs whose rationale must survive planning
- blocking or deferred questions with reopen conditions
- `CA-###` consequence obligations when the Senior Consequence Analysis Gate
  triggered

Each `MP-###` item must include `id`, `type`, `claim`, `source`,
`downstream_requirement`, `blocking_level`, `owner`, `latest_resolve_phase`,
`status`, and required deferred or superseded fields when applicable.

## Internal Ready Summary Quality Check

A final `handoff-ready` user summary is valid only when it gives enough context
for the user or a later agent to trust the transition without rereading the
entire discussion. It must include:

- the handoff goal in one sentence
- the selected product or technical direction
- the target project and evidence boundary
- the handoff Markdown and JSON paths
- Must-Preserve ID coverage, including count and notable examples
- hard unknown and open conflict counts
- quality gate status and user confirmation state
- whether Markdown/JSON agreement was checked
- the exact next command or consumption path

If the closeout says only that files were updated, counters are zero, and the
next step is review or `sp-specify`, return `request-changes` for an incomplete
ready summary.

## Draft User Review Summary Quality Check

A draft handoff user-review reply is valid only when it uses a concise draft handoff review card.
It must include:

- Draft Handoff Review: the decision being requested
- Recommended Route: the recommended downstream consumer and why
- Scope To Approve: the exact scope the user would approve
- Excluded Scope: work explicitly outside the draft
- Readiness Checks: self-review, hard unknown/conflict, and Markdown/JSON
  agreement status
- Package: the handoff Markdown and JSON paths
- Your Review Decision: approve as handoff-ready or request concrete changes

If the draft review says only that files were written, lists paths, and asks for
approval, return `request-changes` for an incomplete user-review summary.
An unrelated prompt, codebase explanation request, new target root, or new
product question is not approval and must leave the handoff in draft/user-review
state.

## Boundaries

- Do not review implementation code, tests, or architecture beyond the evidence
  needed to validate the handoff's claims.
- Do not rewrite product scope while reviewing. If scope is wrong, request a
  handoff change and route back to `sp-discussion`.
- Do not downgrade a hard unknown to a soft unknown to make the package ready.
- Do not ignore Markdown/JSON disagreement because one side looks more complete.
- Do not approve a bare yes/no user confirmation unless the user reviewed clear
  criteria from the `Handoff Reviewer Guide`.

## Next Action Rules

- For `approve-handoff-ready`, name the handoff paths and the exact downstream
  invocation or consumption path, but do not invoke `sp-specify` automatically.
- For `request-changes`, list the smallest concrete edits needed and keep the
  discussion in draft/user-review state.
- For `block-handoff`, name the blocker, the missing evidence or file, and the
  first safe recovery step inside `sp-discussion`.
