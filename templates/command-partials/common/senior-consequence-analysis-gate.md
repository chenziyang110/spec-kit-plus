## Senior Consequence Analysis Gate

Run this gate whenever the request, artifact set, defect, or planned change can affect lifecycle operations, running objects, concurrent work, destructive behavior, shared state, downstream consumers, compatibility, security-sensitive behavior, or multiple plausible product behaviors.

Project cognition first. Use the project cognition runtime to identify ownership, consumers, state surfaces, change-propagation facts, verification routes, conflicts, known unknowns, and coverage gaps. Senior consequence analysis second. Turn those facts into explicit product and implementation obligations instead of treating the graph as the decision-maker.

Project cognition readiness provides routing advice. If readiness is `ready`, continue with the returned task-local bundle. If readiness is `review`, inspect the returned `minimal_live_reads` before continuing. If readiness is `ambiguous`, ask the user to choose. If readiness is `needs_update`, continue with live repository evidence and recommend `{{invoke:map-update}}` as follow-up map maintenance. If readiness is `needs_rebuild`, continue with live repository evidence and recommend `{{invoke:map-scan}} -> {{invoke:map-build}}` only for missing or unusable baseline, schema failure, zero active-generation `path_index` rows, `explicit_rebuild_requested`, or `baseline_identity_invalid`. If readiness is `blocked`, report the blocked state and continue with live repository evidence unless the user's actual request is to fix cognition runtime state. Carry relevant project cognition facts, returned `minimal_live_reads`, inference notes, and coverage gaps into the workflow's artifacts or durable state, but back consequence claims with live code, tests, scripts, configuration, or authoritative docs.

Required output when the gate triggers:

- **Affected Object Map**: name each object, record, worker, queue, artifact, command, API, file surface, user-visible state, or downstream consumer that can be affected.
- **State-Behavior Matrix**: describe behavior for each important lifecycle state, including created, queued, running, paused, failed, cancelled, completed, resumed, archived, missing, stale, or partially refreshed states when relevant.
- **Dependency Impact Table**: map direct dependencies, indirect consumers, shared state, compatibility surfaces, validation routes, and adjacent workflows that can break if semantics change.
- **Recovery And Validation Contract**: state rollback, retry, idempotency, cleanup, migration, observability, and validation evidence required before handoff or completion.
- **Coverage Gaps**: list what project cognition or live evidence cannot prove, who must resolve each gap, the latest safe resolve phase, the stop-and-reopen condition, and the routing decision: current workflow may continue with an assumption, must ask the user, must route to clarification or deep research, or must request map maintenance.
- **Consequence Obligations**: assign stable `CA-###` IDs to every obligation that must survive downstream handoff, task generation, worker packets, verification, or debug closeout. Each `CA-###` must include claim, affected objects, owner workflow, latest resolve phase, status, and stop-and-reopen condition.

Stand down only for docs-only wording changes, trivial isolated fixes, or local refactors that cannot affect lifecycle operations, running state, destructive operations, shared state, downstream consumers, compatibility, security, or multiple behavior choices. Record the no-trigger reason or stand-down reason in the workflow's durable artifact or closeout before skipping the required outputs.

If the gate triggers and the current workflow cannot preserve the required outputs, stop and route to the workflow that can. Do not mark ready, resolved, handoff-ready, planning-ready, or complete while triggered consequence obligations remain unresolved, unmapped, or unsupported by validation evidence.
