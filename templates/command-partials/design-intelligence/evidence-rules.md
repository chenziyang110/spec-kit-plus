## Pipeline: Evidence → System → Implementation

For screenshot, existing UI, reference, or greenfield-with-references work:

1. **UI Evidence Analysis** — collect inspectable sources (screenshots, live
   routes, design exports, notes). Build a page/surface map. Tag every claim
   with a Design Evidence object (below). Do not invent pixels as “measured.”
2. **UI System Model** — tokens, components, states, responsive rules, and
   behavior rules with confidence. Prefer modeling the system over cloning one
   page.
3. **Implementation** — generate UI only after the system (or a bounded existing-
   pattern exception) is clear; verify with visual validation.

Greenfield without references still needs taste intake + three-direction
preview before approval; reverse engineering applies when sources exist.

## Design Evidence v1 (required on reverse-engineered claims)

Machine-readable evidence uses Design Evidence v1:

- Schema: `templates/design-intelligence/schema/design-evidence.schema.json`
- Validate via `specify_cli.design_intelligence.validate_design_evidence`
- Canonical `type`: `measured` | `inferred` | `assumption`
- Prose alias `evidence-backed-inference` is accepted and maps to `inferred`
- Fields: `claim`, `type`, optional `source`, `source_gap`, `confidence`,
  `rationale`, `subject`, `id`

### Semantic rules (enforced)

- **non-measured** (`inferred` / `assumption`) **requires** non-empty
  `rationale`
- **inferred** requires `source` **or** explicit `source_gap` (no silent
  evidence-backed label without trace)
- Never promote `assumption` to implementation “must match” without user
  confirmation or higher evidence

Example object:

```json
{
  "subject": "color.primary",
  "claim": "Primary action color is #0066ff",
  "type": "measured",
  "source": "devtools computed style on /app",
  "confidence": 1.0,
  "rationale": null
}
```

```json
{
  "subject": "font.family",
  "claim": "Body font is Inter",
  "type": "inferred",
  "source": null,
  "source_gap": "screenshot only; no font file or CSS access",
  "confidence": "low",
  "rationale": "glyph shape similarity only"
}
```

Human brief lines may still use compact prose, but durable JSON must use the
schema. Prompt labels remain subordinate to the schema.

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
