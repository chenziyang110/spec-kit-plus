## Taste DNA and dials

Before generating or materially changing UI, record or inherit:

- **Design personality / DNA**: subject, audience, single job, feeling/tone
  (for example trustworthy · calm · sharp · dense), what to avoid.
- **`design_read`**: one line — kind / audience / vibe / foundation lean.
- **Dials (1-10)**: `variance`, `motion`, `density` with a short inference reason.
- **Surface type**: `landing` | `product-workspace` | `hybrid` |
  `existing-pattern-maintenance`.
- **Anti-slop locks**: surface-aware subset; never promote landing-only bans into
  project constitution.

When an applicable registered change is pinned, follow its tokens, components,
motion, and signature for that declared scope even if they conflict with
default anti-slop locks. When no applicable registered direction exists, route
new or high-visibility work through `sp-design`/`spx-design`.

## Anti-slop engine

Read surface-aware policy from `design-library/anti-slop-policy.md` (installed as
`.specify/templates/design-library/anti-slop-policy.md`). Defaults to avoid
unless the brief or approved design requires them:

- generic SaaS hero + three equal cards
- purple/blue AI gradient chrome without product grounding
- every control rounded the same with no hierarchy
- random or decorative motion
- empty decorative dashboard cards / placeholder metrics
- inventing a second design system beside the exact bound design change

## Stage contracts

### Discussion — design discovery + UI evidence intent

When UI is involved, run Design Discovery (optional pass, not a hard handoff
gate unless UI decisions block readiness). Capture durable **design_context**
(not chat-only):

- `ui_involved`: true | false | unknown
- `feeling_tone` / personality
- `dials`: variance, motion, density (or null when deferred)
- `reference_products` / reference intents
- `information_density` and interaction complexity notes
- applicable input modes, data-state boundaries, resize/overflow risks, and
  recovery expectations that need later `interaction_matrix` or
  `data_state_matrix` rows
- `anti_slop_locks` or surface default set
- `design_system_status` and whether `sp-design` is required next
- whether screenshots/live UI need **UI Evidence Analysis** before formal design

Persist into discussion Design Carry-Forward and, on handoff, into
`discussion_decision_digest.design_context` plus
`experience_commitments` / `design_system_requirements`. Prefer writing
machine-readable DesignContext under `.specify/design/context/` when durable.

### Design — reverse engineering + system studio

`sp-design` / `spx-design` owns create/refine/audit. On `synthesize` or live UI
refine: run Evidence → System before the current-concept board. Extract tokens,
components, states, and responsive rules as Design Evidence objects. Export
approved truth only through design approve/export into
`.specify/design/changes/<UD-ID>/DESIGN.md`, then make it consumable through
design register. The approved change records interaction and data-state rows,
the exact `accessibility_matrix`, `navigation_matrix`, `content_matrix`,
`motion_contract`, and `usability_validation`, component governance and
interaction/data scenarios, and continuous stretch/overflow behavior. Each
immutable concept round demonstrates meaningful component states and event
paths, not one static default-state screenshot.
Never implement production UI inside design.

### Specify — UI Requirements + acceptance / design DNA

For substantive UI work, specification must carry **UI Requirements** and
**UI Acceptance Criteria** (in `spec.md` Experience Requirements and/or
`ui-brief.md`):

- layout pattern and hierarchy; responsive targets
- tokens/components: use the exact registered design change selected for this
  feature (not ad-hoc or implicit latest)
- required states: loading, empty, error, success, disabled, focus (and hover
  when interactive)
- exact `interaction_matrix`, `editing_matrix`, and `data_state_matrix` rows, including empty and
  populated data for every data-bearing surface plus applicable partial,
  permission, offline, retry, undo, and recovery behavior
- exact `accessibility_matrix`, `navigation_matrix`, `content_matrix`,
  `motion_contract`, and `usability_validation` rows/objects, including any
  risk-owned target-user human review
- component `interaction_modes` / `data_scenarios`; responsive
  `stretch_behavior` / `overflow_behavior`, including active-focus and
  unsaved-input resize behavior
- quality: no generic dashboard/template pattern; maintain design DNA and dials
- evidence: structure_snapshot, visual_capture, runtime_diagnostics, comparison
  or pending-human-review

Never treat a legacy root contract as current approval direction.

### Plan / Tasks — architecture and packet continuity

Plan selects immutable interaction, data-state, accessibility, navigation,
content, motion, usability, component, responsive, and
visual-acceptance rows; it records the implementation and verification route
for each without weakening them into `required_states` prose. Tasks split only
by applicable row subset. Each UI task packet retains `interaction_matrix`,
`data_state_matrix`, `accessibility_matrix`, `navigation_matrix`,
`content_matrix`, `motion_contract`, `usability_validation`, component
`interaction_modes` / `data_scenarios` / governance fields, and
responsive `stretch_behavior` / `overflow_behavior`; all UI tasks together
cover the Plan set.

