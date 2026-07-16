{{spec-kit-include: ../common/user-input.md}}

## Objective

Create or update the project constitution as the authoritative rule layer for downstream specification, planning, and execution work.

## Context

- Primary inputs: the current constitution, the user's requested principle changes, the consume-only Learning CLI intake, and the smallest repository context needed to derive missing values.
- Constitution amendments may invalidate downstream planning artifacts, active workflow state, dependent templates, guidance files, or lower-order project memory. Treat those as re-entry or follow-up signals to report, not as permission to edit additional files.
- Versioning and governance metadata are part of the contract, not optional decoration.

## Process

- Run `{{specify-subcmd:learning start --command constitution --format json}}`; expand only selected matching Learning with its `show_argv`.
- Load the current constitution before broader repository context. Do not parse project Learning storage files directly.
- If the repository already has code and you need repo-derived evidence, read `.specify/project-cognition/status.json` plus the smallest relevant query-backed cognition artifact first to assess map freshness as advisory navigation before trusting any compatibility/export artifact. If the cognition baseline is stale or too weak for an ordinary existing-baseline touched area, continue from live repository evidence and recommend `/sp-map-update` only as external/manual map maintenance when the user asks for map maintenance or before a separate map-maintenance pass. Use `/sp-map-scan -> /sp-map-build` only for first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation `path_index` rows, missing or invalid `alias_index`, `explicit_rebuild_requested`, or `baseline_identity_invalid`.
- Load the current constitution and identify unresolved placeholders or requested changes.
- Derive the right version bump and updated governance metadata.
- Rewrite only `.specify/memory/constitution.md`.
- Report any downstream template, docs, compatibility/export output, project cognition runtime, workflow-state, or lower-memory updates required by the amendment as pending follow-up in the Sync Impact Report.
- If a principle change invalidates active `spec.md`, `plan.md`, `tasks.md`, or `workflow-state.md`, report the highest affected downstream stage instead of always handing off directly to `/sp-specify`.

## Output Contract

- Write a finalized constitution with a sync-impact report.
- Record dependent templates, guidance, and lower-order project memory that need alignment as pending follow-up items.
- Surface the exact downstream re-entry path (`/sp-specify`, `/sp-plan`, `/sp-tasks`, or `/sp-analyze`) when an amendment invalidates active work.
- Surface any follow-up items if a value must remain intentionally deferred.

## Guardrails

- Do not leave unexplained placeholders behind.
- Respect the semantic-versioning rules for constitution changes.
- Do not update downstream guidance from this workflow unless the user explicitly expands the write scope in the same request; report pending alignment instead.
- Do not always hand off directly to `/sp-specify`; use the highest affected downstream stage when the amendment is midstream.
- Do not leave project rules or learnings that conflict with the amended constitution unreported in the sync-impact report.
