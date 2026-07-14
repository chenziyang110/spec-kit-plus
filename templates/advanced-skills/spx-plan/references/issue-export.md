# Issue export

Use this only when the user explicitly asks to publish ready tasks to an issue
tracker. External issue creation is a separate authorized side effect, not an
automatic planning closeout step.

Export only validated tasks with stable IDs, outcomes, dependencies,
acceptance, verification, and useful source links. Preserve dependency order
and avoid duplicate issues by checking existing task IDs or recorded issue
links. Do not expose secrets, private evidence, or unnecessary internal notes.

Use an installed deterministic exporter or tracker connector when available.
Record created or matched issue identifiers back into the task index without
changing task meaning. On partial failure, report exactly what was created and
what remains safe to retry.
