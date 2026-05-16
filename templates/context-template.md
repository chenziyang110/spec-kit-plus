# Impact and Constraint Map: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`  
**Created**: [DATE]  
**Status**: Ready for planning  
**Derived From**: `spec.md`, `alignment.md`, retained references, and discovery evidence

## Brainstorming-Derived Execution Context

- **Truth Owner**: [repo | prd | mixed]
- **Primary Route**: [compiled route]
- **Complexity Level**: [T1 | T2 | T3 | T4]
- **Compatibility Constraints**:
  - [constraint]
- **Must-Preserve Invariants**:
  - [invariant]
- **Allowed Internal Redesign**:
  - [yes/no and notes]
- **Allowed Optimization Scope**:
  - [scope planners and implementers may improve without reopening intent]
- **Stop-And-Reopen Conditions**:
  - [condition that requires upstream truth to reopen]


## Must-Preserve Execution Constraints

- `MP-###`: [implementation-shaping decision, reference, non-goal, or trade-off]
- Stop-and-reopen conditions:
  - [condition tied to MP ID]

## Affected Surfaces

- [Primary module, workflow, interface, or artifact this feature changes]
- [Secondary surface that must change to preserve usability or correctness]

## Brainstorming-Derived Execution Context

- **Truth Owner**: [Which locked brainstorming truth artifacts own the route, intent, and complexity decisions]
- **Compatibility Constraints**: [Compatibility obligations carried forward from the locked requirement package]
- **Allowed Internal Redesign**: [Where execution may improve internal quality without violating preserved outcomes]

## Upstream Dependencies

- [Trigger, input, external contract, repository subsystem, or prerequisite]
- [Existing workflow, data producer, or policy that shapes this feature]

## Downstream Dependencies and Consumers

- [Direct consumer, adjacent workflow, or later stage that depends on this behavior]
- [Indirect consumer, reporting surface, operator flow, or integration seam]

## Product Boundary Constraints

- [Current product or release boundary that limits what this feature should deliver]
- [Policy, compatibility, architecture, or ownership boundary planners must preserve]

## Domain-Expected Completeness Checks

- [Normal domain expectation that must be satisfied for the feature to feel complete]
- [Permission, lifecycle, state, supportability, or failure-path expectation]
- [Acceptance or validation expectation that planners must carry forward]

## Critical Adjacent Effects

- [Adjacent behavior that would break or feel incomplete if omitted]
- [Downstream, migration, notification, observability, or support consequence]

## Existing Capability and Reuse Notes

- [Existing component, workflow, or pattern that changes what "complete" means here]
- [Reusable implementation surface, precedent, or constraint already present in the repo]

## Brainstorming-Derived Execution Context

- **Truth Owner**: [repo | PRD | mixed]
- **Compatibility Constraints**:
  - [Constraint compiled from brainstorming truth]
- **Allowed Internal Redesign**:
  - [yes/no plus boundary note]

## Change Propagation Matrix

| Change Surface | Upstream Inputs | Downstream Consumers | Constraint / Risk |
| --- | --- | --- | --- |
| [surface] | [input] | [consumer] | [constraint or propagation risk] |

## Locked Decisions Carry-Forward

- [Decision from `spec.md#decision-capture` that planners and implementers must preserve]
- [Boundary or dependency rule that must survive into implementation planning]

## Canonical References

- [Spec, ADR, policy, project cognition entry, or repository doc downstream work must read]
- [Reference example or external contract that constrains delivery]

## Outstanding Questions

- [Planning-critical ambiguity still unresolved]
- [If empty for normal completion, remove this section rather than writing "None"]

## Deferred / Future Ideas

- [Idea intentionally captured for later instead of this delivery slice]
- [If none, remove this section rather than writing "None"]
