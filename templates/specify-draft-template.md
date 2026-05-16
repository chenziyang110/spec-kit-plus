# Specification Draft Ledger: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`
**Created**: [DATE]
**Status**: Active draft
**Purpose**: Fixed-heavy discovery content ledger and resume anchor for `sp-specify`

## Intent Analysis Record

- current_intent_hypothesis: [Best current understanding of the user's intended capability]
- likely_affected_surfaces: [Primary surfaces implicated by intent-analysis]
- biggest_open_ambiguity: [Highest-risk misunderstanding still to correct]

## Domain Progress Ledger

- current_domain: [goal-and-users | triggers-and-primary-flow | boundaries-and-non-goals | failure-paths-exceptions-and-permissions | dependencies-constraints-and-upstream-downstream-impact | acceptance-and-completeness-gap-closure]
- domain_statuses:
  - goal-and-users: [not-started | in-progress | confirmed-by-user | closed-by-existing-evidence | force-carried-with-risk | reopen-required]
  - triggers-and-primary-flow: [status]
  - boundaries-and-non-goals: [status]
  - failure-paths-exceptions-and-permissions: [status]
  - dependencies-constraints-and-upstream-downstream-impact: [status]
  - acceptance-and-completeness-gap-closure: [status]

## Question Batch Ledger

- **Batch**: [Batch identifier]
  Domain: [Active domain]
  Questions:
  - [Question 1]
  - [Question 2]
  - [Question 3]
  Answer summary: [Condensed summary of what the user answered or what evidence closed the batch]
  Disposition: [closed | reopen-required | force-carried-with-risk]

## Adversarial Review Ledger

- **Batch / domain**: [Which batch was reviewed]
  Challenge focus: [Contradiction, omission, hidden dependency, boundary conflict, etc.]
  Findings: [What the adversarial review surfaced]
  Reopen decision: [none | reopen current domain | escalate to final audit concern]

## Completeness Gap Register

- [Gap description] -> [Affected domain] -> [Why it threatens completeness] -> [Current disposition]
- [Missing boundary, capability, adjacent effect, or feasibility concern] -> [Affected domain] -> [Disposition]

## Final Audit Inputs

- audit_readiness: [not-ready | ready-for-audit | audit-failed | audit-passed]
- planning_readiness_summary: [Why the package is or is not ready to leave discovery]
- handoff_candidate: [/sp.plan | /sp.clarify | /sp.deep-research | undecided]

## Lossless State Companion

- Trusted recovery source: JSON stage artifacts plus `brainstorming/journal.ndjson`
- Human-readable companion: this file
- Markdown is not a trusted recovery source.
- If this file disagrees with structured stage artifacts, regenerate or repair this file from the structured state.

## Facts Lock Notes

- [field]: [current evidence-backed state]

## Route Lock Notes

- primary_route: [pending route]
- matched_rules:
  - [rule id]

## Intent Lock Notes

- goal: [locked goal]
- non_goals:
  - [excluded scope]
- success_criteria:
  - [observable outcome]
- must_preserve:
  - [invariant]
- allowed_optimization_scope:
  - [permitted redesign latitude]

## Complexity Lock Notes

- complexity_level: [T1 Local | T2 Structured | T3 Cross-Boundary | T4 Reconstruction | pending]
- matched_triggers:
  - [trigger rule]
- execution_mode: [solo | bounded-parallel | coordinated | pending]

## Unknown Handling Notes

- unresolved_unknowns:
  - field: [truth field]
    question: [question or evidence needed]
    blocking_level: [hard | soft]
    resolver: [user | evidence | downstream-contract | risk-waiver]
    latest_resolve_phase: [facts-lock | route-lock | intent-lock | complexity-lock | specify-compile]
    status: [open | resolved | deferred | waived]

## Handoff To Specify Notes

- facts_file: brainstorming/facts.json
- route_file: brainstorming/route.json
- intent_file: brainstorming/intent.json
- complexity_file: brainstorming/complexity.json
- compile_ready: [true | false]

## Brainstorming Companion Rules

- Every note must map to a field, rule, or lock state.
- After every answer, update the relevant truth file immediately.
- Do not use freeform brainstorming chat as a substitute for field closure.
- Route selection is valid only when `route.json` records a primary route, matched rules, and any rejected-route reasoning.
- Complexity selection is valid only when `complexity.json` records the chosen `T1 Local`, `T2 Structured`, `T3 Cross-Boundary`, or `T4 Reconstruction` level and the matched trigger rules.
- `unknown` is a pending decision object, not a default exit state.
- Every unresolved `unknown` must carry `field`, `question`, `blocking_level`, `resolver`, `latest_resolve_phase`, and `status`.
- Do not hand off past the current gate while a hard unknown remains unresolved.
