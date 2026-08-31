# UI quality gate

Read this reference only when work changes a user-visible screen, component,
layout, navigation or interaction flow, responsive behavior, visual state,
desktop/mobile surface, TUI layout, or CLI presentation. UI work does not
require an external screenshot to trigger this gate.

Use the deterministic `design profiles` capability catalog for substantive
design work. `no-ui` is valid only with current evidence of no user-visible
presentation; record `design_system_status: not-applicable` and skip the visual
artifact chain. Do not use `no-ui` to downgrade a content, CLI, TUI, mobile,
desktop, or Web presentation surface.

## Design readiness

Run `specify-runtime design resolve --scope <exact-surface> --format json`, then
query metadata-only `.specify/design/index.json`, select an applicable
registered `UD-*` change, and inspect that exact change-local `design-change.md`
through `specify-runtime artifact show` together with relevant live surfaces.
Resolution is discovery only. Split composite coverage into explicit bindings.
Because current consumer binding artifacts are singular, the split must produce
independently bound consumer units rather than one worker blending contracts.
Never resolve "latest" and never use an unregistered root design document as
workflow input. Route a new product surface, redesign,
rebrand, shared component-language change, or unresolved visual direction to
`$spx-design`. A narrow existing-pattern fix may continue only when the live
governing tokens/components and affected states are clear.

Avoid generic defaults that are not grounded in product purpose or current
language. Separate work type from surface type (`landing`,
`product-workspace`, `hybrid`, `existing-pattern-maintenance`) and platform.
Name subject, audience, single job, visual/content/interaction theses, and one
recognizable signature. Apply the surface-aware anti-slop policy from
`design-library/anti-slop-policy.md` only as a bias correction subordinate to
the exact registered design change: landing/marketing favors higher variance
and bans common AI-hero fingerprints; product-workspace favors density and bans marketing
theatrics; trust-public favors restraint and real design-system foundations.
This gate never authorizes production implementation inside design workflows.
New or high-visibility direction requires an
inspectable approved visual reference; a narrow existing-pattern exception must
name its live governing surface. Reuse approved tokens and components.
Resolve `style_authority` before professional routing. Existing-product feature,
component, and partial functional-page work uses `inherit-existing`, records
exact live token/theme/component/surface refs, protects `global-shell` and
`shared-components`, allows no style-delta surfaces, and keeps the style skill
null. `page-overhaul-authorized` requires explicit user authorization for one
exact complete page; only that page may appear in
`allowed_style_delta_surfaces`, while shell/shared components stay protected.
Adding or refactoring one function page does not authorize a new visual
language. `greenfield` requires evidence that no live UI style applies.
For substantive create/refine, read
`.specify/templates/ui-professional-skills/router.md` and preserve the resolved
`professional_skill_route`: `domain_skill_id`, `style_skill_id`,
`specialist_skill_ids`, `matched_signals`, `loaded_refs`, and Web-only
`mature_web_ui_resource_ids`, `web_ui_asset_inventory`, explainable
`mature_web_ui_selection`, deterministic component adoption/permission rows,
read-only selected-official-resource refresh results,
`smoothness_acceptance_ids`, and performance budgets. Pass the actual
project root for the bounded read-only asset scan. Load only the selected one domain, zero-or-one
style, and zero-to-two specialists. For Web component work, use the
router-triggered mature-component selection reference: prefer compatible live
components, then one mature primary system, and only exact headless/specialist
gaps; retrieve official Agent material only for shortlisted selections. Never
load the full UI professional skill catalog or blend conflicting style skills.
Pass `style_authority` to the router; `inherit-existing` suppresses style refs
without suppressing domain or specialist quality guidance.
Approved references, registered design truth, platform rules, and accessibility
constraints take precedence. Image-primary and html-primary authoring consume
the same sparse route through separate prompt contracts.
For Quick adoption, stage exact `scope`, `design_change_id`,
`design_change_ref`, `design_change_sha256`, and `design_contract_ref` as
confirmation-protected `decision.ui_confirmation.design_binding` before
confirmation. Only afterward, use a fresh leased
`specify-runtime artifact patch` call to set the independent top-level
`STATUS.md` `ui_design_binding` adoption copy; both copies must exact-match
before `specify-runtime design adopt` may succeed.
For a replacement, first run `specify-runtime design diff`, then the read-only
`specify-runtime design impact <consumer-ref> ... --expected-change
<CURRENT-UD-ID|none>` preview. Present `preserved_bindings`,
`invalidated_bindings`, and `reconcile_from`; only a matching adoption receipt
may trigger scope-bounded reconciliation. Preserve completed work and
unaffected Review evidence. Quick retires unstarted affected packets and
creates a corrective work item for completed-work drift.
For a Design created after a planning-ready feature spec, preserve that source
spec's exact bytes and SHA-256, adopt with `--mode formal-post-specify`, and
verify it using `specify-runtime design adoption`. Plan consumes this late
overlay directly: specify -> design -> plan must not require a second Specify.
Only a real requirements, scope, or acceptance change returns to Specify.
When `sp-design` produced a change-level visual round, preserve its exact
change-local `round-NN.<html|png|jpg|jpeg|webp>#direction-id` reference, registered design-change
ref/hash, motion/reduced-motion contract, preview/manifest/handoff SHA-256
values, immutable handoff ref, approved `DS-*` decision IDs, and applicable
`DH-*` handoff contract IDs.
Do not replace them with a prose summary or the later feature target.

