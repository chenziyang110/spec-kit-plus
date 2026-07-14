---
name: spx-map-scan
description: Low-cost project-cognition scan workflow for advanced coding models. Use when a new or explicitly rebuilt baseline needs canonical repository evidence before deterministic graph construction.
---

# SPX Map Scan

Read `references/project-cognition.md` for its evidence boundary, then
`references/scan-gates.md` and `references/scan-worker.md`. Do not run Compass
intake while the baseline is missing or invalid. This skill writes only
cognition scan/workbench artifacts; product source remains read-only.

Confirm scan/rebuild need with
`{{specify-subcmd:project-cognition status --format json}}`. Then:

1. Run `{{specify-subcmd:project-cognition generate-ignore --format json}}`.
   If it creates an ignore file, obtain user review before scanning.
2. Create the canonical boundary with
   `{{specify-subcmd:project-cognition scan-set --out .specify/project-cognition/tmp/scan-files.json --format json}}`.
   Never substitute raw repository globs.
3. Run
   `{{specify-subcmd:project-cognition scan-prepare --scan-set .specify/project-cognition/tmp/scan-files.json --format json}}`.
   Resume a compatible queue. Use `--force` only after explicitly abandoning
   the old workbench, because accepted and pending results are discarded.
4. Keep the advanced model as leader and dispatch every prepared packet with
   `references/scan-worker.md` to the lowest-cost capable worker/model. The
   leader owns boundaries, acceptance, coverage, and escalation—not bulk reads.
5. Accept each returned packet with
   `{{specify-subcmd:project-cognition scan-accept --packet-id <packet-id> --format json}}`.
   Repair or escalate rejected packets locally.
6. Run `{{specify-subcmd:project-cognition validate-scan --format json}}` and
   repair every blocking coverage/evidence gap.

Stop when validation reports the scan package ready. Do not run
`build-from-scan`, publish a database, or claim the cognition baseline is
queryable. Hand off to `$spx-map-build`.
