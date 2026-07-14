# Design and task contract

Plan from the specification contract and current repository. Preserve confirmed
scope; phases order delivery and do not silently defer it.

Record only decisions that constrain implementation:

- affected owners, consumers, files, and generated/mirrored surfaces;
- interfaces, data/state transitions, error and recovery behavior;
- compatibility, migration, security, rollout, and rollback when triggered;
- verification at the real entry point and important boundaries;
- alternatives or risks that materially change the chosen design.

Tasks express outcomes, not a transcript of coding steps. Each task needs a
clear result, dependencies, likely write scope, acceptance evidence, and
verification. Mark parallel only when inputs are stable and write sets do not
overlap. Add `task-index.json` for delegated, multi-batch, obligation-heavy, or
runtime-validated execution; a short linear task set may remain in `tasks.md`.

Trace requirements, must-preserve behavior, and consequence obligations into
design and tasks. Repair upstream contradictions rather than adding a task to
"figure it out later". Use the templates in `assets/` for new artifacts; retain
existing semantic work when updating an established feature.
