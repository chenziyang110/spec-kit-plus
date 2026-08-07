## UI quality gate packaging

- **Classic** installs this Design Intelligence partial tree as the rule core.
- **Advanced (SPX)** installs `templates/advanced-skills/_shared/ui-quality-gate.md`
  as the compact install surface for UI-bearing skills. That file must **point
  at** shared schemas and this rule core—it is not a second independent rule
  book.
- Capability matrix: `templates/design-intelligence/CAPABILITY-MATRIX.md`
- Artifact lifecycle: `templates/design-intelligence/ARTIFACT-LIFECYCLE.md`
- Executable report schema:
  `templates/design-intelligence/schema/ui-quality-gate-report.schema.json`
- Deterministic starter rules:
  `specify_cli.design_intelligence.run_ui_quality_gate_rules`

Prompt gate remains valid until the executable engine expands. Never replace
`specify-runtime design approve` with gate report status alone.