## Source continuity gate

When an interface is reconstructed, migrated, adapted, or completed from one or
more prior products or references, preserve a structured `source_continuity`
contract. This is technology-neutral and may combine screenshot/recording,
HTML/design export, live source UI, source code/resources/tests, runnable source
runtime, requirements, and business evidence. Assign each input a bounded
authority role: pixels do not prove hidden surfaces or behavior, source does
not prove reachability, and a compiled target does not prove the user promise.
Preserve `schema: spec-kit-ui-source-continuity-v1`, `applicability`, `mode`,
`reason`, the complete `coverage.surface_ids` / `interaction_ids` /
`component_ids` universe, and stable `authority_refs` before the binding
arrays. Each coverage set must exactly equal its binding targets; a sampled
subset cannot close a larger discovered scope.

Executable delivery proves this contract through Source Continuity Lab. For a
formal task run `specify-runtime evidence source-continuity-manifest
--feature-dir <feature-dir> --task-id <Txxx>`; for Quick use `--quick-id
<quick-id> --item-id Qn`. Inspect the live session tool inventory and pass only
tool refs, generic signals, roles, execution mode, and availability to
`source-continuity-adapter-bridge`. The Bridge maps signals through
`source-continuity-adapter-catalog` and owns inventory, Probe, and Plan.
`source-continuity-adapter-probe` and `source-continuity-adapter-plan` remain
progressively lower-level fallbacks. Compile the exact Plan through
`source-continuity-adapter-execution`; execute only its packet actions, targets,
evidence requirements, permissions, preconditions, and stop conditions.
Evidence records use provenance `adapter:<adapter_id>`; each
observation row names its adapter and binds the returned plan ref/digest plus
composite adapter. After independent source/target discovery and matched
execution, submit observations through `specify-runtime evidence
source-continuity-validate` with `--manifest <manifest-ref> --adapter-plan
<adapter-plan-ref> --adapter-execution <adapter-execution-ref>`. Carry the returned exact coverage,
`source_continuity_adapter_plan_ref`/SHA-256 and
`source_continuity_adapter_execution_ref`/SHA-256 and
`source_continuity_lab_report_ref`/SHA-256 into `ui_verification`. The
runtime-owned report, not the Agent-authored coverage list, owns the PASS claim.

- Discover the in-scope surface/state graph beyond the starting screen,
  including deep routes, menus, dialogs, alternate triggers, shortcuts,
  dynamic views, error/recovery paths, permissions, pending/cancel/repeat, and
  persistence where applicable.
- Preserve `surface_bindings` with one explicit source-target disposition per
  row: `preserve`, `adapt`, `replace`, `merge`, `split`, or `retire`. Retirement
  requires evidence and intent; it is not a label for unexplored scope.
- Preserve `action_bindings` from user input and source route through the domain
  operation as exact `interaction_id`, `source_refs`, `user_promise`,
  `business_outcome`, `side_effects`, `final_state`, and `verification` fields.
  Linked interaction/scenario rows own feedback and recovery. A component or
  handler existing is not end-to-end proof.
