# Feature Context: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`  
**Created**: [DATE]  
**Status**: Ready for planning  
**Derived From**: `spec.md`, `alignment.md`, retained references, and clarification outcomes

## Phase / Feature Boundary

[Clear statement of what this feature or bounded release slice delivers.]

## Locked Decisions

> **Source of truth**: `spec.md#decision-capture`. Planners, task generators, and implementers must preserve every locked decision recorded there. This section may summarize the decisions most relevant to downstream implementation, but must not contradict or silently drop any.

- [Implementation-critical decision carried forward from spec.md — reference the exact spec.md decision, do not rephrase]

## Capability Checkpoints

> **Source of truth**: `alignment.md#capability-checkpoints`. This section carries forward only the checkpoints that materially affect implementation sequencing or validation.

- [Capability whose checkpoint changes downstream implementation order or verification scope]

## Decision Fork Outcomes

> **Source of truth**: `alignment.md#high-impact-decision-forks`. Record only the planning-significant consequences that implementers must preserve — the options considered and rationale live in alignment.md.

- [Chosen direction and its downstream planning impact]

## Claude Discretion

- [Area where the user explicitly allowed implementation choice]
- [If none, remove this section rather than writing "None"]

## Canonical References

- [Spec, ADR, policy, or repository document that downstream work must read]
- [Reference example or contract that constrains implementation]

## Existing Code Insights

- [Reusable component, module, or pattern relevant to this feature]
- [Integration point or repository convention that should shape planning]

## Change Propagation Matrix

| Change Surface | Direct Consumers | Indirect Consumers | Risk |
| --- | --- | --- | --- |
| [surface] | [consumer] | [indirect consumer] | [risk summary] |

## Boundary Contracts and Lifecycle Notes

- [Trigger/event source, boundary contract, or identifier/payload rule planners must preserve]
- [State lifecycle, retention, archival, cleanup, failure, retry, or stale-state behavior that downstream work must not rediscover]

## Configuration Surface

- [Relevant user, admin, template, or runtime setting that changes behavior]
- [When configuration takes effect, plus rollout, migration, backfill, or cleanup implications]

## Specific User Signals

- [Concrete preference, wording, example, or product reference from the user]
- [Edge-case expectation, workflow nuance, or acceptance cue]

## Observer-Carried Risks

- [Risk surfaced by the observer that downstream planning must preserve]

## Outstanding Questions

- [Planning-critical ambiguity still unresolved]
- [If empty for normal completion, remove this section rather than writing "None"]

## Deferred / Future Ideas

- [Idea intentionally captured for later instead of this feature scope]
- [If none, remove this section rather than writing "None"]
