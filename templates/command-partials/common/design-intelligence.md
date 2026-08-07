# Design Intelligence (shared)

Horizontal UI/product design capability for every UI-bearing stage. Not a new
mainline command. Subordinate to approved root `DESIGN.md` plus immutable
preview/approval/handoff when present. Bootstrap `DESIGN.md` is never product
direction.

**UI is a design-system modeling problem, not a one-shot page generation
problem.** Do not jump from a screenshot or idea straight to production markup.
Establish system rules first, then implement against them.

Apply when work changes a user-visible screen, component, layout, navigation or
interaction flow, responsive behavior, visual state, desktop/mobile surface,
TUI layout, or CLI presentation—even without an external screenshot.

## Design Intelligence Engine (three capabilities)

| Capability | Role |
| --- | --- |
| **Taste Intelligence** | Personality/DNA, dials, anti-slop, signature |
| **Design System Reverse Engineering** | Evidence → UI System Model before implementation |
| **Visual Validation** | Real-entrypoint capture, comparison, pending-human-review |

`sp-design` / `spx-design` is the studio that materializes approved system truth;
other stages **consume** that truth through Design Intelligence hooks.

## Owners (do not invent parallel systems)

| Concern | Canonical owner |
| --- | --- |
| Design DNA / theses / signature | approved `DESIGN.md` + design brief |
| Global dials | `design_brief.dials` variance · motion · density (1-10) |
| Taste intake | `design_read`, aesthetic family, foundation strategy, redesign mode |
| Anti-slop locks | `design_brief.anti_slop_locks` + `design-library/anti-slop-policy.md` |
| UI System Model (tokens/components/states/responsive/behavior) | approved `DESIGN.md` + `.specify/design/design-system.json` |
| Evidence confidence on reverse-engineered claims | design brief / references / decision rows |
| Approval authority | `specify-runtime design approve` / export digests only |
| Feature composition | `ui-brief.md` → plan `ui_design_contract` → task `ui_contract` |
| Durable discussion carry | discussion Design Carry-Forward + handoff `design_context` |

Do **not** create a parallel root `.design/` tree. Use `.specify/design/**` and
root `DESIGN.md` only.

## Pipeline: Evidence → System → Implementation

For screenshot, existing UI, reference, or greenfield-with-references work:

1. **UI Evidence Analysis** — collect inspectable sources (screenshots, live
   routes, design exports, notes). Build a page/surface map. Tag every claim
   with an **evidence level** (below). Do not invent pixels as “measured.”
2. **UI System Model** — tokens, components, states, responsive rules, and
   behavior rules with confidence. Prefer modeling the system over cloning one
   page.
3. **Implementation** — generate UI only after the system (or a bounded existing-
   pattern exception) is clear; verify with visual validation.

Greenfield without references still needs taste intake + three-direction
preview before approval; reverse engineering applies when sources exist.

## Evidence Level (required on reverse-engineered claims)

Every token, layout rule, or component observation from screenshots/live UI
must carry one of:

| Level | Meaning |
| --- | --- |
| `measured` | Directly observed (devtools, source, exact asset, counted spacing) |
| `evidence-backed-inference` | Strong visual/code pattern evidence; state the reason |
| `assumption` | Temporary working guess; must not silently become approved truth |

Never promote `assumption` to implementation “must match” without user
confirmation or higher evidence. Record reason when level is not `measured`.

Example shape (in brief, references, or decision notes—not a second schema):

```text
color.primary: #0066ff | confidence: measured
font.family: Inter | confidence: assumption | reason: screenshot similarity only
```

## UI System Model

Model product UI as a system with four layers:

1. **Pixel layer** — color, type, spacing, radius, elevation, density values
2. **System layer** — components, variants, composition, reuse rules
3. **Behavior layer** — states, keyboard, focus, motion, feedback
4. **Engineering layer** — token owners, implementation bindings, platforms

Structured inventory (bind into DESIGN.md / design-system.json / ui-brief):

- **Tokens**: color, typography, spacing, radius, shadow/elevation, motion
- **Components**: Button, Input, Card, Table, navigation, domain-specific
- **States**: default, hover, focus, active, disabled, loading, empty, error,
  success, permission-limited
- **Responsive**: desktop / tablet / mobile (or content breakpoints)
- **Behavior**: keyboard paths, interaction timing, reduced-motion

Default “AI card grid” is not a system model.

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
`experience_commitments` / `design_system_requirements`.

### Design — reverse engineering + system studio

`sp-design` / `spx-design` owns create/refine/audit. On `synthesize` or live UI
refine: run Evidence → System before three-direction boards. Extract tokens,
components, states, and responsive rules with evidence levels. Export approved
truth only through design approve/export into `DESIGN.md` and
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
`pending-human-review`.

## Non-goals

- No `sp-design-intelligence` or taste top-level command
- No parallel root `.design/` product tree (use `.specify/design/**`)
- No bypass of `specify-runtime design approve` / export digests
- No treating passive anti-slop seeds as approved product direction
- No treating screenshot clone as a substitute for UI System Model