- Preserve `asset_bindings` for icons, imagery, fonts, sounds, and other
  identity-bearing resources using exact `component_id`, `semantic_role`,
  `source_refs`, `target_strategy`, `target_ref`, `provenance`, `fallback`, and
  `placeholder_policy: forbid-character-substitution`. Unicode, emoji, ASCII,
  or arbitrary characters cannot substitute for missing icons or images.
- Preserve `unresolved_gaps` as strings that name category, affected scope,
  owner, exact next discovery action, and blocking effect. Ready source-continuity truth has no
  open gap capable of hiding a surface, promised action, business outcome,
  final state, asset, or unsafe evidence conflict.

For source controls with distinct states, bind
`surface_bindings[].component_states` to exact component anatomy/required
states; each state separates `behavior` from per-part `visuals`. Disabled
semantics cannot prove disabled label/indicator/icon appearance. Source image
variants require `asset_bindings[].state_variants` with complete state coverage,
source/target refs and `[width,height]` sizes; `preserve` keeps dimensions equal.
Variant mappings exhaust the full source resource inventory and component
states; deleting the same state from declarations and results cannot shrink scope.
Native actions require `action_bindings[].native_operation` with the platform
API, explicit permission requirement/refs/reason, and observable effect.
Use the matching nested Lab result details, typed state captures, and native
runtime evidence with before/after state objects. Declare
`effect_requirement: state-change|observation` and exact scalar `effect_fields`;
compare only those fields, all present on both sides, with numeric rather than
textual equality. Unrelated timestamps cannot prove window movement.
Observation mode requires no promised side effects and cannot downgrade drag.
Never infer native
operation from a DOM marker or browser-only preview. Omit these optional
details only for static/non-native sources; unknowns block through
`unresolved_gaps`. Adapter `binding_targets` preserves the applicable state
and asset-variant targets without executable commands or another workflow.

Detailed result shapes: `surface_results[].component_states[]` carries
`component_id`, `state`, `behavior_matches`, `behavior_observation`,
`behavior_evidence_ref`, and `visuals[{part,matches,observation,
source_evidence_ref,target_evidence_ref}]`;
`asset_results[].state_variants[]` carries `state`, source/target `_ref` and
`_size`, source/target `_evidence_ref`, `render_match`, and
`character_substitution`; `action_results[].native_operation` carries `api_ref`,
`verified_permission_refs`, `permission_evidence_ref`, `effect_evidence_ref`,
`before`/`after` objects, and `effect_matches`. State-change requires a change
in a declared effect field. Match flags are booleans;
character substitution is false. Behavior/native refs use target runtime
diagnostics; visual refs use matched source/target visual captures.

Design may discover and approve this contract but remains design-only and must
not write target code or claim runtime parity. Quick may own full direct
delivery when its confirmed checkpoint binds the applicable continuity subset;
source depth, migration breadth, and surface count increase task-local planning,
lanes, and evidence rather than forcing a formal-spec handoff. Escalate to
Design only when a new or unresolved visual direction needs approval. Every
implementation packet receives its exact surface/action/asset bindings. Review
runs matched scenarios through source and target real entrypoints when the
source is runnable, with equivalent safe data, and separately verifies visual
fidelity, reachability, feedback, side effects, `business_outcome`, and
`final_state`. If the source cannot run, use the strongest remaining authority
and explicitly withhold the parity claim.

## Delivery chain

For substantive UI work preserve one contract through the workflow:

`registered change-local design-change.md + approved preview/approval/handoff sidecars + original references -> ui-brief.md -> plan ui_design_contract -> task ui_contract -> comparison report + real-entrypoint evidence`

