Trigger: before design closeout, downstream recommendation, adoption of a new approval round, or resuming a workflow that was blocked on design readiness.

Purpose: name the formal and direct consumers of design truth and prevent an approved design revision from silently changing in-flight delivery contracts.

Preserved Contract: formal delivery binds design through `sp-specify`, direct delivery binds it through `sp-quick`, immutable approvals remain pinned until explicit adoption, and integrated verification owns the final design-conformance claim.

## Consumer Roles

- `sp-discussion` may shape the product and help the user choose formal or
  direct delivery, but it is not a formal design-contract consumer and must not
  bind or rewrite `DS-*`/`DH-*` rows.
- `sp-specify` is the first formal consumer. It selects the feature-relevant
  registered `UD-*` contract, immutable approval digest, `DS-*` decisions, and
  `DH-*` handoff contracts and binds them into `spec-contract.json` plus the
  compact adoption document `ui-brief.md`.
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
- An audit pass that changes no design bytes, index state, or approval metadata may resume the
  originally blocked workflow when its existing binding is still exact. An
  audit failure routes change-scoped design truth to `create`/`refine`,
  feature-local truth to `sp-specify`/`sp-quick`, and implementation drift to
  `sp-review` or the active implementation workflow.

## Immutable Adoption

- A newly approved design round must not silently retarget an existing feature
  or Quick workspace. Existing delivery remains pinned to its recorded preview,
  manifest, handoff refs, SHA-256 values, and selected `DS-*`/`DH-*` rows.
- Discover candidates only with
  `specify-runtime design resolve --scope <exact-surface> --format json`;
  “latest” is never an adoption rule. A composite result must be split into
  independently bound consumer units. Current binding artifacts are singular;
  each unit owns one exact scope and one `spec-contract.json` or Quick
  `STATUS.md`.
- Before replacing a binding, run
  `specify-runtime design diff <CURRENT-UD-ID> <CANDIDATE-UD-ID> --format json`
  and preserve its scope, decision, handoff-contract, and changed-section delta
  in the owning consumer workflow. Then run the read-only
  `specify-runtime design impact <consumer-ref> --change <CANDIDATE-UD-ID> --scope <exact-surface> --mode <formal|quick> --expected-change <CURRENT-UD-ID|none> --format json`
  before patching any binding. Present its impact classes, affected `DS-*` /
  `DH-*` IDs, `preserved_bindings`, `invalidated_bindings`, and
  `reconcile_from`; its compare-and-swap preview must still match at adoption.
- To adopt the new approval in an existing formal feature, re-enter
  `sp-specify` and use fresh leased `specify-runtime artifact patch` calls to
  set the complete new four-field binding in `spec-contract.json` and
  `ui-brief.md`. Hash the exact `spec-contract.json` bytes, then run
  `specify-runtime design adopt feature:<feature-id> --change <UD-ID> --scope <exact-surface> --mode formal --binding-ref <feature-dir>/spec-contract.json --binding-sha256 <sha256> --expected-change <CURRENT-UD-ID|none> --format json`.
  Only a successful compare-and-swap receipt authorizes reconciliation. The
  receipt repeats `preserved_bindings`, `invalidated_bindings`, and
  `reconcile_from`: the owning formal workflow reconciles from that earliest
  stage, marks only the listed downstream surfaces pending, preserves completed
  implementation, and invalidates only affected-scope Review evidence. The
  design runtime does not rewrite `ui-brief.md`, Plan, Tasks, or Review.
- To adopt it in an active Quick task, present and persist a Quick checkpoint
  amendment containing the new exact design binding as
  `decision.ui_confirmation.design_binding` before implementation resumes.
  This confirmation-protected decision copy contains exact `scope` plus
  `design_change_id`, `design_change_ref`, `design_change_sha256`, and
  `design_contract_ref`. `quick checkpoint-confirm` must leave `confirmation.json` in
  `confirmed` or `inherited` state and `STATUS.md` with
  `understanding_confirmed: true`. After confirmation, use a fresh leased
  `specify-runtime artifact patch` call to set the independent
  top-level `## UI Design Binding` / `ui_design_binding` adoption copy in
  `STATUS.md`; do not manually duplicate the decision copy into the
  runtime-managed STATUS projection. The confirmation and adoption copies must
  match exactly. Hash those exact bytes, then run `specify-runtime design adopt quick:<quick-id> --change <UD-ID> --scope <exact-surface> --mode quick --binding-ref <quick-dir>/STATUS.md --binding-sha256 <sha256> --expected-change <CURRENT-UD-ID|none> --format json`.
  Without that confirmation and receipt, Quick remains pinned to its earlier
  snapshot. After success, the Quick owner uses the receipt to retire unstarted
  worker packets, stop affected in-progress packets at a safe boundary,
  preserve completed work, create a corrective work item where completed work
  now drifts, and recapture only affected Review evidence; unaffected scope and
  evidence stay valid.

Every consumer records `.specify/design/changes/<UD-ID>/DESIGN.md`, its
registered `approval_sha256`, preview/manifest/handoff digests, and selected
`DS-*`/`DH-*` rows. A new approval must never silently retarget an existing
consumer. The metadata-only `.specify/design/index.json` may resolve candidates,
but cannot authorize adoption by itself.
