# Research: Pitfalls for v1.3 Implement Orchestrator Runtime

## High-Risk Failure Modes

- Leaving `single-lane` ambiguous so the leader still acts as the executor for serial tasks.
- Dispatching workers without explicit write-set or shared-surface conflict rules, which breaks artifact consistency.
- Advancing phases based on optimistic task completion instead of verified convergence.
- Letting cross-phase preparation mutate later-phase state before prerequisite work is complete.

## Integration Pitfalls

- Updating Codex-specific guidance without first updating the shared template, creating cross-surface drift.
- Adding new scheduler state outside the existing orchestration/state machinery, which fragments the runtime story.
- Treating worker failure as a generic boolean without classifying critical-path impact, retry count, or deferral status.

## Prevention Strategy

- Make leader-only execution a first-class requirement and reflect it in tests.
- Keep phase advancement gated by explicit success criteria and artifact updates.
- Represent worker outcomes and blockers in persisted planning state.
- Validate template, generated skill, and orchestration tests together before calling the runtime shipped.

## Phase Targets

- Contract and scheduler semantics should land first.
- Failure handling and batch coordination should land next.
- Surface alignment, state persistence, and end-to-end verification should land last.