The UI brief is required for substantive UI work even without external
references. It identifies entry points, required states and viewports,
must-preserve/may-adapt/must-not decisions, responsive/accessibility rules, and
visual acceptance evidence. Preserve the approval hashes, required design and
handoff contract IDs, component anatomy, color modes, motion contract,
`style_authority`,
component interaction modes, interaction rows, component data scenarios,
viewport/state matrix, resize/stretch/overflow behavior, capability profile and
specimen IDs, and real content/image plans. Each UI task carries only its
applicable decision subset; all UI tasks together must cover the plan's
required set.
Preserve `surface_catalog` as the stable inventory of implemented UI surfaces,
with one exact official `entrypoint_id`, source/specimen/component references,
and exact decision bindings. Missing, unknown, or ambiguous entrypoint bindings
block real-entrypoint evidence rather than falling back to another runnable
surface. Preserve
`scenario_matrix` as the bounded execution graph: each required, risk-labelled
scenario references one `surface_id` plus the exact interaction, data,
editing, accessibility, navigation, content, responsive, and motion rows exercised
together. Each scenario also preserves an exact `interaction_script` with
non-empty `preconditions`, a `start_state_id` selected by `data_state_ids`,
ordered `steps` (`input`, `action`, `expected_feedback`), and bounded
`branches`. Each branch has unique applicable `conditions` from success,
failure, timeout, cancel, retry, duplicate, and out-of-order completion; its
`expected_state_id` must be one of the same scenario's data states and it keeps
setup, feedback, focus behavior, announcement, and continuation explicit.
Also preserve non-empty `focus_checkpoint`,
`announcement_checkpoint`, `completion_checkpoint`, and `recovery_checkpoint`.
Scenarios collectively cover every referenced row and each
scenario's `decision_ids` equals the union of those rows. Use risk-based or
pairwise selection, never an unbounded Cartesian product.
Carry interaction and data truth structurally, not as prose only: preserve
`interaction_matrix` rows for pointer/mouse, keyboard, focus, touch, shortcuts,
command/system events, and async feedback. Each row uses exact `id`, `surface`,
`input`, `trigger`, `event_sequence`, `immediate_feedback`, `focus_behavior`,
`repeat_behavior`, `cancellation_behavior`, `pending_behavior`, and
`decision_ids`; it owns input mechanics while the scenario script owns journey
outcomes. Add explicit rows for rapid/repeated activation,
duplicate submission, drag cancellation, async completion order, timeouts,
navigation/reload/close, session expiry, and external updates when they can
lose work or duplicate effects. Preserve `data_state_matrix` rows for
empty/first-use, populated representative and maximum-density data, loading,
partial/stale/refreshing, validation/error, permission/read-only,
offline/unavailable, optimistic/pending, and success conditions as applicable;
every data-bearing surface includes both empty and populated. Preserve component
rows with `interaction_modes` and `data_scenarios`; preserve responsive rows
with `stretch_behavior` and `overflow_behavior`, including continuous
stretch/compression/reflow while focus, selection, scrolling, dragging, an
overlay, or unsaved input is active. Stress long/localized content, text zoom
or scaling, software keyboards, safe areas, high contrast, and reduced motion
when applicable. Use risk-based or pairwise input × data × size combinations
rather than an unbounded Cartesian product; never let a populated pointer happy
path substitute for keyboard, recovery, or resize evidence.

Preserve `editing_matrix` rows through exact scenario `editing_ids`. Each row
uses `id`, `surface`, `input_methods`, `composition_behavior`,
`paste_autofill_behavior`, `selection_caret_behavior`, `formatting_behavior`,
`validation_timing`, `validation_feedback`, `dirty_state_behavior`,
`persistence_behavior`, `undo_redo_behavior`, `conflict_behavior`,
`read_only_disabled_behavior`, `submission_behavior`, and `decision_ids`.
Cover IME composition without premature validation, paste/autofill
normalization, caret and selection preservation, formatting boundaries,
inline and announced correction, visible dirty state, draft/autosave/reload,
native or application undo/redo, edit conflict resolution, selectable
read-only values, explained disabled controls, and Enter/shortcut/pending/
failure/retry/duplicate submission behavior.

Preserve the professional contract under `design_change.verification` and in
every exact downstream subset: `surface_catalog`, `scenario_matrix`,
`editing_matrix`, `accessibility_matrix`, `navigation_matrix`, `content_matrix`,
`motion_contract`, and `usability_validation`, alongside `interaction_matrix`
and `data_state_matrix`. A top-level accessibility summary
does not replace `accessibility_matrix`.

- Accessibility rows carry `id`, `surface`, `semantics`, `reading_order`,
  `focus_order`, `keyboard`, `announcements`, `target_size`, `contrast`,
  `zoom_reflow`, `alternatives`, and `decision_ids`. Target WCAG 2.2 AA or
  platform equivalent; verify Name/Role/Value, logical reading order and focus
  order, visible focus, keyboard alternative and drag alternative, dynamic
  status announcement, applicable 24x24 (24×24 CSS px) Web and 44pt native
  targets,
  4.5:1/3:1 contrast, 400% reflow/zoom, forced colors/high contrast, and
  image/icon alternatives.
