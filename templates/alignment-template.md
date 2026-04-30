# Requirement Alignment Report: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`  
**Created**: [DATE]  
**Status**: [Aligned: ready for plan | Force proceed with known risks]

## Task Classification

**Detected Type**: [greenfield project | existing feature addition | bug fix | technical refactor | docs/config/process change]

**User Correction**: [None | corrected to X]

## Current Understanding

[Summarize what is being built or changed, who it is for, where it fits, and what success looks like.]

### Planning Summary

- **Goal / outcome**: [What must be delivered]
- **Users / roles**: [Who the feature serves]
- **In scope**: [What is explicitly included in this release]
- **Out of scope**: [What is explicitly deferred or excluded]
- **Success signal**: [How planners and testers will recognize success]

## Analysis Confidence

### Confirmed Facts

- [Fact confirmed directly by the user, repository evidence, or retained references]
- [Capability boundary, rule, or requirement that is fixed enough for planning]

### Low-Risk Inferences

- [Reasonable default adopted from context]
- [Assumption that helps planning without materially changing scope]

### Unresolved Items

- [Open item, missing decision, or unclear dependency]
- [Question that still affects confidence, scope, or planning]

## Locked Decisions For Planning

> **Source of truth**: `spec.md#decision-capture`. This section records the process that produced those decisions, not a duplicate copy.

- [How each locked decision in spec.md was reached: user confirmation, repository evidence, or explicit force-carry]
- [Link to the clarifying Q&A that resolved each decision, if any]

## Engineering Closure For Planning

- **Trigger / event source**: [What signal, actor, or upstream action starts the behavior]
- **Contract / boundary notes**: [Which identifiers, payload, or acknowledgement semantics must stay intact across module/service/process boundaries]
- **State lifecycle / retention**: [What states exist, how they transition, and when they are archived, cleaned up, or removed]
- **Failure / retry semantics**: [How failures surface, whether retries/replays happen, and what remains user-visible when the happy path breaks]
- **Configuration / effective scope**: [Which settings shape this behavior and when changes take effect]

## Capability and Planning Impact

- **Capability Shape**: [How the feature decomposes into planning-relevant capabilities]
- **Dependencies / Preconditions**: [What planners must account for first]
- **Downstream Planning Impact**: [How unresolved items, assumptions, or sequencing constraints affect `/sp.plan`]

## Capability Checkpoints

- **[Capability Name]**: Purpose / outcome -> [What this capability must achieve]
- **Boundary and non-goals**: [What stays inside this capability versus adjacent capabilities]
- **Acceptance proof**: [What evidence would show this capability is implemented correctly]

## Feasibility / Deep Research Gate

- **Gate status**: [Not needed | Needed before plan | Completed | Blocked]
- **Reason**: [Why feasibility research is or is not required before planning]
- **Capabilities requiring proof**:
  - [Capability] -> [unknown implementation-chain link] -> [proof target or spike needed]
- **Prototype / demo expectation**: [None | disposable `research-spikes/` demo needed | completed evidence path]
- **Implementation-chain confidence**: [Existing proven path | Proven by research | Constrained but plannable | Blocked]
- **Planning Handoff readiness**: [Not needed | Needed from `/sp.deep-research` | Complete | Incomplete]

## High-Impact Decision Forks

- **[Decision Fork]**: [Requirement-shaping choice that changed behavior, boundary, compatibility, or acceptance proof]
- **Options considered**: [2-3 concrete options that were on the table]
- **Chosen direction**: [Which option was selected and why planners must preserve it]

## Confirmed Decisions

> These are the decisions that reached closure during alignment. The authoritative, planner-ready form of each decision lives in `spec.md#decision-capture`.

- [Final decision or explicit commitment — reference the corresponding entry in spec.md]
- [Decision that resolved a prior ambiguity and changed downstream planning shape]

## Clarification Summary

- Q: [...]
  A: [...]
- Q: [...]
  A: [...]

## Outstanding Questions

- [Planning-critical question that is still unresolved]
- [If empty for normal completion, remove this section rather than writing "None"]

## Remaining Risks

- [None]
- or
- [Unresolved item] -> [Why it matters] -> [Possible downstream impact]

## Planning Gate Recommendation

- [Proceed directly to `/sp.plan`]
- [Run `/sp.clarify` first to close planning-critical gaps]
- [Run `/sp.deep-research` first to prove feasibility or produce a disposable demo]
- [Force proceed only if the user accepts the known risks]

## Artifact Review Gate

- **Self-review**: [passed | revised]
- **Reviewer lane**: [not used | approved | issues found then revised]
- **User artifact review**: [approved | changes requested | continue analysis with `/sp.clarify` | prove feasibility with `/sp.deep-research`]

## Release Decision

**Decision**: [Aligned: ready for plan | Force proceed with known risks]

**Reason**:
[Why the requirement is considered planning-ready, or why it is being force-continued despite unresolved risks.]
