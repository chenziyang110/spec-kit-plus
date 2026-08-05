Trigger: before closeout, downstream recommendation, adoption of a new approval, or return to a design-blocked workflow.

Purpose: bind every design task result to its real downstream consumer without silently upgrading pinned delivery work.

Preserved Contract: Specify owns formal binding, Quick owns direct binding and closeout, immutable approvals require explicit adoption, and Review owns final formal conformance.

## Consumers

- Discussion may shape intent and route choice, but it is not a formal
  design-contract consumer and never binds `DS-*`/`DH-*` rows.
- `$spx-specify` is the first formal consumer. It pins the relevant immutable
  approval, decisions, and handoff rows in `spec-contract.json` and
  `ui-brief.md`.
- `$spx-plan` maps only that bound contract into technical design;
  `$spx-tasks` projects it into task-local UI contracts; `$spx-implement`
  implements the pinned task truth.
- `$spx-review` is the final formal-path design verifier and binds integrated
  comparison to the exact approval digests and selected `DS-*`/`DH-*` rows.
- `$spx-quick` is the direct-delivery consumer. It pins the exact approval in
  Quick state and worker contracts, then plans, implements, converges, and
  closes inside Quick without manufacturing formal-stage artifacts.

## Handoff

- After create/refine, recommend Discussion if product intent cannot yet choose
  a route, Specify for user-selected formal delivery, or Quick for
  user-selected direct delivery with a confirmable outcome.
- Do not jump from changed design truth to Plan unless the active spec already
  binds the exact current approval digests and selected rows.
- An audit pass with no design/provenance change may resume the still-valid
  originally blocked workflow. Audit failure sends project truth to
  create/refine, feature truth to Specify/Quick, and code drift to Review or
  implementation.

## Immutable Adoption

A new approval must not silently retarget an existing formal feature or Quick
workspace. Keep old preview/manifest/handoff refs, SHA-256 values, and selected
`DS-*`/`DH-*` rows pinned. Formal adoption re-enters Specify and regenerates the
highest invalid downstream contract. Quick adoption requires a confirmed
checkpoint amendment with the new exact binding. Future work may bind the new
root baseline normally.