- Navigation rows carry `id`, `surface`, `entry`, `destination`, `trigger`,
  `back_behavior`, `deep_link_behavior`, `interruption_recovery`, and
  `decision_ids`. Cover hierarchy, entry and primary task, back/close, deep
  link behavior, interruption recovery, consistency, landmarks, and task-state
  preservation.
- Content rows carry `id`, `surface`, `state`, `purpose`, `copy`,
  `primary_action`, `trust_requirement`, `localization`, `content_limits`, and
  `decision_ids`. Cover CTA, empty/loading/error/permission, destructive
  action, confirmation, undo/recovery, privacy/trust, long copy and truncation,
  right-to-left (RTL)/bidirectional layout, localization, and locale-aware date,
  number, currency, and time zone output.
- Component rows additionally preserve `variants`, `content_constraints`,
  `semantic_token_refs`, reuse/extend/new `governance`, gap/deprecation
  ownership, and `iconography` source, family, sizing, and optical alignment.
  `semantic_token_refs` bind semantic token references rather than one-off
  values; iconography also records semantics and fallback.
- `motion_contract` preserves purpose, transition trigger/response,
  `duration_ms`, easing, interrupt/cancel behavior, reduced-motion alternative,
  and perceived-performance threshold values for immediate feedback, progress,
  and timeout.
- `usability_validation` preserves risk, methods, critical tasks, success
  criteria, `human_review_required`, and applicable routed
  `smoothness_acceptance_ids` plus performance budgets. Those IDs bind through
  the CLI-owned Smoothness Lab report to the existing structure,
  visual, runtime, and visual-comparison-or-human-review evidence kinds; they
  do not create another evidence kind. Acceptance revalidates the canonical
  manifest, current task-index digest, exact entrypoint, typed evidence triad,
  complete scenario coverage, and performance budgets; a handwritten or
  reduced report is not acceptable. Low-risk existing-pattern changes may
  use a documented cognitive walkthrough or heuristic review. Medium/high-risk
  journeys require representative target users and human review. Automated
  tests and screenshots cannot substitute for target-user usability.

Use risk-based or pairwise coverage rather than an unbounded Cartesian product;
retain every high-severity accessibility, trust, recovery, and usability path.
When references
exist, keep the original inspectable assets and assign each a use intent; prose
alone is not a fidelity source. Default reference fidelity is
`approximate`; `high` requires comparison and a difference/deviation record.
Treat third-party source as evidence, not a license to copy protected brand,
artwork, trade dress, or proprietary implementation.

## Implementation acceptance

Do not stop at code correctness. Query the task's exact
`design_change_ref`/`design_change_sha256`, its exported
`design_contract_ref`, and the feature UI brief through targeted
`specify-runtime artifact show` calls; verify those values against the
metadata-only index, then run the real entry point and capture the required
representative viewport/state matrix. Inspect it against those returned sections, the
brief, prior surfaces, and original references, fix concrete drift, then
recapture. Submit the observed entrypoint/revision, typed evidence refs, matrix
rows, structural/visual differences, covered decision/handoff IDs, explicit
verdict, and reviewer through `specify-runtime evidence visual-compare`; the CLI
derives and owns the approved bindings, tolerance, accepted deviations, report,
path, and digest. For web UI also check overflow, console errors, keyboard/focus, and
accessibility when applicable. For mobile include safe areas, touch targets,
platform navigation, and device states; for desktop include resize, high-DPI,
keyboard shortcuts, and window states; for TUI include representative terminal
widths, color fallback, and non-color state cues; for CLI include help/error
clarity, stable human text, machine-readable output, actionable recovery, and
localization where supported. Persist the platform-neutral evidence triad:
`structure_snapshot`, `visual_capture`, and `runtime_diagnostics`, plus
`visual_comparison_or_human_review`. For web these mean accessibility/DOM
snapshot, viewport screenshot, and console/runtime output. Tests passed and
visual acceptance are separate claims.

