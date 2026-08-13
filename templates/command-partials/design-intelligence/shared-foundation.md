## Design Intelligence Engine (three capabilities)

- **Taste Intelligence**: personality/DNA, dials, anti-slop, signature
- **Design System Reverse Engineering**: Evidence → UI System Model before
  implementation
- **Visual Validation**: real-entrypoint capture, comparison,
  pending-human-review

`sp-design` / `spx-design` is the studio that materializes one approved,
registered change-scoped truth; other stages **consume an exact pinned change**
through Design Intelligence hooks.

## Owners (do not invent parallel systems)

- Design DNA / theses / signature → exact registered change-local `DESIGN.md` + design brief
- Change dials → `design_brief.dials` variance · motion · density (1-10)
- Taste intake → `design_read`, aesthetic family, foundation strategy, redesign
  mode
- Anti-slop locks → `design_brief.anti_slop_locks` +
  `design-library/anti-slop-policy.md`
- UI System Model → `.specify/design/changes/<UD-ID>/DESIGN.md` + its
  change-local `design-contract.json`
- Evidence confidence →
  `templates/design-intelligence/schema/design-evidence.schema.json` +
  `validate_design_evidence`
- DesignContext schema →
  `templates/design-intelligence/schema/design-context.schema.json` (v1)
- Artifact lifecycle → `templates/design-intelligence/ARTIFACT-LIFECYCLE.md`
- Approval authority → `specify-runtime design approve` / export digests only
- Feature composition → `ui-brief.md` → plan `ui_design_contract` → task
  `ui_contract`
- Durable discussion carry → Design Carry-Forward + handoff `design_context`

Do **not** create a parallel root `.design/` tree or mutable global design
authority. Use `.specify/design/changes/<UD-ID>/**`; a pre-existing root
`DESIGN.md` is read-only legacy baseline input only.

## DesignContext v1 (schema contract)

Durable design-context payloads **MUST** conform to DesignContext v1 when
serialized as structured JSON (discussion handoff fields, brief-adjacent
machine records, or runtime owners under `.specify/design/context/`):

- Schema: `templates/design-intelligence/schema/design-context.schema.json`
- Required: `version: "1.0"`, `intent.user_goal`
- Optional: `design_language` (tone + dials), `system`, `references`,
  `decisions`, `evidence` (objects validated by design-evidence schema)
- Validate via `specify_cli.design_intelligence.validate_design_context`
  (structure + evidence semantics; no taste scoring, no screenshot parsing)

Prompt-stage prose may remain human-readable; machine-readable carry-forward
must not invent a second parallel vocabulary.
