---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, artifacts, posters, or applications (examples include websites, landing pages, dashboards, React components, HTML/CSS layouts, or when styling/beautifying any web UI). Generates creative, polished code and UI design that avoids generic AI aesthetics.
license: Complete terms in LICENSE.txt
---

This skill guides creation of distinctive, production-grade frontend interfaces that avoid generic "AI slop" aesthetics. Implement real working code with exceptional attention to aesthetic details and creative choices.

The user provides frontend requirements: a component, page, application, or interface to build. They may include context about the purpose, audience, or technical constraints.

## Spec Kit Plus Design-System Priority

In a Spec Kit Plus project, frontend-design is subordinate to DESIGN.md. Before
choosing a bold aesthetic direction, check whether `DESIGN.md` or an equivalent
committed design-system source governs the UI. Follow that source for tokens,
components, layout density, interaction states, accessibility, motion, and
evidence expectations.

`design_system.status: bootstrap` is not a governing product direction. Do not
let its generic starter palette or typography suppress a project-specific
solution. For substantive new UI, route through `sp-design`/`spx-design`; for a
narrow existing-pattern change, ground the implementation in the live product
surface and record the bounded design assumption.

Do not invent unrelated bold aesthetics when the project already has a design
system or when the request is to implement an existing product surface. If no
design system exists and the work is high-visibility, new product UI, a redesign
or rebrand, or a core workflow experience, recommend `sp-design` before
implementation rather than treating visual style as an implementation detail.

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

Interpret creatively and make unexpected choices that feel genuinely designed for the context. No design should be the same. Vary between light and dark themes, different fonts, different aesthetics. NEVER converge on common choices (Space Grotesk, for example) across generations.

**IMPORTANT**: Match implementation complexity to the aesthetic vision. Maximalist designs need elaborate code with extensive animations and effects. Minimalist or refined designs need restraint, precision, and careful attention to spacing, typography, and subtle details. Elegance comes from executing the vision well.

Use real content and owned or licensed imagery. Run the real entry point and
iterate through structure snapshot, visual capture, runtime diagnostics, and
visual comparison or human review. A passing test suite is not visual
acceptance.
