# Planning contract

Plan from the specification contract and current repository. Preserve confirmed
scope; delivery phases do not silently defer requirements.

Record only decisions that constrain implementation:

- affected owners, consumers, files, and generated or mirrored surfaces;
- interfaces, data/state transitions, error and recovery behavior;
- compatibility, migration, security, rollout, and rollback when triggered;
- verification at real entry points and important boundaries;
- alternatives, assumptions, and risks that materially affect the design.

When UI applies, preserve the feature `ui-brief.md` rather than reinterpreting
it. Explicitly set `ui_applicable: true`, preserve `ui_brief_ref`, and record
`design_readiness: approved` or a bounded `narrow-existing-pattern-exception`.
Map its work/surface/platform types, subject/audience/job, three theses,
signature, approved visual ref, reference intents, real content/image plans,
entry points, approved design tokens/components, required states,
responsive/accessibility rules, fidelity constraints, and
must-preserve/may-adapt/must-not decisions into
`plan-contract.json#/ui_design_contract`. The verification plan names the
representative viewport/state matrix, screenshot or platform capture routes,
the structure/visual/runtime evidence triad, visual comparison, and accepted
deviation or pending-human-review boundary. Carry verified cognition routes for
entry points, owners, reusable patterns, and visual tests in the context capsule.

Trace every requirement and must-preserve obligation to a design decision or an
explicit unresolved blocker. Use precise paths when reasonably knowable, but do
not turn the plan into task-level edit instructions. A planning-ready result has
no hidden feasibility question capable of changing the chosen architecture.
