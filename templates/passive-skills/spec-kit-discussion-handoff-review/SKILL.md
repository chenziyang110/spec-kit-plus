---
name: spec-kit-discussion-handoff-review
description: Review an agent-only discussion requirement contract before it becomes ready or is consumed downstream.
---

# Discussion Contract Review

Use when `sp-discussion` asks for final review, a user requests changes, or `sp-specify`/`sp-quick` reports contract integrity failure.

## Authority

Review `.specify/discussions/<slug>/handoff-to-specify.json`. It is the only handoff authority. Do not require, generate, or compare a Markdown companion.

Human-facing explanation belongs in the visible reply; the contract remains schema-first and agent-only.

Read supporting `discussion-state.md`, `requirements.md`, `technical-options.md`, `project-context.md`, or `open-questions.md` only when a named source-evidence ref is stale, missing, contradictory, or required to repair a specific field. Do not sweep them by default.

## Review Order

1. Goal and in/out/deferred scope.
2. Context boundary and implementation target.
3. Evidence authority, stale conditions, hard/soft unknowns, and conflicts.
4. Selected direction, accepted tradeoffs, and only rejected alternatives that could reappear.
5. Success criteria and downstream planning constraints.
6. `MP-*`, `CA-###`, dependencies, and stop/reopen conditions.
7. Consumer eligibility, coverage/planning gates, and protected digest.

## Verdict

Return one structured verdict:

- `approve`: no semantic or integrity blocker;
- `request-changes`: name exact JSON refs and required corrections;
- `blocked`: name cause, owner, safe retry, and stop condition.

For the visible human review, explain the decision being requested, scope and exclusions, readiness checks, protected review criteria, carry-forward coverage, blocking issues, required changes, and next action. The agent chooses the visible headings and layout; no fixed review card is required.

Deterministic field/schema/digest failures are repaired through `specify discussion validate-handoff` and `sp-discussion`. Review judgment must not silently patch upstream truth.

After changes, recompute the digest and require confirmation of the current revision. Do not treat confirmation of an older digest as approval.

## Minimum-Sufficient Rule

Keep a field only when omitting it can change downstream action, lose a requirement or obligation, force rediscovery, weaken validation, or prevent safe recovery. Remove presentation prose, duplicated history, and fields irrelevant to eligible consumers.
