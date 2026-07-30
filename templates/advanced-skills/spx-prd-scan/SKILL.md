---
name: spx-prd-scan
description: Reconstruction-grade repository scan for advanced coding models. Use when an existing product needs a read-only evidence package before a PRD suite can be compiled.
---

# SPX PRD Scan

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/project-cognition.md`, using cognition intent `research`, and
`references/prd-scan-contract.md`.

Initialize or resume the run with
`{{specify-subcmd:specify-runtime prd-scan <run-slug> --json}}`; inspect existing status before
creating a new workspace. Project source, tests, configuration, and docs are
read-only. The `.specify/prd-runs/<run-id>/` evidence workspace is CLI-owned and
must remain resumable; never write its files directly.

Query the installed `workflow-state.md` through `specify-runtime artifact show` and update it only through its registered artifact owner instead of reconstructing the
run from chat. Persist `active_command: sp-prd-scan`, the current scan stage,
`scan_status`, `build_status`, `classification`, current packet,
`accepted_packet_results`, `rejected_packet_results`,
`failed_readiness_checks`, open gaps, next action, next command, and handoff
reason. Resume a non-terminal run from those fields without replacing accepted
evidence.

Use the stable PRD freshness result to bound reads: `fresh` confirms status
unless a new run was explicitly requested; `targeted-stale` scans the changed
surfaces and adjacent capability boundaries; `full-stale` rebuilds the complete
reconstruction evidence package. Classify the product independently as
`ui | service | mixed` and persist that value in workflow state and scan
evidence so build cannot erase either UI or service behavior.

Use cognition to define capabilities, entry points, boundaries, and
verification routes. Split disjoint evidence lanes and send bulk reading to the
lowest-cost capable workers available; the advanced leader owns scope,
contradiction resolution, packet acceptance, coverage, and escalation. Every
accepted claim needs concrete source paths, observed behavior, confidence, and
the owner/consumer/state/error/config/protocol/verification details required by
its criticality.

Keep only each semantic record in memory. Use `prd-scan init|status`
`record_digests`, compact `prd-scan record-list`, and selected `record-show`
reads; create or update one capability, artifact, entrypoint, configuration,
protocol, state-machine, error, verification, coverage, or
reconstruction-readiness row with `specify-runtime prd-scan record-upsert
<run-id> --surface <surface> --expected-sha256 <sha> --input-json
'<record-with-stable-id>' --format json`. Remove one obsolete row only through
`record-remove`. The PRD CLI owns all ten outer JSON documents, ordering,
digest checks, and atomic writes; never read/reconstruct or generically
prepare, submit, or patch those files. Keep critical unknowns explicit. Submit scan packets through the artifact CLI, worker results
through `result submit --command prd-scan --result-json`, and evidence through
the evidence CLI. Do not synthesize the final PRD or reread evidence on behalf
of the build phase.

Hand off to `$spx-prd-build` only when the CLI-owned scan package passes the contract's
reconstruction-ready gate. Otherwise persist `blocked-by-gap` with the exact
missing evidence and smallest recovery lane. This invocation authorizes only
this workflow stage; do not invoke another workflow in this run. The explicit
`$spx-prd` compatibility route owns scan-to-build continuation when it was the
user-authorized entrypoint.

After a leased workflow-state patch records `status: ready-for-build`,
`scan_status: complete`, `build_status: pending`, and the build handoff, run
`{{specify-subcmd:specify-runtime prd-scan finalize <run-id> --format json}}`;
only that command may seal `.specify/prd/status.json`. Then run
`{{specify-subcmd:specify-runtime hook validate-artifacts --command prd-scan --feature-dir .specify/prd-runs/<run-id> --format json}}`.
Do not hand off unless both native gates pass for the exact run.
