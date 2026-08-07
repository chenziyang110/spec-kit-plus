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

When approved `DESIGN.md` exists, follow its tokens, components, motion, and
signature even if they conflict with default anti-slop locks. When only bootstrap
exists, route new or high-visibility direction through `sp-design`/`spx-design`.

## Anti-slop engine

Read surface-aware policy from `design-library/anti-slop-policy.md` (installed as
`.specify/templates/design-library/anti-slop-policy.md`). Defaults to avoid
unless the brief or approved design requires them:

- generic SaaS hero + three equal cards
- purple/blue AI gradient chrome without product grounding
- every control rounded the same with no hierarchy
- random or decorative motion
- empty decorative dashboard cards / placeholder metrics
- inventing a second design system beside approved `DESIGN.md`

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
- `anti_slop_locks` or surface default set
- `design_system_status` and whether `sp-design` is required next
- whether screenshots/live UI need **UI Evidence Analysis** before formal design

Persist into discussion Design Carry-Forward and, on handoff, into
`discussion_decision_digest.design_context` plus
`experience_commitments` / `design_system_requirements`. Prefer writing
machine-readable DesignContext under `.specify/design/context/` when durable.

### Design — reverse engineering + system studio

`sp-design` / `spx-design` owns create/refine/audit. On `synthesize` or live UI
refine: run Evidence → System before three-direction boards. Extract tokens,
components, states, and responsive rules as Design Evidence objects. Export
approved truth only through design approve/export into `DESIGN.md` and
`.specify/design/**`. Never implement production UI inside design.

### Specify — UI Requirements + acceptance / design DNA

For substantive UI work, specification must carry **UI Requirements** and
**UI Acceptance Criteria** (in `spec.md` Experience Requirements and/or
`ui-brief.md`):

- layout pattern and hierarchy; responsive targets
- tokens/components: use approved design-system (not ad-hoc)
- required states: loading, empty, error, success, disabled, focus (and hover
  when interactive)
- quality: no generic dashboard/template pattern; maintain design DNA and dials
- evidence: structure_snapshot, visual_capture, runtime_diagnostics, comparison
  or pending-human-review

Never treat bootstrap tokens as approved direction.

### Quick — UI Audit then design-before-code

When the change is UI-bearing, do not jump to code. Run **UI Audit** then the
**Quick Design Loop**:

1. **UI Audit** of current UI: hierarchy, spacing consistency, missing states,
   generic/card patterns, DNA drift (issue list, not code yet)
2. Analyze current UI against DESIGN.md / brief / live surface
3. Identify the design issue
4. Propose improvement (before → after) against DNA/dials/anti-slop/system model
5. Implement the smallest coherent change
6. Visual check at real entry points (capture → inspect → fix → recapture)

UI Confirmation still binds user-owned experience decisions before substantive
implementation.

### Debug — UI Debug Mode (layout / interaction / taste)

Classify UI symptoms into at least one issue class and record it in the session:

- **visual/layout**: spacing, alignment, overflow, responsive breakage
- **UX / interaction**: unclear action, weak feedback, confusing flow; missing
  or broken hover, focus, keyboard, loading, empty, error states
- **taste/generic-look**: template-like weight, no hierarchy, noise, anti-slop
  violation, DNA drift

Default-looking happy path is not enough—state matrix bugs count. Diagnosis
names issue, reason, and design-aware fix direction before coding.

### Implement / Review — system contract + visual validation loop

Before UI generation: query approved design + UI System Model (tokens,
components, states) + anti-slop + task `ui_contract`. Prefer visual hierarchy
from the contract over generic equal-weight card grids. Close only with
real-entrypoint evidence triad and visual comparison or explicit
`pending-human-review`. Review revalidates design-system, anti-slop, and state
coverage fidelity; it never invents a second approval authority.

**Visual validation loop**: implement → capture → critic/compare → difference
report → fix → recapture. Unavailable automated comparison remains
`pending-human-review`. Optional structured gate reports use
`ui-quality-gate-report.schema.json` under `.specify/design/gate-reports/`.
