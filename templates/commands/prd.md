---
description: Deprecated compatibility entrypoint for the old one-step PRD extraction flow.
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

## Migration Path

If an older doc, alias, or operator still calls `sp-prd`, route the work through the canonical flow instead:

```text
sp-prd-scan -> sp-prd-build
```

The scan step performs the read-only reconstruction investigation and produces the run package. The build step compiles the master pack and exports the final PRD suite.

## Guardrails

- Do not describe `sp-prd` as the preferred workflow.
- Do not keep one-step semantics alive in new guidance.
- Do not skip `sp-prd-scan` and jump straight to `sp-prd-build`.
