---
name: spx-prd-build
description: Scan-to-PRD compilation workflow for advanced coding models. Use only after spx-prd-scan has produced a reconstruction-ready evidence package.
---

# SPX PRD Build

Read `references/project-cognition.md` only for its evidence boundary, then read
`references/prd-build-contract.md`. Do not run cognition intake in this phase:
the frozen scan package is the only allowed product-fact source.

Inspect the run with `{{specify-subcmd:prd-build <run-id> --json}}` and consume
its machine result `status: ready | blocked`,
`readiness: ready-to-build | complete | blocked`, `errors`, and `recovery`.
Treat `blocked` as a hard refusal and follow its stage-local recovery; never
reinterpret surface presence as semantic readiness. `ready-to-build` authorizes
compilation from the frozen package, while `complete` means the final package
also passed semantic validation. The frozen package is the only product-fact source.
Do not crawl or reread the repository, and do not invent facts to make an
export complete.

Before substantial synthesis, update the installed workflow state with
`active_command: sp-prd-build`, current build stage, `scan_status`,
`build_status`, `classification`, current packet, accepted/rejected packet
results, failed readiness checks, `failed_reverse_coverage_checks`, open gaps,
next action, next command, and handoff reason. Resume non-terminal build state
without discarding accepted joins or completed exports.

Compile `master/master-pack.md`, `exports/README.md`, `exports/prd.md`, and the
triggered supporting exports with the deterministic templates under
`.specify/templates/prd/`. Preserve traceability from each material statement
to accepted scan evidence. Reconcile duplicates and contradictions explicitly;
retain critical unknowns and reconstruction risks.

Preserve the scan's `ui | service | mixed` classification with
classification-aware exports: UI runs retain user-visible states, flows, and
interaction/error behavior; service runs retain API/CLI/runtime/configuration
contracts; mixed runs preserve both instead of collapsing one side.

Validate required files, contract shapes, reverse coverage, navigation links,
critical evidence depth, and the final workflow state. Delegation is optional
and limited to independent synthesis or validation lanes over the same frozen
scan package. The leader accepts joins and owns final consistency.

Rerun `{{specify-subcmd:prd-build <run-id> --json}}` after writing outputs. Mark
workflow state complete only when it returns `readiness: complete`; otherwise
persist its errors and recovery without claiming the suite complete.

Stop after producing the PRD suite. This reconstruction workflow is a peer
output and does not automatically create a feature, plan, tasks, or production
changes.
