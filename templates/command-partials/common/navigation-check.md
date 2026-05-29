> **Compatibility shim:** `context-loading-gradient.md` defines the authoritative
> brownfield project cognition advisory layer. Templates that still include this file must
> follow that shared cognition-runtime contract instead of treating this file as
> an independent navigation checklist.

- Load and consult `context-loading-gradient.md`.
- Treat the task-local project cognition query bundle, readiness, and returned
  `minimal_live_reads` as the primary runtime read surfaces.
- Preserve the concept selection, rejected concepts, `selection_reason`, and
  returned `route_pack` when handing off to the next workflow artifact.
- If `baseline_kind=greenfield_empty`, continue with workflow artifacts and live
  requirements. Do not recommend map-scan -> map-build solely because the graph
  has no paths.
- If the project cognition runtime is missing for a brownfield project, recommend the initial baseline via
  `{{invoke:map-scan}}`, then `{{invoke:map-build}}`.
- If the project cognition runtime is stale or insufficient for the touched
  query scope, recommend `{{invoke:map-update}}`; rebuild only when no usable
  brownfield baseline remains, schema failure, zero active-generation `path_index`
  rows outside `greenfield_empty`, `explicit_rebuild_requested`, or
  `baseline_identity_invalid`.
- This navigation check is entry-only. Entry-time stale or weak cognition is advisory unless the user requested map maintenance. Workflow-owned mutation closeout is separate: if the current workflow changes project-related files or behavior, run inline project cognition update before successful completion. `sp-map-update` is for manual/external maintenance and follow-up repair; it is external map maintenance, not routine closeout for this workflow's own changes. In shared routing summaries, sp-map-update is for manual/external maintenance.
