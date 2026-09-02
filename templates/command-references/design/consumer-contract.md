Trigger: before design closeout, downstream recommendation, adoption of a new approval round, or resuming a workflow that was blocked on design readiness.

Purpose: name the formal and direct consumers of design truth and prevent an approved design revision from silently changing in-flight delivery contracts.

Preserved Contract: design-first formal delivery binds design through
`sp-specify`; a late design overlay binds immutably to the
unchanged source spec and returns to Plan; direct delivery binds through
`sp-quick`. Immutable approvals remain pinned until explicit adoption, and
integrated verification owns the final design-conformance claim.

## Consumer Roles

- `sp-discussion` may shape the product and help the user choose formal or
  direct delivery, but it is not a formal design-contract consumer and must not
  bind or rewrite `DS-*`/`DH-*` rows.
- Direction-confirmed is non-consumable. Plan and Implement may consume only
  formal-approval plus register, represented by the approve/register receipt,
  registered `approval_sha256`, exact design-change ref, and exported contract.
  Direction-confirmed must not bind `spec-contract.json`, Quick `STATUS.md`, a
  task `ui_contract`, or any implementation packet.
  Direction-confirmed must not bind spec-contract.json or any other delivery
  artifact.
- For a design-first route, `sp-specify` is the first formal consumer. It selects the feature-relevant
  registered `UD-*` contract, immutable approval digest, `DS-*` decisions, and
  `DH-*` handoff contracts and binds them into `spec-contract.json` plus the
  compact adoption document `ui-brief.md`.
- For a post-Specify route, `sp-specify` is already the requirements owner. Its
  planning-ready `spec-contract.json` remains byte-identical while Design is
  approved and registered. A `formal-post-specify` adoption receipt binds the
  late Design overlay to that exact source spec digest.
- `sp-plan` maps either the design-first bound feature contract or a verified
  post-Specify overlay into technical choices and `ui_design_contract`; it does
  not select an unbound newer design version. In both routes, Plan must verify
  the exact current approval digests before authoring technical choices.
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
- On a design-first route, recommend `sp-specify`; the mainline is
  `design -> specify -> plan`. Recommend `sp-quick` when the user chooses direct
  delivery and the complete outcome is confirmable at the Quick checkpoint.
- On a post-Specify route, preserve the planning-ready source spec and use
  `formal-post-specify`; the mainline is `specify -> design -> plan` and must
  not require a second Specify. Reopen Specify only when Design exposes a real
  requirements change in behavior, scope, constraints, or acceptance—not for a
  visual, interaction, layout, responsive, or component-contract decision that
  stays inside the approved feature semantics.
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
  `specify-runtime design impact <consumer-ref> --change <CANDIDATE-UD-ID> --scope <exact-surface> --mode <formal|formal-post-specify|quick> --expected-change <CURRENT-UD-ID|none> --format json`
  before patching any binding. Present its impact classes, affected `DS-*` /
  `DH-*` IDs, `preserved_bindings`, `invalidated_bindings`, and
  `reconcile_from`; its compare-and-swap preview must still match at adoption.
- For design-first adoption, or after a genuine requirements change, use
  `sp-specify` and fresh leased `specify-runtime artifact patch` calls to
  set the complete new four-field binding in `spec-contract.json` and
  `ui-brief.md`. Hash the exact `spec-contract.json` bytes, then run
  `specify-runtime design adopt feature:<feature-id> --change <UD-ID> --scope <exact-surface> --mode formal --binding-ref <feature-dir>/spec-contract.json --binding-sha256 <sha256> --expected-change <CURRENT-UD-ID|none> --format json`.
  Only a successful compare-and-swap receipt authorizes reconciliation. The
  receipt repeats `preserved_bindings`, `invalidated_bindings`, and
  `reconcile_from`: the owning formal workflow reconciles from that earliest
  stage, marks only the listed downstream surfaces pending, preserves completed
  implementation, and invalidates only affected-scope Review evidence. The
  design runtime does not rewrite `ui-brief.md`, Plan, Tasks, or Review.
- For Design started from an existing planning-ready feature spec whose
  requirements did not change, do not patch `spec-contract.json` and do not run
  Specify again. Hash the unchanged source spec, preview impact with
  `--mode formal-post-specify`, then run
  `specify-runtime design adopt feature:<feature-id> --change <UD-ID> --scope
  <exact-surface> --mode formal-post-specify --binding-ref
  <feature-dir>/spec-contract.json --binding-sha256 <source-spec-sha256>
  --expected-change <CURRENT-UD-ID|none> --format json`. Verify the current
  receipt with `specify-runtime design adoption feature:<feature-id> --scope
  <exact-surface> --binding-ref <feature-dir>/spec-contract.json
  --binding-sha256 <source-spec-sha256> --expected-change <UD-ID>`. This receipt
  is the explicit late overlay and sends the feature to Plan. The runtime never
  rewrites the source specification.
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

Every consumer records `.specify/design/changes/<UD-ID>/design-change.md`, its
registered `approval_sha256`, preview/manifest/handoff digests, and selected
`DS-*`/`DH-*` rows. A new approval must never silently retarget an existing
consumer. The metadata-only `.specify/design/index.json` may resolve candidates,
but cannot authorize adoption by itself.
