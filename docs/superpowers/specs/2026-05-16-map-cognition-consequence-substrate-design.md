# Map Cognition Consequence Substrate Design

## Summary

Add the project cognition supply layer required by the Senior Consequence Analysis Gate. The first phase made workflows consume consequence facts. This phase makes `sp-map-scan`, `sp-map-build`, and `sp-map-update` produce and maintain the facts those workflows need to reason like a senior maintainer.

The model is baseline-once, update-by-default:

```text
sp-map-scan -> sp-map-build   # initial or rare rebuild only
sp-map-update                 # normal maintenance after changes
```

`sp-map-scan` and `sp-map-build` establish the initial query-backed baseline. After that, ordinary code, template, test, and documentation changes use `sp-map-update`. Direct-work workflows such as `sp-fast`, `sp-quick`, `sp-debug`, and `sp-implement` must close by naming what code or behavior they changed and recommending `sp-map-update` with those changed paths so project cognition does not drift.

## Goals

- Make the project cognition runtime provide the evidence substrate for consequence analysis: ownership, consumers, lifecycle states, running actors, shared state, dependencies, recovery paths, verification routes, confidence, and known unknowns.
- Treat `sp-map-update` as the default reliable maintenance path after the first baseline, not as a best-effort fallback.
- Make direct implementation workflows report changed code and behavior surfaces in a shape that `sp-map-update` can consume.
- Ensure `map-update` starts from Git changes, queries current project cognition, expands the affected closure, and updates affected runtime records.
- Preserve uncertainty explicitly through low-confidence claims, conflicts, known unknowns, and `minimal_live_reads` instead of claiming that an update is impossible.
- Reserve `sp-map-scan -> sp-map-build` for no baseline, unusable baseline, schema/DB incompatibility, corruption, or explicitly requested rebuilds.

## Non-Goals

- Do not make project cognition decide product semantics. It supplies evidence; downstream workflows still choose or ask for behavior.
- Do not require full rebuilds for ordinary code changes.
- Do not make `.specify/project-map/**` a new runtime truth source.
- Do not require generated workflows to inspect the full repository after every small edit.
- Do not remove live reads. `map-update` should reduce them and name the minimum necessary reads when confidence is low.

## Current Context

The existing design already says project cognition gives ownership, consumers, state surfaces, change-propagation facts, verification routes, conflicts, known unknowns, and `minimal_live_reads`. The first phase also documents that `sp-map-build` and the query runtime are necessary but not sufficient for product semantics.

The remaining gap is the maintenance loop. If `map-update` is framed as something that may frequently fail or route back to full rebuild, teams will stop trusting the cognition runtime. The intended operating model is different:

- Initial brownfield onboarding builds the runtime once.
- Each implementation workflow reports what it changed.
- `map-update` uses Git plus existing cognition to update the affected slice.
- If exact closure cannot be proven, the update still records partial truth, confidence, conflicts, and live-read requirements.
- Only structural runtime failures or missing baseline force a rebuild.

## Consequence Substrate Fields

Project cognition must be able to answer the questions that consequence analysis asks. It does not need to precompute every answer, but scan/build/update outputs must preserve enough evidence for query planning.

At minimum, the runtime must maintain or derive:

- **Ownership and truth owners**: source files, state files, commands, APIs, templates, generated surfaces, and runtime records that own behavior.
- **Consumers**: direct callers, downstream workflows, generated artifacts, tests, docs, CLIs, APIs, hooks, worker packets, result validators, and user-visible surfaces.
- **Lifecycle and state surfaces**: statuses, state machines, queues, locks, leases, heartbeats, sessions, active workers, pending jobs, and durable workflow state.
- **Concurrent or running actors**: workers, batches, async jobs, active sessions, in-flight results, background refreshes, external processes, and retry loops.
- **Shared mutable state**: databases, JSON state files, indexes, caches, registries, queues, counters, and coordination files.
- **Destructive or irreversible operations**: delete, close, reset, cleanup, force, revoke, archive, migration, and de-scope paths.
- **Dependency propagation routes**: upstream callers, downstream consumers, generated-surface propagation, compatibility surfaces, and adjacent workflows.
- **Recovery and validation routes**: rollback, retry, cleanup, idempotency, observability, tests, manual checks, smoke queries, and CI commands.
- **Confidence and gaps**: evidence IDs, confidence levels, conflicts, known unknowns, stale facts, and `minimal_live_reads`.

These facts should be queryable by natural task intent after the agent creates a `query_plan` from the runtime lexicon.

## `sp-map-scan` Responsibilities

`sp-map-scan` remains evidence-only. It must not publish final cognition truth.

It must collect consequence substrate evidence during the initial baseline scan:

- classify surfaces by owner, consumer, state, dependency, verification, risk, and generated-surface propagation role
- identify lifecycle/state vocabulary such as `status`, `state`, `phase`, `running`, `queued`, `closed`, `failed`, `cancelled`, `resumed`, and domain-specific equivalents
- record running/concurrent actor evidence when code references workers, tasks, sessions, batches, queues, locks, leases, heartbeats, async jobs, or external processes
- record destructive-operation evidence when code or docs mention delete, close, cleanup, reset, force, revoke, archive, migration, or irreversible mutation
- capture verification entrypoints near each critical or important surface
- mark unknown or low-confidence classification as a scan gap, not as `low-risk`

