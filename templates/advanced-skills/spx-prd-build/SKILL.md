---
name: spx-prd-build
description: Scan-to-PRD compilation workflow for advanced coding models. Use only after spx-prd-scan has produced a reconstruction-ready evidence package.
---

# SPX PRD Build

Read `references/project-cognition.md` only for its evidence boundary, then read
`references/prd-build-contract.md`. Do not run cognition intake in this phase:
the frozen scan package is the only allowed product-fact source.

Inspect the run with `{{specify-subcmd:prd-build <run-id> --json}}`. Treat a
blocked result as a hard refusal and route the missing evidence back to
`$spx-prd-scan`. The validated scan workspace is the only product-fact source
for this phase: do not crawl or reread the repository, and do not invent facts
to make an export complete.

Compile `master/master-pack.md`, `exports/README.md`, `exports/prd.md`, and the
triggered supporting exports with the deterministic templates under
`.specify/templates/prd/`. Preserve traceability from each material statement
to accepted scan evidence. Reconcile duplicates and contradictions explicitly;
retain critical unknowns and reconstruction risks.

Validate required files, contract shapes, reverse coverage, navigation links,
critical evidence depth, and the final workflow state. Delegation is optional
and limited to independent synthesis or validation lanes over the same frozen
scan package. The leader accepts joins and owns final consistency.

Stop after producing the PRD suite. This reconstruction workflow is a peer
output and does not automatically create a feature, plan, tasks, or production
changes.