### Test Design — scenario coverage without combinatorial explosion

Freeze risk-based or pairwise cases across input × data × size. Cover declared
pointer/mouse, keyboard/focus, touch/shortcut/command paths; empty and populated
data plus applicable loading, partial, error, permission, offline, pending, and
success states; and continuous stretch/compression/overflow. Include high-risk
transitions such as retry, cancel, undo, navigation, or resize while focus,
selection, scrolling, an overlay, or unsaved input is active.
Also derive risk-bounded cases from `accessibility_matrix`,
`navigation_matrix`, `content_matrix`, `motion_contract`, and
`usability_validation`. Never expand the combined contract into an unbounded
Cartesian product or treat automation/screenshots as target-user validation.

### Quick — UI Audit then design-before-code

When the change is UI-bearing, do not jump to code. Run **UI Audit** then the
**Quick Design Loop**:

1. **UI Audit** of current UI: hierarchy, spacing consistency, missing states,
   generic/card patterns, DNA drift (issue list, not code yet)
2. Analyze current UI against the exact registered design change / brief / live surface
3. Identify the design issue
4. Propose improvement (before → after) against DNA/dials/anti-slop/system model
5. Implement the smallest coherent change
6. Visual check at real entry points (capture → inspect → fix → recapture)

UI Confirmation still binds user-owned experience decisions before substantive
implementation.
Quick preserves the affected exact subset of `interaction_matrix`,
`data_state_matrix`, `accessibility_matrix`, `navigation_matrix`,
`content_matrix`, `motion_contract`, and `usability_validation`; use risk-based
or pairwise coverage, not an unbounded Cartesian product.

### Debug — UI Debug Mode (layout / interaction / taste)

Classify UI symptoms into at least one issue class and record it in the session:

- **visual/layout**: spacing, alignment, overflow, responsive breakage
- **UX / interaction**: unclear action, weak feedback, confusing flow; missing
  or broken pointer/touch, hover, focus, keyboard, loading, empty, populated,
  partial, error, permission, offline, retry, undo, or recovery states
- **resize / reflow**: stretch/compression loses focus, selection, scroll,
  overlays, unsaved input, actions, or makes overflow unreachable
- **taste/generic-look**: template-like weight, no hierarchy, noise, anti-slop
  violation, DNA drift

Default-looking happy path is not enough—state matrix bugs count. Diagnosis
names issue, reason, and design-aware fix direction before coding.
Debug identifies the violated exact row in `interaction_matrix`,
`data_state_matrix`, `accessibility_matrix`, `navigation_matrix`,
`content_matrix`, `motion_contract`, or `usability_validation` and does not
rewrite approved truth. Reproduce risk-based scenarios rather than an
unbounded Cartesian product.

### Analyze / Checklist — contract quality without downgrade

Analyze checks continuity, contradictions, omissions, and ownership across
`interaction_matrix`, `editing_matrix`, `data_state_matrix`, `accessibility_matrix`,
`navigation_matrix`, `content_matrix`, `motion_contract`, and
`usability_validation`. Checklist asks whether each applicable professional
lens is specific, measurable, and traceable. Both remain read-only and use
risk-based prioritization rather than an unbounded Cartesian product.

### Implement / Review — system contract + visual validation loop

Before UI generation: query the task's exact registered design change + UI
System Model (tokens, components, states) + anti-slop + task `ui_contract`.
Prefer visual hierarchy from the contract over generic equal-weight card grids.
Exercise the declared event path and feedback/state transition, not only final
pixels. Capture empty and populated data plus applicable degraded/recovery
states and resize between named targets while relevant interaction state is
active. Close only with real-entrypoint evidence triad and visual comparison or
explicit `pending-human-review`. Review revalidates the bound design change,
anti-slop, interaction/data/resize coverage, and state fidelity; it never
invents a second approval authority.
Implement and Review also preserve and exercise the task's exact
`accessibility_matrix`, `navigation_matrix`, `content_matrix`,
`motion_contract`, and `usability_validation`. Medium/high-risk required human
review remains pending; automated tests and screenshots cannot substitute for
target-user usability. Select risk-based or pairwise combinations rather than
an unbounded Cartesian product.

**Visual validation loop**: implement → capture → critic/compare → difference
report → fix → recapture. Unavailable automated comparison remains
`pending-human-review`. Optional structured gate reports use
`ui-quality-gate-report.schema.json` under `.specify/design/gate-reports/`.

### Accept — human product verdict

Acceptance observes the frozen human scenarios derived from the exact
`interaction_matrix`, `editing_matrix`, `data_state_matrix`, `accessibility_matrix`,
`navigation_matrix`, `content_matrix`, `motion_contract`, and
`usability_validation`. It does not diagnose or rewrite the contracts. It
executes the risk-based frozen universe rather than an unbounded Cartesian
product and cannot mark medium/high-risk usability complete without the
required target-user human review.
