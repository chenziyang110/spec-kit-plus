{{spec-kit-include: ../common/user-input.md}}

## Objective

Create or update the project constitution as the authoritative rule layer for downstream specification, planning, and execution work.

## Context

- Primary inputs: the current constitution, the user's requested principle changes, the stable shared memory layer (`project-rules.md`, `learnings/INDEX.md`, and relevant learning detail docs), and any repository context needed to derive missing values.
- The constitution must stay synchronized with dependent templates and guidance files.
- Constitution amendments may invalidate downstream planning artifacts, active workflow state, or lower-order project memory and must be treated as a workflow re-entry event when that happens.
- Versioning and governance metadata are part of the contract, not optional decoration.

## Process

- Run `{{specify-subcmd:learning start --command constitution --format json}}` when available so passive learning files exist and relevant shared memory is visible before broader context collection.
- Load the current constitution, then read `.specify/memory/project-rules.md` and `.specify/memory/learnings/INDEX.md` in that order before broader repository context. Open only relevant learning detail docs linked from the index.
- If the repository already has code and you need repo-derived evidence, read `.specify/project-cognition/status.json` plus the smallest relevant query-backed cognition artifact first to assess map freshness as advisory navigation before trusting any compatibility/export artifact. If the cognition baseline is stale or too weak for an ordinary existing-baseline touched area, continue from live repository evidence and recommend `/sp-map-update` as follow-up map maintenance. Use `/sp-map-scan -> /sp-map-build` only for missing or unusable baseline, schema failure, zero active-generation `path_index` rows, `explicit_rebuild_requested`, or `baseline_identity_invalid`.
- Load the current constitution and identify unresolved placeholders or requested changes.
- Derive the right version bump and updated governance metadata.
- Rewrite the constitution and propagate any downstream template, docs, compatibility/export output, project cognition runtime, or lower-memory updates required by the amendment.
- If a principle change invalidates active `spec.md`, `plan.md`, `tasks.md`, or `workflow-state.md`, reopen the highest affected downstream stage instead of always handing off directly to `/sp-specify`.

## Output Contract

- Write a finalized constitution with a sync-impact report.
- Keep dependent templates, guidance, and lower-order project memory aligned with the updated principles.
- Surface the exact downstream re-entry path (`/sp-specify`, `/sp-plan`, `/sp-tasks`, or `/sp-analyze`) when an amendment invalidates active work.
- Surface any follow-up items if a value must remain intentionally deferred.

## Guardrails

- Do not leave unexplained placeholders behind.
- Respect the semantic-versioning rules for constitution changes.
- Do not update downstream guidance partially; either sync it or report it as pending.
- Do not always hand off directly to `/sp-specify`; use the highest affected downstream stage when the amendment is midstream.
- Do not leave project rules or learnings that conflict with the amended constitution without updating them or flagging them in the sync-impact report.
