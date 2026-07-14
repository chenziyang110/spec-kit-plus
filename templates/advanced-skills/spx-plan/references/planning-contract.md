# Planning contract

Plan from the specification contract and current repository. Preserve confirmed
scope; delivery phases do not silently defer requirements.

Record only decisions that constrain implementation:

- affected owners, consumers, files, and generated or mirrored surfaces;
- interfaces, data/state transitions, error and recovery behavior;
- compatibility, migration, security, rollout, and rollback when triggered;
- verification at real entry points and important boundaries;
- alternatives, assumptions, and risks that materially affect the design.

Trace every requirement and must-preserve obligation to a design decision or an
explicit unresolved blocker. Use precise paths when reasonably knowable, but do
not turn the plan into task-level edit instructions. A planning-ready result has
no hidden feasibility question capable of changing the chosen architecture.
