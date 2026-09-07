# UI Workflows

Read before changing Design, UI briefs, UI-bearing Spec/Plan/Tasks, worker
packets, source continuity, visual evidence, or UI Review/Accept contracts.
These requirements govern the workflow product being maintained; they do not
activate a generated workflow for ordinary source-repository maintenance.
Source paths below are repository-relative; Advanced `_shared/` paths are
relative to `templates/advanced-skills/`. Generated artifact names retain the
workspace context of their owning workflow.

## UI Workflow Contract Across Profiles

### Routing and Registered Design Truth

- `sp-design` / `spx-design` is one natural-language entrypoint. Route prompt
  intent to `create/refine/audit`; reference synthesis is an input strategy for
  create/refine, not a public colon subskill or terminal task type. Resume
  active design work before reclassification. On a design-first route,
  `sp-specify` is the first formal consumer; when Design follows an already
  planning-ready feature spec and requirements remain unchanged, a
  `formal-post-specify` receipt binds the late Design overlay to the unchanged
  source-spec digest and returns directly to Plan (`specify -> design -> plan`).
  Plan verifies that receipt with `specify-runtime design adoption`; that path
  must not require a second Specify. Only a genuine requirements,
  scope, or acceptance change reopens Specify. `sp-quick` is the direct-delivery
  consumer. A new approval must not silently retarget pinned work: design-first
  formal adoption rebinds through Specify, while Quick requires a confirmed checkpoint amendment whose
  `decision.ui_confirmation.design_binding` names the exact scope and
  registered change.
- The product goal is better implemented UI, not merely more UI documentation.
  Both profiles must preserve this executable chain for substantive UI work:
  `approved immutable change-local preview + original references -> registered
  .specify/design/changes/<UD-ID>/design-change.md + approval_sha256 -> feature
  ui-brief.md -> plan ui_design_contract -> per-task ui_contract ->
  real-entrypoint captures + visual comparison report`.
- UI applicability is broader than reference-image intake. New or changed
  screens, components, layouts, navigation/interaction flows, responsive
  behavior, visual states, desktop/mobile surfaces, TUI layouts, and CLI
  presentation can all trigger the UI contract.
- The design workflow has no root design contract. `specify-runtime design change`
  creates one bounded `.specify/design/changes/<UD-ID>/` workspace, and only an
  explicitly selected, registered change-local contract may bind delivery work.
  New or high-visibility UI requires an approved, registered
  change-local contract; narrow existing-pattern fixes may record a bounded
  exception. Durable invariants for future unrelated work are promoted
  explicitly to `.specify/memory/project-rules.md`, not accumulated by mutating
  a global design document.
- Refining approved truth uses
  `specify-runtime design iterate <SOURCE-UD-ID> <SUCCESSOR-UD-ID>` so
  `iteration_of`, `basis_sha256`, the baseline digest, and `supersedes` are
  runtime-pinned. A requested successor scope must still be active on that
  source; once a subtree is excluded, iterate from its active successor or from
  a remaining active parent scope. `specify-runtime design register` subtracts
  only intersecting scope into parent `superseded_scopes`; the parent remains active elsewhere.
  `specify-runtime design resolve --scope <exact-surface>` is discovery only
  and may return a composite. Current consumer binding artifacts are singular,
  so split that result into independently bound consumer units, each with one
  exact scope and one binding artifact. Before rebinding, run
  `specify-runtime design diff <CURRENT-UD-ID> <CANDIDATE-UD-ID>`, then preview
  the exact scope-bounded consumer effect with `specify-runtime design impact
  <consumer-ref> --change <CANDIDATE-UD-ID> --scope <exact-surface> --mode
  <formal|quick> --expected-change <CURRENT-UD-ID|none>`. Impact is read-only
  and reports impact classes, affected `DS-*`/`DH-*` IDs,
  `preserved_bindings`, `invalidated_bindings`, and `reconcile_from`. After the
  owning workflow confirms the preview, updates and hashes its binding artifact, record the exact
  compare-and-swap with `specify-runtime design adopt ... --expected-change
  <CURRENT-UD-ID|none>`. The receipt repeats the impact contract. Formal mode
  binds `spec-contract.json` through Specify, reconciles from the named stage,
  marks only affected downstream bindings and Review evidence pending, and
  preserves completed implementation plus unaffected evidence; the design
  runtime never rewrites those consumer artifacts.
  Quick mode first stages exact `scope` plus the four registered binding fields
  as confirmation-protected `decision.ui_confirmation.design_binding`, then
  requires `confirmation.json` state `confirmed|inherited` and
  `understanding_confirmed: true`. Only afterward does it bind the independent
  top-level `ui_design_binding` adoption copy in `STATUS.md`; the two copies
  must exact-match, and the decision copy remains in `confirmation.json` rather
  than being manually written into the runtime-managed STATUS projection. A
  successful Quick replacement retires unstarted affected packets, stops
  in-progress affected packets at a safe boundary, preserves completed work,
  creates a corrective work item for completed-work drift, and recaptures only
  affected Review evidence.
