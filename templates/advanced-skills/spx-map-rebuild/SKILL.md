---
name: spx-map-rebuild
description: Lean project-cognition rebuild workflow for advanced coding models. Use only when cognition reports a missing, unusable, schema-invalid, explicitly invalidated, or rebuild-required baseline.
---

# SPX Map Rebuild

Read `references/project-cognition.md`. This skill repairs the navigation data
plane; it does not change product behavior.
Read `references/rebuild-gates.md` before scanning.

Confirm rebuild necessity with
`{{specify-subcmd:project-cognition status --format json}}`. Do not rebuild for
an ordinary local gap that incremental update can repair.

1. Run `{{specify-subcmd:project-cognition generate-ignore --format json}}`; if
   it creates an ignore file, obtain user review before scanning.
2. Resolve the canonical boundary with
   `{{specify-subcmd:project-cognition scan-set --out .specify/project-cognition/tmp/scan-files.json --format json}}`.
   Do not replace this boundary with raw repository globs.
3. Run
   `{{specify-subcmd:project-cognition scan-prepare --scan-set .specify/project-cognition/tmp/scan-files.json --format json}}`.
   Treat its packet files and IDs as the only scan work queue.
   If an existing workbench blocks preparation, resume its pending queue when
   compatible. Use `--force` only after explicitly abandoning that workbench;
   it discards its accepted and pending scan results.
4. Keep the advanced model as leader. Dispatch each prepared packet with
   `references/scan-worker.md` to the
   lowest-cost capable subagent/model available. The leader owns boundaries,
   acceptance, and escalation—not bulk file reading. If the runtime cannot
   select a worker tier, use its configured scan worker or native subagent and
   report the cost-route degradation; never pretend a cheaper model was used.
   Escalate only a packet with a critical semantic conflict, uncovered critical
   path, or repeated validation failure.
5. For each returned packet, run
   `{{specify-subcmd:project-cognition scan-accept --packet-id <packet-id> --format json}}`.
   Rejected results remain packet-local; repair or escalate only that packet.
6. Run `{{specify-subcmd:project-cognition validate-scan --format json}}`.
   Repair gaps instead of publishing incomplete evidence.
7. Run `{{specify-subcmd:project-cognition build-from-scan --format json}}`,
   then `{{specify-subcmd:project-cognition validate-build --format json}}`.
   This is the deterministic build stage: do not ask any model to reconstruct
   the graph or reread the repository. Publication blocks are hard failures;
   never construct the SQLite graph manually.

Prove success with a representative project-pinned `project-cognition compass`
query. Report coverage, exclusions, remaining gaps, and exact validation.
