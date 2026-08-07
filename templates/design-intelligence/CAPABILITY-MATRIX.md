# Design Intelligence Capability Matrix

Classic (`sp-*`) and Advanced (`spx-*`) share one DI rule core. Advanced installs
a compact SPX surface; Classic installs the full partial bundle.

| Capability | Classic | Advanced (SPX) | Shared source of truth |
|------------|---------|----------------|------------------------|
| Taste / DNA / dials | `command-partials/common/design-intelligence.md` + design brief | `_shared/ui-quality-gate.md` + design brief | design brief + approved `DESIGN.md` |
| DesignContext v1 | schema + validator | same schema; SPX points to it | `templates/design-intelligence/schema/design-context.schema.json` |
| Evidence model v1 | evidence-rules partial + schema | ui-quality-gate pointer + schema | `design-evidence.schema.json` + `validate_design_evidence` |
| UI System Model | stage hooks in DI partials | stage hooks in ui-quality-gate | Evidence → System → Implementation pipeline |
| Stage hooks (discussion…review) | `design-intelligence/stage-hooks.md` | ui-quality-gate Stage hooks | same contracts, different packaging |
| Anti-slop | design-library + brief locks | same library + compact gate | `design-library/anti-slop-policy.md` |
| Visual validation | implement/review contracts | same + gate pointer | real-entrypoint capture + comparison / pending-human-review |
| Executable UI gate report | optional engine path | optional engine path | `ui-quality-gate-report.schema.json` |
| Approval authority | `specify-runtime design approve` | same | digests only |

## Packaging rules

- Classic includes DI through `{{spec-kit-include: ../common/design-intelligence.md}}`.
- That common file is an orchestrator over
  `templates/command-partials/design-intelligence/*` (context, evidence-rules,
  stage-hooks, ui-quality-gate pointer).
- Advanced `_shared/ui-quality-gate.md` is an **install surface**, not a second
  rule book: keep stage hooks compact; point at schemas for durable machine
  contracts.
- Do not grow per-workflow DI prose; add shared markers once and include them.