### Concept, Direction, and Approval

- Every substantive design round presents one professionally authored current
  concept through a live capability-routed primary medium. Probe
  `image_generation`, `image_inspection`, and `image_editing` independently at
  entry/resume; never hard-code them from an Agent, model, CLI, or integration.
  When generation is available, use one image-primary review board plus its
  exact generate/edit prompt and machine-readable manifest. When generation is
  unavailable, use one self-contained HTML-primary concept with a stable deep
  link and embedded manifest. Inspection availability separately determines
  whether the Agent may inspect actual pixels and claim visual quality or must
  leave visual critique to the user; editing availability selects targeted edit
  versus invariant-preserving regeneration. Image prompts and semantic
  HTML/DOM/CSS authoring prompts are distinct professional contracts. Both
  routes preserve component/state specimens, deliberate color and motion
  systems, and responsive targets. The Agent discovers intent through one
  high-impact question at a time, makes a grounded recommendation, and does not
  advance past an unanswered question. User feedback revises the same concept
  in a new inspected/reviewed immutable round; never mutate an approved round
  in place. Only explicit user approval may freeze the current concept.
- Substantive create/refine work uses the platform-neutral sequence
  `intake -> concept-calibration -> direction-confirmed -> contract-completion
  -> formal-approval -> register`. Before direction confirmation, author only
  the minimum needed to judge one visual direction: exact scope and selected
  profiles, subject/audience/single job, taste, primary layout and signature,
  layout-changing critical states, contrast/focus/reduced-motion feasibility,
  and one stress target. After concept lint and explicit user confirmation,
  `specify-runtime design direction-confirm` writes an immutable
  `round-NN.direction.json` checkpoint. It is non-consumable, does not approve
  or register the change, never enters Plan/Tasks/Implement, and is not written
  to the Design index. Contract completion starts in the next numbered round,
  where complete source-continuity coverage, mature component adoption,
  scenario/interaction/editing/state/accessibility matrices, and `DH-*` rows
  are added without changing the confirmed visual direction. If that work
  requires a material visual change, return to concept calibration and user
  review. Only the existing formal approve-and-register chain is consumable.
### Professional Resources and Existing Style Authority

- The shared **UI Professional Skill** pack uses progressive disclosure before
  substantive create/refine authoring: read its compact catalog, select exactly
  one domain, zero-or-one style, and zero-to-two specialists, then load only
  those references. Persist the route and resume it for the active immutable
  round. Material ambiguity asks one high-impact question instead of blending
  conflicting styles. Approved references and registered design truth outrank
  routed advice; image-primary and HTML-primary use distinct augmented prompts.
- Web UI professional routing also persists a compact
  `mature_web_ui_resource_ids` shortlist. Inspect installed packages, live
  components, tokens, versions, licenses, and exact capability needs first;
  reuse or extend live components before choosing one compatible mature primary
  system, and add headless/specialist support only for a recorded gap. Load
  official Agent Skills, MCP, `llms.txt`, or Markdown docs only for selected
  candidates; they do not authorize installation, upgrade, migration, or
  license acceptance. Smoothness still requires real-entrypoint evidence for
  focus/selection/scroll continuity, pending/cancel behavior, large-data
  performance, interruption, and reduced motion.
  The deterministic helper accepts the actual project root, reads only
  catalog-listed manifests and paths, and persists `web_ui_asset_inventory`,
  explainable `mature_web_ui_selection` reason/confirmation codes, a
  deterministic component adoption plan, read-only selected-official-resource
  drift results, `smoothness_acceptance_ids`, and performance budgets. An
  unscanned inventory is provisional; install/add/upgrade/license actions remain
  confirmation-gated. Carry adoption rows into component contracts and
  smoothness IDs/budgets through interaction, motion, usability, and integrated
  Review evidence. `evidence smoothness-manifest|smoothness-validate` owns the
  real-entrypoint Playwright matrix and hashed report without adding another UI
  evidence kind.
