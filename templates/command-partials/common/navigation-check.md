> **Compatibility shim:** `context-loading-gradient.md` defines the authoritative
> brownfield project cognition gate. Templates that still include this file must
> follow that shared cognition-runtime contract instead of treating this file as
> an independent navigation checklist.

- Load and enforce `context-loading-gradient.md`.
- Treat the `specify project-cognition query` task-local bundle, readiness, and
  returned `minimal_live_reads` as the primary runtime read surfaces.
- If the project cognition runtime is missing, create the initial baseline via
  `{{invoke:map-scan}}`, then `{{invoke:map-build}}`.
- If the project cognition runtime is stale or insufficient for the touched
  query scope, prefer `{{invoke:map-update}}`; rebuild only when no usable
  baseline remains.
