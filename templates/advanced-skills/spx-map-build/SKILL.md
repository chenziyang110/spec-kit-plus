---
name: spx-map-build
description: Deterministic project-cognition build workflow for advanced coding models. Use when spx-map-scan has produced a validated scan package that must become the queryable SQLite cognition baseline.
---

# SPX Map Build

Read `references/project-cognition.md` for its evidence boundary and
`references/build-gates.md`. Do not run Compass intake until after a valid build
is published. This skill consumes the accepted scan package and does not read
or modify product source.

Require `{{specify-subcmd:project-cognition validate-scan --format json}}` to
report a build-ready scan. If it is incomplete, stop and route the exact gaps to
`$spx-map-scan`.

Run `{{specify-subcmd:project-cognition build-from-scan --format json}}`, then
`{{specify-subcmd:project-cognition validate-build --format json}}`. These are
the only construction and publication steps. Do not ask a model to reconstruct
the graph, reread the repository, hand-edit SQLite, or finalize with incremental
`complete-refresh`.

Prove the published baseline with
`{{specify-subcmd:project-cognition compass --intent implement --query "<representative project query>" --format json}}`
and targeted expansion when validation calls for it. Treat publication blocks,
schema/index failures, unresolved paths, and claim-lifecycle errors as hard
failures.

Report the scan identity consumed, database/build readiness, representative
query result, validation, and any remaining coverage limitation. Return to the
workflow that requested the baseline only after the runtime is query-ready.