For approved motion, exercise the named entrance, feedback, loading, and state
transition moments at the real entry point and verify the reduced-motion
equivalent. Keep this evidence within the existing structure snapshot, visual
capture, runtime diagnostics, and comparison/review kinds rather than inventing
a parallel motion-evidence schema.

If visual comparison is unavailable, record `pending-human-review` and the
exact evidence/decision needed. Never claim visual match from prose, component
tests, or source inspection alone.

## Design Intelligence

Horizontal Design Intelligence Engine for every UI-bearing stage: **Taste
Intelligence** + **Design System Reverse Engineering** + **Visual Validation**.
Not a new mainline command. Reuse design-brief dials (`variance` / `motion` /
`density`), `design_read`, anti-slop locks, and the exact registered design
change—do not invent a second parameter system or approval authority. UI is a design-system
modeling problem: Evidence → System → Implementation. Prefer tokens, components,
states, and responsive rules over one-shot page clones.

### Taste DNA and dials

Record or inherit design personality (feeling/tone, what to avoid), one-line
`design_read`, dials 1-10 with inference reason, surface type, and active
anti-slop locks before generating or materially changing UI.

### Evidence Level and UI System Model

This SPX file is an **install surface**, not a second rule book. Durable
contracts live in shared Design Intelligence schemas:

- DesignContext v1:
  `templates/design-intelligence/schema/design-context.schema.json`
- Design Evidence v1:
  `templates/design-intelligence/schema/design-evidence.schema.json`
- Lifecycle / paths: `templates/design-intelligence/ARTIFACT-LIFECYCLE.md`
- Capability matrix: `templates/design-intelligence/CAPABILITY-MATRIX.md`

Reverse-engineered claims use Design Evidence v1: `measured` | `inferred` |
`assumption` (alias `evidence-backed-inference` → `inferred`). Non-measured
requires rationale; inferred requires source or explicit source_gap. Validate
with `validate_design_evidence` / `validate_design_context`. Model UI as pixel /
system / behavior / engineering layers: tokens, components, state matrix
(including hover/focus/loading/empty/error), responsive rules, and
keyboard/behavior. Bind into
`.specify/design/changes/<UD-ID>/design-change.md` and its change-local exported
`design-contract.json`—not a global design document or parallel root
`.design/` tree.
Optional executable reports use
`ui-quality-gate-report.schema.json` and
`run_ui_quality_gate_rules` without replacing design approve.

### Stage hooks

- **Discussion — design discovery**: when UI is involved, capture durable
  `design_context` (not chat-only): `ui_involved`, `feeling_tone`, dials or
  deferred nulls, reference products/intents, information density, interaction
  complexity, anti-slop locks, whether UI Evidence Analysis is needed, and
  whether `$spx-design` is required. Persist in Design Carry-Forward and handoff
  `discussion_decision_digest.design_context`.
- **Design — reverse engineering**: on synthesize or live refine, extract
  tokens/components/states/responsive with evidence levels before boards;
  approve only through design approve/export, then freeze consumer truth through
  design register.
- **Specify — UI Requirements + acceptance**: layout pattern; design-system
  token/component use; required states (loading/empty/error/success/disabled/
  focus); required interaction/event paths; data-state scenarios; responsive
  targets including resize/stretch/overflow behavior; quality (no generic
  dashboard/template; maintain DNA/dials); visual evidence kinds.
- **Test Design — UI coverage obligations**: enumerate accessibility,
  responsive, viewport/state, interaction, motion, and visual-comparison cases
  plus their data and evidence needs. Do not implement tests, run captures, or
  substitute a test-design audit for real-entrypoint review evidence.
- **Quick — UI Audit then design-before-code**: UI Audit issue list first →
  analyze → identify issue → propose before/after → implement → visual check.
  Do not jump straight to code edits.
- **Debug — UI Debug Mode**: classify visual/layout (spacing, alignment,
  overflow, responsive), UX/interaction (unclear action, hover/focus/keyboard,
  loading/empty/error), or taste/generic-look. Name issue, reason, and
  design-aware fix before coding.
- **Implement / Review**: query the task's exact registered design change + UI System Model + anti-slop +
  task `ui_contract` before UI generation; prefer visual hierarchy over
  equal-weight card grids; visual validation loop
  (capture → compare → fix → recapture) or `pending-human-review`.
