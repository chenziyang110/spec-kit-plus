# UI design-change contract

Use `.specify/design/changes/<UD-ID>/DESIGN.md` as the immutable visual and
interaction delta for its declared scope. Ground it in live product surfaces,
accepted baseline refs, and confirmed references. The metadata-only
`.specify/design/index.json` resolves candidates and relationships; it is not
design truth. A root `DESIGN.md` is a read-only legacy baseline.

Include only applicable decisions:

- product subject, audience, single user job, and surface/platform fit;
- visual, content, and interaction theses; one recognizable signature; safe
  system choices; and deliberate creative risks with gain/cost;
- color, type, spacing, elevation, motion, iconography, and density tokens;
- component anatomy, variants, states, composition, reuse rules, exact
  `interaction_modes`, and `data_scenarios`;
- an `interaction_matrix` for applicable pointer/mouse, keyboard/focus, touch,
  shortcut, command, and system events, with exact event sequence, immediate
  feedback, focus, repeat, cancellation, and pending behavior;
- an `editing_matrix` selected by scenario `editing_ids` for input methods,
  composition, paste/autofill, caret/selection, formatting, validation, dirty
  state, persistence, undo/redo, conflict, read-only/disabled, and submission;
- a `data_state_matrix` covering empty and populated representative/maximum
  density for every data-bearing surface plus applicable loading, partial,
  validation/error, permission/read-only, offline/unavailable, pending, and
  success behavior;
- responsive targets plus continuous stretch/compression/reflow,
  `stretch_behavior`, and `overflow_behavior`, including active interaction;
- accessibility semantics, focus, contrast, input, and reduced-motion behavior;
- reference fidelity and later visual evidence requirements.

Before locking a new or materially changed direction, complete durable taste
intake in the design brief (`design_read`, variance/motion/density dials with
inference reason, aesthetic family, foundation strategy, redesign mode when
applicable, anti-slop locks, and synthesize reference-board intents when used).
When screenshots, live UI, or other references are present, run **UI Evidence
Analysis** first: surface/page map, candidate tokens/components/states/
responsive rules, each claim tagged
`measured` | `evidence-backed-inference` | `assumption` with a reason when not
measured. Build the **UI System Model** (pixel/system/behavior/engineering
layers) before treating any single page clone as the design. Prefer system rules
over one-shot page generation.
Then query design profiles through the design CLI, select one or more visual
capability profiles, generate `round-NN.manifest.json` with
`specify-runtime design preview-manifest --profiles ...`, and render it with
`specify-runtime design preview --manifest` as an unfinished freeform shell.
Author the project-specific HTML/CSS for one current concept in
`#direction-main`; the seed is never review-ready. The profile registry
determines required capabilities, input modes, units, specimens, state
obligations, and presentation targets for Web, mobile, desktop, CLI, TUI, and
content-led surfaces. One numbered HTML round holds exactly one concept and its
comparison baseline. Keep it self-contained and framework-neutral. Modern CSS
and bounded inline review behavior may express meaningful interaction and
animation, but the artifact must not load remote code/assets, persist data,
call a network, simulate business logic, or claim to be production
implementation.

For refine/audit of live UI, audit before mutate: classify `preserve` vs
`overhaul`, extract brand tokens and signatures to keep with evidence levels,
list AI-slop drift to retire, and never treat design-library seeds or anti-slop
policy as approval truth.

Persist the exact `style_authority` alongside the professional route. Local
feature and partial-page contracts use `inherit-existing`, inherit the live style, and protect
`global-shell` plus `shared-components`; a style skill cannot override them.
Only user-authorized exact full-page overhaul scope may declare
`page-overhaul-authorized`, allowed style-delta surfaces, and its approval
source. Carry this structure unchanged into every downstream UI contract.

For Web UI, retain the router's `mature_web_ui_resource_ids` shortlist,
`web_ui_asset_inventory`, `mature_web_ui_selection`, its exact component
adoption and official-resource refresh records, and
`smoothness_acceptance_ids` plus performance budgets. Final selection requires a scanned live project;
provisional scores or refresh results cannot authorize dependency changes.
Component contracts prefer inspected live components and documented
extensions; select one compatible mature primary system and only
capability-justified headless or specialist support. `governance: new` requires
a recorded gap. Every affected component contract copies the exact nested
adoption action/package/version/license/source/permission row. Official Agent,
MCP, or LLM material is retrieval input for a
selected candidate, not dependency, license, upgrade, or migration authority.

