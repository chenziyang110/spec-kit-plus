Trigger: While authoring a project-specific HTML concept.
Purpose: Turn the confirmed design brief into a deliberate, responsive, and inspectable visual composition.
Preserved Contract: Avoid generic placeholder craft, preserve approved decisions, and prove the concept at its declared states and viewports.

# Professional HTML prototype craft

Use this reference when authoring the single concept inside a design-preview
round. The HTML is an inspectable design artifact, not production UI.

## Commit to one specific concept

- Ground every decision in the product's real subject, audience, content, and
  single job. Avoid placeholder copy and anonymous dashboard furniture.
- Write a compact concept plan first: 4-6 color tokens, deliberate type roles,
  layout logic, information density, interaction character, and one memorable
  signature element.
- Spend boldness in one justified place. Keep surrounding elements disciplined.
- Reject the agent's habitual defaults. If the same palette, hero, card grid,
  radius, type choice, or decorative effect could fit an unrelated product,
  revise it before authoring HTML.
- Preserve the chosen platform's native expectations. HTML is only the review
  carrier; a Windows, macOS, iOS, or Android concept must not masquerade as a
  generic responsive website.

## Author a complete reviewable surface

- Replace the entire seed. Set `data-prototype-status="authored"` only after the
  visible concept is complete.
- Mark at least one representative composition with `data-ui-surface` and mark
  meaningful controls/components with `data-ui-component` so the artifact is
  inspectable. Attributes supplement visible design; they never substitute for
  it.
- Show real hierarchy, primary task, navigation, representative data density,
  and applicable default/loading/empty/error/permission/offline states.
- Demonstrate input and feedback that matter for the platform: pointer,
  keyboard/focus, touch, pen, voice, or command input as applicable.
- Include the selected responsive/adaptive targets and a reduced-motion
  equivalent. Preserve focus, selection, scroll, drafts, and overlays across
  resize when those risks apply.
- Keep the file self-contained: no CDN, remote font, remote image, external
  script, network call, persistence, analytics, or production data.

## Visual quality floor

Before showing the user:

1. Open the real HTML in a browser at every representative target.
2. Capture and inspect it visually; do not infer appearance from source code.
3. Check hierarchy at a glance, typography, spacing rhythm, alignment, contrast,
   content credibility, platform authenticity, state coverage, overflow, focus,
   and reduced motion.
4. Remove decorative elements that do not serve the concept and repair any
   generic or unfinished region.
5. Recapture after repair. `preview-lint` proves structural readiness only; the
   inspected capture and user review decide visual satisfaction.

Source informing the craft rubric:

- https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md