- Live UI is the default style authority. Feature, component, and partial
  functional-page work inside an existing product uses structured
  `style_authority.mode: inherit-existing`, cites exact live source refs,
  protects `global-shell` and `shared-components`, allows no style-delta
  surfaces, and cannot select a style skill. Only explicit user authorization
  for one exact complete-page visual overhaul may use
  `page-overhaul-authorized`; only that page may change style, while shell and
  shared components stay protected. Carry `style_authority` unchanged through
  Design, UI brief, Spec/Plan, Tasks, worker packets, and Review.
- Brownfield routing separates the design artifact lifecycle from visual
  authority: `contract_action: create|refine|audit` never widens
  `surface_posture: greenfield|inherit-existing|page-overhaul-authorized`.
  `inherit-existing` image rounds require exact project-contained edit-source
  coverage and exact/preserve source-continuity bindings for every protected
  surface. Keep the exact professional prompt in memory and pass it through
  stdin to `specify-runtime design prompt <manifest> --content -` before image
  generation/import.
- The adjacent image prompt and generation sidecar are runtime-owned outputs of
  that create-only specialized command. Their content remains byte-identical;
  a different request uses a new numbered round. Concept lint owns a
  byte-bound receipt and, when inspection is available, its protected-surface
  comparison; `direction-confirm` rejects missing or stale receipts.
### Immutable Approval and Task Binding

- `specify-runtime design approve` freezes one exact change-local direction
  with a byte-bound approval sidecar, visual/manifest SHA-256 digests, the
  image-generation prompt digest when image-primary, a
  separate immutable handoff sidecar and digest, review round, stable `DS-*`
  decision IDs, and stable `DH-*` implementation contract IDs. Ready lint and
  export must reject a change-local `design-change.md` whose approval fields do not
  match those immutable artifacts. `specify-runtime design register` is the
  downstream consumption boundary: it pins that document's exact SHA-256 in
  metadata-only `.specify/design/index.json`, rejects later mutation, and
  rejects overlapping active scope without an explicit relationship.
- Classic keeps the explicit UI lane, full `sp-design` professional references,
  passive `frontend-design` guidance, worker prompts, and verbose
  evidence mapping. Advanced must not install that passive bundle; its essential
  equivalent lives in `_shared/ui-quality-gate.md`, owning SPX references,
  compact deterministic assets, and shared runtime schemas/validators.
- Do not treat a top-level UI coverage table as sufficient. Every UI-bearing
  task must carry structured task-local design sources, fidelity, states,
  must-preserve/may-adapt/must-not rules, and required visual evidence so the
  worker packet cannot silently downgrade UI work to `not_applicable`. It also
  carries `design_change_id`, `design_change_ref`, `design_change_sha256`, and
  `design_contract_ref`; no stage may resolve an unbound "latest" change.
### Source Continuity and Interaction Contracts

- Reference-, live-product-, recording-, or implementation-grounded UI also
  carries `spec-kit-ui-source-continuity-v1`. Authority refs bind exact source
  surfaces; complete coverage surface/interaction/component ID sets must equal
  their binding targets so sampled happy paths cannot close a larger UI;
  surface bindings carry preserve/adapt/replace/merge/split/retire dispositions; action
  bindings map interaction IDs to user promises, business outcomes, side
  effects, final states, and source-target verification; asset bindings map
  component IDs to semantics, provenance, target strategy/ref, fallback, and
  `forbid-character-substitution`. Screenshots/HTML cannot prove hidden behavior;
  `unresolved_gaps` blocks ready Design, Quick, task, worker, or Review claims.
  Quick may perform a bounded read-only continuity preflight before its Decision
  Checkpoint, then digest-binds and packetizes the same contract.
  Executable continuity routes the live session inventory through the runtime-owned
  adapter Bridge, embedded provider catalog, Probe, and Plan, then compiles one
  bounded execution packet per selected adapter. Observations, Lab reports,
  Formal acceptance, and Quick `item-accept` bind the exact inventory/probe/plan/
  execution chain; no packet may contain command, argv, env, script, or install
  fields. Formal target snapshots use current `expected_write_scope` with
  legacy `write_scope` only as fallback; Quick uses confirmed item
  `write_scope`. Both exclude runtime-owned workflow roots and Source Continuity
  outputs and remain byte-stable until an in-scope product source changes. Do
  not add `source-continuity` artifacts to product or
  execution-guard scope as a recovery workaround; explicit runtime-owned scopes
  are invalid.