The scan output should let `sp-map-build` reconstruct graph claims without rediscovering repository scope.

## `sp-map-build` Responsibilities

`sp-map-build` publishes query-backed cognition truth from accepted scan evidence.

It must synthesize consequence substrate claims and edges:

- owner edges from behavior surfaces to truth owners
- consumer edges from behavior surfaces to downstream callers, generated artifacts, tests, docs, and workflows
- state edges from lifecycle surfaces to state vocabulary and transition evidence
- running-actor edges from workflows or runtime surfaces to workers, jobs, sessions, queues, and result paths
- dependency-propagation edges from changed surfaces to affected commands, templates, schemas, packets, validators, and docs
- verification-route edges from claims to tests, smoke queries, manual checks, or CI commands
- conflict or known-unknown records where evidence is incomplete or contradictory

Build validation should fail only when the baseline cannot become queryable or critical substrate is absent without an explicit known-unknown. It should not require product decisions that belong to `discussion`, `specify`, or `plan`.

## `sp-map-update` Responsibilities

`sp-map-update` is the normal maintenance workflow after the baseline exists.

It must:

1. Read Git changes: modified, added, deleted, renamed paths, and optionally the commit range or explicit user-supplied scope.
2. Query the current project cognition runtime for each changed path and user-supplied behavior surface.
3. Expand the affected closure through owners, consumers, state surfaces, generated-surface propagation, verification routes, and adjacent workflows.
4. Refresh evidence for the closure with bounded live reads.
5. Update or invalidate affected claims, edges, conflicts, known unknowns, and verification routes.
6. Record low-confidence or partial updates when evidence is insufficient for full confidence.
7. Update `.specify/project-cognition/status.json` with freshness, readiness, touched closure, low-confidence areas, and recommended `minimal_live_reads`.

`sp-map-update` should not say "cannot update" for ordinary uncertain closures. It should record what changed, what it could prove, what it could not prove, and which minimal live reads future workflows should perform.

### Rebuild Boundary

`sp-map-update` routes to `sp-map-scan -> sp-map-build` only when:

- no query-backed baseline exists
- the DB is missing, corrupted, or schema-incompatible
- validation proves the runtime cannot load or answer lexicon/query calls
- the user explicitly requests a full rebuild
- the repository changed so broadly that the runtime identity is no longer meaningful, such as replacing the application architecture wholesale

Unclear impact closure is not by itself a rebuild reason. It becomes a partial or low-confidence update with explicit follow-up reads.

## Completion Workflow Obligations

Direct implementation workflows must give `sp-map-update` useful input at closeout.

`sp-fast`, `sp-quick`, `sp-debug`, and `sp-implement` should report:

- changed code paths: modified, added, deleted, renamed
- changed behavior surfaces: commands, APIs, templates, state files, workflows, packets, validators, docs, tests
- affected lifecycle or state behavior
- dependency or consumer surfaces touched
- verification evidence run
- recommended `sp-map-update` command or argument shape

Example:

```text
Changed code:
- modified: src/team/close.py
- added: tests/test_team_close.py

Behavior surfaces touched:
- team lifecycle close behavior
- running worker drain path
- late result submission handling

Recommended next step:
- Run sp-map-update with the changed paths from this task so project cognition reflects the new behavior.
```

This recommendation should be normal, not alarming. It is the maintenance loop that keeps later consequence analysis accurate.

## Query Expectations

After build or update, a downstream workflow should be able to query for:

- affected owners for a requested change
- downstream consumers of a state or behavior surface
- lifecycle states and transition evidence
- running actors and in-flight result paths
- shared mutable state and coordination mechanisms
- verification routes that prove behavior or recovery
- known unknowns and `minimal_live_reads`

For example, a request like "close team" should let the agent find terms for team lifecycle, worker state, task queue, result submission, heartbeat, cleanup, status, resume, and validation routes when those concepts exist in the codebase.

## Validation Strategy

Add contract tests and validators that prove:

- `map-scan` guidance requires consequence substrate evidence collection.
- `map-build` guidance requires owner, consumer, state, dependency, verification, confidence, conflict, and known-unknown synthesis.
- `map-update` guidance treats Git diff plus runtime query as the default refresh path.
- `map-update` preserves partial/low-confidence updates instead of escalating ordinary uncertainty to rebuild.
- direct workflows report changed paths and recommend `map-update` after implementation.
- docs explain baseline-once and update-by-default.

Where structured validators exist, enforce shape. Where only prompt contracts exist, add rendering and template assertions.

## Acceptance Criteria

- `sp-map-scan` describes consequence substrate evidence as required baseline input.
- `sp-map-build` describes consequence substrate synthesis as required runtime output.
- `sp-map-update` is documented as the default post-change maintenance path after baseline.
- `sp-map-update` only routes to rebuild for missing/unusable baseline, schema/DB failure, explicit rebuild, or wholesale architecture replacement.
- `sp-fast`, `sp-quick`, `sp-debug`, and `sp-implement` closeout guidance includes changed paths, behavior surfaces, verification evidence, and recommended `sp-map-update`.
- Documentation says `sp-map-scan -> sp-map-build` establishes the baseline once, while routine changes use `sp-map-update`.
- Tests assert the generated workflows and docs preserve the baseline-once/update-by-default contract.

