---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, artifacts, posters, or applications (examples include websites, landing pages, dashboards, React components, HTML/CSS layouts, or when styling/beautifying any web UI). Generates creative, polished code and UI design that avoids generic AI aesthetics.
license: Complete terms in LICENSE.txt
---

This skill guides creation of distinctive, production-grade frontend interfaces that avoid generic "AI slop" aesthetics. Implement real working code with exceptional attention to aesthetic details and creative choices.

The user provides frontend requirements: a component, page, application, or interface to build. They may include context about the purpose, audience, or technical constraints.

## Spec Kit Plus Design-Change Priority

In a Spec Kit Plus project, frontend-design is subordinate to any exact design
change already bound by the current feature or task. When such a binding
exists, inspect the selected
`.specify/design/changes/<UD-ID>/design-change.md` through targeted
`specify-runtime artifact show` calls, verify its registered SHA-256, and follow
that scoped contract for tokens, components, layout density, interaction
states, accessibility, motion, and evidence expectations. Never resolve
"latest" or use a root design document as adoption authority. If the bound
scope is composite, require independently bound consumer units rather than
blending parent and successor contracts.

When no design change is already bound, do not treat a missing
`.specify/design/index.json` as an automatic blocker. For a narrow
existing-pattern change, proceed from the user's request, supplied references,
and the live product surface; inherit the live visual language unless the user
explicitly requests a scoped redesign, and record the compact direction
contract and assumptions in the implementation closeout.

For substantive new UI with no applicable registered change, or for
high-visibility UI, a redesign or rebrand, or a core workflow experience,
recommend `sp-design`/`spx-design` before implementation, then wait for the
user's explicit invocation rather than treating visual style as an
implementation detail.

`sp-design` remains user-invoked. This passive implementation skill must not
load or invoke `sp-design`/`spx-design` itself.
If Design returns only a direction-confirmed sidecar, do not implement from it:
direction-confirmed is non-consumable, not approval, not register, and not a
Plan/Implement input. Implementation requires the later approve/register
receipt with the exact registered change ref, digest, and exported contract.

When the bound contract reports an approved
`.specify/design/changes/<UD-ID>/previews/round-NN.<html|png|jpg|jpeg|webp>#<direction-id>`, inspect
that exact change-level board through the design/artifact CLI before
implementation. Carry its component states, density, motion tokens, and
reduced-motion equivalent into the feature brief and real UI. A feature-level
`ui-target.html` can refine composition, but cannot silently replace the bound
preview or registered design change.

Do not invent unrelated bold aesthetics when a registered change governs the
affected scope or when the request is to implement an existing product surface.
Without a bound change, make visual choices explicit in the direction contract
only when the change qualifies for the narrow existing-pattern path above.

## Design Thinking

Before coding, state a compact direction contract:
- **Subject, audience, single job**: What is this product about, who is using it, and what one outcome must this surface make easy?
- **Surface and platform**: Distinguish landing, product workspace, hybrid, or existing-pattern maintenance from web, mobile, desktop, TUI, or CLI delivery.
- **Visual thesis**: What hierarchy, density, typography, color, and composition make the product recognizable?
- **Content thesis**: What real content or data makes the design credible, and where does it come from?
- **Interaction thesis**: What should feel immediate, guided, powerful, calm, or expressive?
- **Signature element**: What one visual or interaction choice should users remember?
- **Constraints**: Technical requirements (framework, performance, accessibility).
- **Risk**: Which choices are safe system decisions, and which creative risk is intentional? Record its gain and cost.

**CRITICAL**: Choose a clear conceptual direction and execute it with precision. Bold maximalism and refined minimalism both work - the key is intentionality, not intensity.

Then implement working code (HTML/CSS/JS, React, Vue, etc.) that is:
- Production-grade and functional
- Visually striking and memorable
- Cohesive with a clear aesthetic point-of-view
- Meticulously refined in every detail

## Frontend Aesthetics Guidelines

Focus on:
- **Typography**: Choose typography for the product, content, platform, language coverage, and performance. Distinctive display type can serve expressive surfaces; system or established product type can be correct for native-feeling tools and dense workspaces.
- **Color & Theme**: Commit to a cohesive aesthetic. Use CSS variables for consistency. Dominant colors with sharp accents outperform timid, evenly-distributed palettes.
- **Motion**: Use motion only when it clarifies change, hierarchy, feedback, or product character. Respect reduced motion and runtime cost.
- **Spatial Composition**: Choose expected or unexpected composition according to the user job. Preserve scanability and information density where the product depends on them.
- **Backgrounds & Visual Details**: Add atmosphere only when it supports the approved visual thesis; plain surfaces can be the deliberate choice.

Avoid generic AI-generated aesthetics: unexplained gradients, interchangeable card grids, placeholder copy, arbitrary font changes, and visual effects unrelated to product purpose. The problem is unsupported defaulting, not any single font, radius, layout, or color.

## Surface-aware anti-slop (subordinate to the bound design change)

When Spec Kit Plus has an applicable registered design change, obey that exact
ref/hash for its declared scope. When implementing without a governing approved change, or when recording a bounded existing-pattern
exception, apply surface-aware locks from
`templates/design-library/anti-slop-policy.md` (also installed under
`.specify/templates/design-library/anti-slop-policy.md`):

| Surface | Default lean | Avoid as default |
| --- | --- | --- |
| `landing` / marketing | higher variance, one signature | AI neon heroes, three equal feature cards, section-number eyebrows |
| `product-workspace` | denser, lower variance | marketing-hero theatrics, multi-accent rainbow chrome |
| `trust-public` | restrained motion, real DS when expected | experimental chaos, low-contrast decoration |
| `existing-pattern-maintenance` | inherit live language | inventing a parallel aesthetic family |

Do not promote landing-only bans into global constitution. Design workflows own
taste intake and approval; this skill does not authorize mutating a registered
design change or implementing production UI inside `sp-design`.

Interpret creatively and make unexpected choices that feel genuinely designed for the context. No design should be the same. Vary between light and dark themes, different fonts, different aesthetics. NEVER converge on common choices (Space Grotesk, for example) across generations.

**IMPORTANT**: Match implementation complexity to the aesthetic vision. Maximalist designs need elaborate code with extensive animations and effects. Minimalist or refined designs need restraint, precision, and careful attention to spacing, typography, and subtle details. Elegance comes from executing the vision well.

Use real content and owned or licensed imagery. Run the real entry point and
iterate through structure snapshot, visual capture, runtime diagnostics, and
visual comparison or human review. A passing test suite is not visual
acceptance.