- The single current UI contract separates work type, surface type, and platform. It preserves
  subject, audience, single job, visual/content/interaction theses, a signature
  element, an inspectable approved visual reference, per-reference use intent,
  task-relevant real-content/image plans, approval digests, decision and handoff
  contract subsets, a stable `surface_catalog`, a bounded risk-based or pairwise
  `scenario_matrix`, an exact `editing_matrix`, color modes, component contracts, responsive and motion
  rules, visual acceptance rows, comparison tolerance, and approved deviations
  through the Classic and Advanced artifact chain. Every scenario binds one
  stable surface to the exact interaction, editing, data, accessibility, navigation,
  content, responsive, and motion rows exercised together and carries an exact
  `interaction_script` with preconditions, a selected start-state ID, ordered
  input/action/feedback steps, and bounded state branches for applicable
  success, failure, timeout, cancel, retry, duplicate, and out-of-order outcomes.
  Every branch target is one of the scenario's selected data-state IDs and
  preserves setup, feedback, focus behavior, announcement, and continuation,
  plus scenario-level focus/announcement/completion/recovery checkpoints.
  Interaction rows are exact input-mechanics contracts: `id`, `surface`,
  `input`, `trigger`, `event_sequence`, `immediate_feedback`, `focus_behavior`,
  `repeat_behavior`, `cancellation_behavior`, `pending_behavior`, and
  `decision_ids`. They preserve platform event ordering, pre-completion
  feedback, focus/selection/scroll continuity, repeated activation rules,
  cancellation, and allowed or blocked pending actions; scenario scripts own
  journey outcome branches rather than duplicating those mechanics.
  Editing rows preserve input methods, IME composition, paste/autofill,
  selection/caret, formatting, validation timing/feedback, dirty state,
  persistence, undo/redo, edit conflict, read-only/disabled, and submission
  behavior; scenarios bind them through exact `editing_ids`.
  Scenarios cover all
  selected rows without an unbounded Cartesian product. Downstream stages
  select immutable `DS-*`/`DH-*` rows by ID; they do not reauthor them as prose.
  Do not collapse those dimensions into one enum or prose.
### Implementation Evidence and Regression Coverage

- A feature `ui-target.html` is a self-contained composition/state target bound
  to the exact registered design-change and handoff digests, task decisions, and
  handoff contracts. It may contain
  bounded review-only interaction JavaScript, but no network calls, persistence,
  production data access, external runtime dependency, or replacement approval
  authority for the change-level preview.
- UI implementation system review requires a real-entrypoint convergence loop
  before human acceptance:
  run, capture representative viewport/state evidence, visually inspect against
  design/brief/reference inputs, repair drift, and recapture. Passing automated
  tests is separate from visual and interaction acceptance; unavailable visual
  comparison remains explicit `pending-human-review`.
- UI task lifecycles use only typed `structure_snapshot`, `visual_capture`, and
  `runtime_diagnostics` evidence plus visual comparison or human review. Web
  maps those kinds to accessibility/DOM structure, viewport screenshots, and
  console/runtime output. Integrated lanes must recapture them with
  `evidence_scope: integrated`; isolated task evidence cannot close the lane.
- A passing visual comparison requires a hashed
  `spec-kit-visual-comparison-v1` report bound to the approved visual reference,
  exact design-change ref/hash, approval digests, exact task decision set,
  implementation captures, viewport/state matrix, comparison tolerance, and
  approved deviations.
  Unavailable or incomplete comparison remains `pending-human-review`; automated
  tests or unbound screenshots cannot substitute for this report.
- Stateful source reconstruction preserves applicable `component_states`
  (behavior and per-part visual expectations), `state_variants` (complete
  source/target resource states and dimensions), and `native_operation`
  (native API, permission declarations, and observable effect). Keep their
  complete source denominators in task and adapter packets and revalidate
  detailed evidence at Lab and lifecycle acceptance; a generic PASS or unrelated
  metadata change cannot prove a missing visual state or native effect.
- UI contract versions are not a compatibility surface. Do not emit or accept
  `ui_contract_version`, `contract_version`, `ui_fidelity_requirements`,
  `ui_fidelity_evidence`, lifecycle `evidence_refs`, or legacy evidence-kind
  aliases. Regenerate stale UI artifacts into the single current contract.
- A UI workflow change must evaluate `templates/design-change-template.md`,
  design CLI change/register and
  readiness behavior, Classic command/partial/passive/worker surfaces,
  Advanced shared and owning skill references/assets, spec/plan/task machine
  contracts, `execution/packet_compiler.py`, lifecycle closeout, integration
  rendering, and cross-profile tests. Keyword-presence tests alone do not prove
  UI contract continuity; include at least one structured
  task-index-to-worker-packet test.
