# Completeness Convergence Report: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`  
**Created**: [DATE]  
**Status**: [Aligned: ready for plan | Force proceed with known risks]

## Route And Complexity Summary

- Primary Route: [route]
- Matched Route Rules:
  - [rule id and evidence]
- Complexity Level: [T1 | T2 | T3 | T4]
- Matched Complexity Rules:
  - [rule id and evidence]
- Hard Unknowns Cleared: [yes/no]
- Soft Unknowns Carried:
  - [field, owner, latest resolve phase, and risk if any]
- Reopen Required: [yes/no]
- Structured Handoff: [brainstorming/handoff-to-specify.json status]

## Initial Intent Analysis

[Summarize the initial feature-shape hypothesis, the likely intended outcome,
the major affected surfaces, and the biggest ambiguity discovered during
intent-analysis.]

## Route And Complexity Summary

- **Primary Route**: [Locked route selected from route.json]
- **Complexity Level: [T1 | T2 | T3 | T4]**: [Locked complexity level carried from complexity.json]
- **Hard Unknowns Cleared**: [Which hard unknowns were resolved before handoff]
- **Reopen Required**: [Whether downstream work must reopen upstream truth before continuing]

## Domain Closure Log

| Domain | Closure State | Evidence Basis | Notes |
| --- | --- | --- | --- |
| goal-and-users | [confirmed-by-user | closed-by-existing-evidence | force-carried-with-risk | reopen-required] | [user | repo | docs | mixed] | [Why this domain closed or reopened] |
| triggers-and-primary-flow | [state] | [basis] | [notes] |
| boundaries-and-non-goals | [state] | [basis] | [notes] |
| failure-paths-exceptions-and-permissions | [state] | [basis] | [notes] |
| dependencies-constraints-and-upstream-downstream-impact | [state] | [basis] | [notes] |
| acceptance-and-completeness-gap-closure | [state] | [basis] | [notes] |

## Batch Adversarial Review Summary

- **Batch / domain**: [Which question batch was challenged]
  Challenge focus: [Contradiction, hidden dependency, omitted boundary, adjacent effect, etc.]
  Finding: [What the adversarial review concluded]
  Disposition: [accepted | reopened | force-carried]

- **Batch / domain**: [Repeat as needed]
  Challenge focus: [Focus area]
  Finding: [Result]
  Disposition: [accepted | reopened | force-carried]

## Critical Gaps and Reopen Decisions

- [Critical gap that blocked closure] -> [Domain reopened or final disposition] -> [How it was resolved or why it remains carried]
- [Missing capability, hidden dependency, or project-boundary conflict] -> [Action taken] -> [Evidence or remaining risk]

## Consequence Completeness

- Gate status: [not-triggered | ready | blocked | stood-down]
- Resolved `CA-###` obligations:
- Unresolved planning blockers:
- Force-carried risks:
- Required next workflow:

## Completeness Audit Outcome

- **Audit status**: [passed | failed | force-carried-with-risk]
- **Missing capability check**: [Result]
- **Boundary completeness check**: [Result]
- **Adjacent effects check**: [Result]
- **Domain-expected completeness check**: [Result]
- **Reasoning**: [Why the discovery package is or is not complete enough to leave `sp-specify`]

## Route And Complexity Summary

- **Primary Route**: [Compiled route classification]
- **Complexity Level**: [T1 Local | T2 Structured | T3 Cross-Boundary | T4 Reconstruction]
- **Hard Unknowns Cleared**: [yes | no]
- **Reopen Required**: [yes | no]

## Planning Gate Recommendation

- [Proceed directly to `/sp.plan`]
- [Run `/sp.clarify` first to close requirement-level critical gaps]
- [Run `/sp.deep-research` first to prove feasibility or implementation-chain readiness]
- [Force proceed only if the user accepts the known risks]

## Release Decision

**Decision**: [Aligned: ready for plan | Force proceed with known risks]

**Reason**:
[Why the requirement package is considered planning-ready, or why the workflow
is continuing with known unresolved risk.]
