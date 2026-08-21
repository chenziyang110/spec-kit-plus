Trigger: before closeout, downstream recommendation, adoption of a new approval, or return to a design-blocked workflow.

Purpose: bind every design task result to its real downstream consumer without silently upgrading pinned delivery work.

Preserved Contract: the requirements workflow owns design-first formal binding and requirements;
a late design overlay uses a digest-bound receipt and returns to Plan; Quick
owns direct binding and closeout. Immutable approvals require explicit adoption,
and Review owns final formal conformance.

## Consumers

- Discussion may shape intent and route choice, but it is not a formal
  design-contract consumer and never binds `DS-*`/`DH-*` rows.
- On a design-first route, `$spx-specify` is the first formal consumer. It pins the relevant registered
  `UD-*` contract, approval digest, decisions, and handoff rows in `spec-contract.json` and
  `ui-brief.md`.
- On a post-specify route, the requirements workflow is already the requirements owner. Keep its
  planning-ready source spec byte-identical and bind the registered design with
  a `formal-post-specify` adoption receipt.
- `$spx-plan` maps either the requirements-bound design or the verified post-specify
  overlay into technical design only after verifying the exact current approval digests;
  `$spx-tasks` projects it into task-local UI contracts; `$spx-implement`
  implements the pinned task truth.
- `$spx-review` is the final formal-path design verifier and binds integrated
  comparison to the exact approval digests and selected `DS-*`/`DH-*` rows.
- `$spx-quick` is the direct-delivery consumer. It pins the exact approval in
  Quick state and worker contracts, then plans, implements, converges, and
  closes inside Quick without manufacturing formal-stage artifacts.

## Handoff

- After create/refine, recommend Discussion if product intent cannot yet choose
  a route, Specify for design-first formal delivery, or Quick for user-selected
  direct delivery with a confirmable outcome.
- When Design started from a planning-ready source spec and requirements stayed
  unchanged, the route is specify -> design -> plan, must not require a second Specify,
  and uses `formal-post-specify`. A real requirements change is the
  only reason to return to Specify before adoption.
- An audit pass with no design/provenance change may resume the still-valid
  originally blocked workflow. Audit failure sends project truth to
  create/refine, feature truth to Specify/Quick, and code drift to Review or
  implementation.

## Immutable Adoption

A new approval must not silently retarget an existing formal feature or Quick
workspace. Keep old preview/manifest/handoff refs, SHA-256 values, and selected
`DS-*`/`DH-*` rows pinned. Discover candidates with
`specify-runtime design resolve --scope <exact-surface> --format json`; this is
discovery only. Current binding artifacts are singular, so composite results
require independently bound consumer units, each with one exact scope and one
binding artifact. Before replacement
run `specify-runtime design diff <CURRENT-UD-ID> <CANDIDATE-UD-ID> --format json`,
then preview the exact consumer transaction with
`specify-runtime design impact <consumer-ref> --change <CANDIDATE-UD-ID> --scope <exact-surface> --mode <formal|formal-post-specify|quick> --expected-change <CURRENT-UD-ID|none> --format json`.
Impact is read-only; present its affected `DS-*`/`DH-*` IDs,
`preserved_bindings`, `invalidated_bindings`, and `reconcile_from` before any
binding patch.

Design-first formal adoption, or adoption after a genuine requirements change,
uses the requirements workflow and fresh leased
`specify-runtime artifact patch` calls to update `spec-contract.json` and
`ui-brief.md` first, hashes the exact spec contract, then runs
`specify-runtime design adopt feature:<feature-id> --change <UD-ID> --scope <exact-surface> --mode formal --binding-ref <feature-dir>/spec-contract.json --binding-sha256 <sha256> --expected-change <CURRENT-UD-ID|none> --format json`.
The late overlay does not rewrite that spec. Hash the unchanged planning-ready
source spec, adopt with `--mode formal-post-specify`, then verify read-only with
`specify-runtime design adoption feature:<feature-id> --scope <exact-surface>
--binding-ref <feature-dir>/spec-contract.json --binding-sha256
<source-spec-sha256> --expected-change <UD-ID>`. The receipt is the late overlay
Plan consumes; it preserves feature requirements and acceptance truth.
Quick adoption requires a confirmed checkpoint amendment, updates `STATUS.md`
only after exact `scope` plus the four registered fields have been staged as
the confirmation-protected `decision.ui_confirmation.design_binding` and
`confirmation.json` is `confirmed` or `inherited`; runtime owns the STATUS
readiness projection. Use a fresh leased `specify-runtime artifact patch` call
to update the independent top-level `## UI Design Binding` /
`ui_design_binding` adoption copy. Do not manually duplicate the decision copy
into the runtime-managed STATUS projection. Both copies must match; hash the
exact status bytes, then run
`specify-runtime design adopt quick:<quick-id> --change <UD-ID> --scope <exact-surface> --mode quick --binding-ref <quick-dir>/STATUS.md --binding-sha256 <sha256> --expected-change <CURRENT-UD-ID|none> --format json`.
Only a successful compare-and-swap receipt authorizes downstream regeneration
or Quick resume. Formal owners reconcile from the receipt's earliest stage,
mark only listed bindings pending, preserve completed implementation, and
recapture affected Review evidence only; the design runtime never rewrites
those artifacts. Quick owners retire unstarted packets, stop affected
in-progress work at a safe boundary, preserve completed work, create a
corrective work item for drift, and recapture only affected Review evidence.
“Latest” is never an adoption rule; metadata-only index state cannot authorize
adoption by itself.
