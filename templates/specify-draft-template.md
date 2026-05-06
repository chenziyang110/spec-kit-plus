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
