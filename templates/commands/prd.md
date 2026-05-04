---
description: Use when an older workflow or operator still invokes the deprecated `sp-prd` compatibility entrypoint and must be routed to the canonical `sp-prd-scan -> sp-prd-build` flow.
workflow_contract:
  when_to_use: Use only as a deprecated compatibility entrypoint when an older workflow still invokes `sp-prd`.
  primary_objective: Route operators to the canonical `sp-prd-scan` -> `sp-prd-build` reconstruction flow instead of presenting `sp-prd` as the primary reverse-PRD lane.
  primary_outputs: 'Compatibility runs should produce the same canonical artifacts as `sp-prd-scan` and `sp-prd-build`, including `.specify/prd-runs/<run-id>/prd-scan.md` and `.specify/prd-runs/<run-id>/exports/prd.md`.'
  default_handoff: Start with /sp-prd-scan, then continue to /sp-prd-build.
---

# `/sp.prd` Deprecated Compatibility Entrypoint

## Workflow Contract Summary

This summary is routing metadata only. The full workflow contract is the frontmatter plus the sections below.

- `sp-prd` is deprecated.
- `sp-prd` is compatibility-only and is no longer the primary reverse-PRD lane.
- Use `sp-prd-scan` first, then `sp-prd-build`.

## Objective

Route deprecated `sp-prd` invocations into the canonical reconstruction flow
without preserving the old one-step semantics as a preferred workflow path.

## Migration Path

[AGENT] If an older doc, alias, or operator still calls `sp-prd`, route the work through the canonical flow instead and preserve compatibility wording only as a migration aid.

If an older doc, alias, or operator still calls `sp-prd`, route the work through the canonical flow instead:

```text
sp-prd-scan -> sp-prd-build
```

The scan step performs the read-only reconstruction investigation and produces the run package. The build step compiles the master pack and exports the final PRD suite.

## Process

1. Detect whether the current invocation came through the deprecated `sp-prd`
   compatibility path.
2. Explain that `sp-prd` is compatibility-only and no longer the primary
   reverse-PRD lane.
3. Start with `sp-prd-scan`.
4. Continue to `sp-prd-build` after the reconstruction scan package is ready.

## Output Contract

- Compatibility routing should hand the operator to `sp-prd-scan` first.
- Final artifacts still come from the canonical pair:
  - `.specify/prd-runs/<run-id>/prd-scan.md`
  - `.specify/prd-runs/<run-id>/exports/prd.md`

## Guardrails

- Do not describe `sp-prd` as the preferred workflow.
- Do not keep one-step semantics alive in new guidance.
- Do not skip `sp-prd-scan` and jump straight to `sp-prd-build`.