The current concept defines motion purpose plus duration, easing, distance or
spatial behavior, and a `prefers-reduced-motion` equivalent. Present it in a
real browser at the applicable target viewports and states. Ask the user what
to preserve and what to change; if it is not satisfactory, incorporate that
feedback into the same direction in a new immutable round. Approval identifies
the exact round path and `direction-main`. Freeze it only after explicit user
approval with
`{{specify-subcmd:specify-runtime design approve <round-path> --direction <direction-id> --format json}}`;
the resulting approval sidecar, selected-direction handoff sidecar, preview
SHA-256, manifest SHA-256, handoff SHA-256, review round, approved decision IDs,
and handoff contract IDs are the approval truth. Carry those values unchanged
with capability profile and specimen IDs through the exact change-local
`DESIGN.md`, the feature UI
brief, plan/task UI contracts, and final
visual comparison. A verbal hybrid is not approvable; render it as a new
direction in a new immutable round.

For a new or high-visibility direction, persist an inspectable approved visual
reference in `approval.visual_refs`. Assign each source an explicit use intent;
reference intent and fidelity are separate decisions. Use real product content
and owned/licensed imagery plans instead of lorem ipsum or decorative
placeholders that mask layout risk.

Name existing implementation owners and planned gaps without pretending a
planned token or component already exists. When auditing, cite concrete live
surfaces and distinguish contract drift from intentional exception. Avoid
generic aesthetic prose that cannot guide or verify downstream work.

The embedded preview manifest and visible specimen must agree. Canonical
`DS-<KIND>-NNN` decisions cover color, typography, spacing, component anatomy,
motion/reduced motion, responsive adaptation, and representative content as
applicable. Each decision names its source, affected surfaces, implementation
token or owner, and verification method. Export the approved `DESIGN.md` to
`.specify/design/changes/<UD-ID>/design-contract.json`, then run
`specify-runtime design register <change-dir>/DESIGN.md`. Downstream work
consumes that stable shape and registered digest instead of re-authoring the
design from prose.

The visible handoff section is part of approval, not explanatory footer text.
It preserves the complete capability model and assigns stable `DH-*` IDs to
implementation bindings, component anatomy and states, presentation targets,
and visual acceptance rows. Every approved `DS-*` decision, specimen, and
required state must be covered. `design approve` deterministically
projects the selected direction into `round-NN.handoff.json`; downstream
artifacts reference its digest and select `DH-*` IDs instead of rewriting its
meaning.

The current concept must demonstrate the required interaction, data, and size
scenarios so feedback is grounded in behavior rather than one attractive
default-state screenshot. Use risk-based or pairwise input × data × size
combinations rather than a Cartesian explosion, but include resize during
active focus, selection, scrolling, dragging, overlays, or unsaved input when
those risks exist. A static populated pointer state cannot stand in for
keyboard, empty/error recovery, or continuous resize behavior.

`no-ui` is an explicit applicability result, not a specimen. It requires current
evidence and `design_system_status: not-applicable`; it cannot be combined with
a visual profile and must not enter preview, approval, handoff, `ui-target`, or
visual-comparison work.

The change-level design preview and feature-level `ui-target.html` are
different artifacts. The preview approves visual, component, state, density,
and motion decisions for the declared scope. The target later describes one feature
composition and cannot silently replace or weaken the approved preview
reference.

Each contract declares `scope`, `baseline_refs`, relationships (`iteration_of`,
`supersedes`, `depends_on`, `conflicts_with`), and Must Preserve / May Adapt /
Must Not boundaries. `design iterate` writes the successor's exact
`iteration_of`, index `basis_sha256`, digest-pinned baseline, and `supersedes`.
Every requested successor scope must still be active on that source; a scope
already covered by `superseded_scopes` must iterate from its active successor,
not from the stale parent.
Approved contracts are immutable. Registration subtracts only overlapping
successor scope into the parent's `superseded_scopes`; the parent remains
active outside those exclusions and becomes fully superseded only when every
declared scope root is covered.

## Professional UI contract continuity

For substantive UI, freeze complete `surface_catalog`, `scenario_matrix`,
`interaction_matrix`, `editing_matrix`, `data_state_matrix`, `accessibility_matrix`,
`navigation_matrix`, `content_matrix`, `motion_contract`, and
`usability_validation` values under
`design_change.verification`, plus component governance and iconography. Use
routed official entrypoint IDs as exact `surface_catalog[].entrypoint_id`
bindings; do not leave a multi-entrypoint consumer ambiguous. Use
routed smoothness IDs in the applicable interaction, motion, and usability
rows, using only the current evidence kinds. Use risk-based or pairwise scenarios rather than an unbounded Cartesian product;
automation/screenshots do not replace required target-user human review.
