---
name: spx-prd-scan
description: Reconstruction-grade repository scan for advanced coding models. Use when an existing product needs a read-only evidence package before a PRD suite can be compiled.
---

# SPX PRD Scan

Read `references/project-cognition.md`, using cognition intent `research`, and
`references/prd-scan-contract.md`.

Initialize or resume the run with
`{{specify-subcmd:prd-scan <run-slug> --json}}`; inspect existing status before
creating a new workspace. Project source, tests, configuration, and docs are
read-only. The `.specify/prd-runs/<run-id>/` evidence workspace is writable and
must remain resumable.

Read and update the installed `workflow-state.md` instead of reconstructing the
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

Build the canonical scan ledgers and contracts in the run workspace, including
capability, artifact, entrypoint, configuration, protocol, state-machine, error,
verification, coverage, and reconstruction-readiness evidence. Keep critical
unknowns explicit. Do not synthesize the final PRD or reread evidence on behalf
of the build phase.

Hand off to `$spx-prd-build` only when the scan package passes the contract's
reconstruction-ready gate. Otherwise persist `blocked-by-gap` with the exact
missing evidence and smallest recovery lane. This invocation authorizes only
this workflow stage; do not invoke another workflow in this run. The explicit
`$spx-prd` compatibility route owns scan-to-build continuation when it was the
user-authorized entrypoint.
