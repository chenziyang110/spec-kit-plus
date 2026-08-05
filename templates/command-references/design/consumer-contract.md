Trigger: before design closeout, downstream recommendation, adoption of a new approval round, or resuming a workflow that was blocked on design readiness.

Purpose: name the formal and direct consumers of design truth and prevent an approved design revision from silently changing in-flight delivery contracts.

Preserved Contract: formal delivery binds design through `sp-specify`, direct delivery binds it through `sp-quick`, immutable approvals remain pinned until explicit adoption, and integrated verification owns the final design-conformance claim.

## Consumer Roles

- `sp-discussion` may shape the product and help the user choose formal or
  direct delivery, but it is not a formal design-contract consumer and must not
  bind or rewrite `DS-*`/`DH-*` rows.
- `sp-specify` is the first formal consumer. It selects the feature-relevant
  immutable approval, `DS-*` decisions, and `DH-*` handoff contracts and binds
  them into `spec-contract.json` plus `ui-brief.md`.
- `sp-plan` maps that already-bound feature contract into technical choices and
  `ui_design_contract`; it does not select an unbound newer design version.
- `sp-tasks` projects the plan-bound subset into each task-local `ui_contract`.
- `sp-implement` implements the pinned task contract and captures real-entrypoint
  evidence.
- `sp-review` is the final formal-path design verifier. It binds the integrated
  visual comparison to the exact approval digests and selected `DS-*`/`DH-*`
  coverage before `sp-accept` receives the reviewed product snapshot.
- `sp-quick` is the direct-delivery consumer. It pins the exact approved design
  snapshot in `STATUS.md` and UI worker packets, performs task-local technical
  planning, implementation, real-entrypoint convergence, and truthful closeout
  without manufacturing the formal spec/plan/task/review artifact chain.

## Handoff Rules

- After `create` or `refine`, recommend `sp-discussion` when product intent is
  still too unclear to choose a delivery route.
- Recommend `sp-specify` when the user chooses durable requirements-first
  delivery. Recommend `sp-quick` when the user chooses direct delivery and the
  complete outcome is confirmable at the Quick checkpoint.
- Do not recommend `sp-plan` immediately after a design mutation unless the
  active `spec-contract.json` already binds the exact current approval digests
  and selected design rows. A changed approval normally re-enters
  `sp-specify` first.
- An audit pass that changes no design bytes or approval metadata may resume the
  originally blocked workflow when its existing binding is still exact. An
  audit failure routes project-wide design truth to `create`/`refine`,
  feature-local truth to `sp-specify`/`sp-quick`, and implementation drift to
  `sp-review` or the active implementation workflow.

## Immutable Adoption

- A newly approved design round must not silently retarget an existing feature
  or Quick workspace. Existing delivery remains pinned to its recorded preview,
  manifest, handoff refs, SHA-256 values, and selected `DS-*`/`DH-*` rows.
- Future features may bind the new root baseline through `sp-specify`.
- To adopt the new approval in an existing formal feature, re-enter
  `sp-specify`, record the design adoption delta, then regenerate the highest
  invalid downstream plan/task surfaces.
- To adopt it in an active Quick task, present and persist a Quick checkpoint
  amendment containing the new exact design binding before implementation
  resumes. Without that confirmation, Quick remains pinned to its earlier
  snapshot.

