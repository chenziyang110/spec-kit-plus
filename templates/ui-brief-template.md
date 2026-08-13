# UI Brief

This is a feature adoption binding, not a copy of the design system. Keep only
the selected design-change identity, feature-relevant rows, and feature delta.

## Source Design Change

- Design change ID: UD-____
- Registered design ref: .specify/design/changes/<UD-ID>/DESIGN.md
- Machine contract ref: .specify/design/changes/<UD-ID>/design-contract.json
- Registered design-change SHA-256:
- Design readiness: approved | narrow-existing-pattern-exception | blocked
- Approved visual ref: .specify/design/changes/<UD-ID>/previews/round-NN.html#direction-id
- Approved direction ID and review round:
- Preview / manifest / handoff SHA-256:
- Immutable handoff ref:
- Selected design decision IDs: []
- Selected handoff contract IDs and exact rows: []

## Feature Adoption

- UI work type: existing-pattern | feature-extension | reference-implementation
- Surface type: landing | product-workspace | hybrid | existing-pattern-maintenance
- Platforms and capability profiles:
- Applicable specimen IDs:
- Real entry points:
- Required states and viewports:
- Subject / audience / single user job:
- Design DNA / personality inherited by this feature:
- Dials (variance / motion / density) and inference reason when relevant:
- Anti-slop locks selected for this surface:

## Feature Delta

Record only what this feature narrows, extends, or overrides. Empty means exact
adoption; it does not authorize reinterpretation.

- Layout and information hierarchy:
- Tokens and components:
- Component anatomy and required states:
- Interaction and feedback timing:
- Responsive adaptation:
- Motion and reduced-motion behavior:
- Accessibility and keyboard requirements:
- Real content and imagery plan:
- Must preserve:
- May adapt:
- Must not:

## Reference And Fidelity

- UI reference notes: ui-reference-notes.md | none
- Visual target: ui-target.html | none
- Original inspectable assets:
- Reference intents: [{ref, intent: exact | preserve-structure | inspiration | extract-tokens | do-not-copy}]
- Fidelity mode: approximate | high | inspiration
- Fidelity criteria and human review condition:
- Ownership and forbidden copying:

## Required Evidence

- Required kinds: `structure_snapshot`, `visual_capture`,
  `runtime_diagnostics`, `visual_comparison_or_human_review`
- Visual acceptance matrix: [entry point | viewport | state | expected result | evidence path]
- Decision coverage: [DS/DH ID | task IDs | viewport/state | comparison evidence]
- Comparison report: [design ref + contract/preview/manifest/handoff SHA | implementation capture | difference | tolerance | deviation]
- Comparison tolerance: copy the selected immutable structured object; prose is invalid
- Accepted deviations and approver:
- Pending human review condition:

## Worker Contract

- Required design sources: exact change ref, machine contract, visual ref,
  handoff ref, this brief, and original references
- Required packet fields: `design_change_id`, `design_change_ref`,
  `design_change_sha256`, `design_contract_ref`, selected `DS-*`/`DH-*` rows,
  entry points, states, Must Preserve / May Adapt / Must Not, evidence
- Convergence loop: run real entry point -> capture -> query the exact pinned
  change and this brief -> compare -> repair -> recapture
- Done condition: behavior checks and visual/interaction acceptance both pass
- Stop condition: source/digest drift, missing state evidence, unresolved
  overlap, or a requested design change outside the pinned contract
