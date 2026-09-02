Trigger: Only when the current concept round uses HTML as its primary review medium.
Purpose: Author a self-contained, inspectable HTML concept with the required manifest and review states.
Preserved Contract: Keep the concept review-only, dependency-free, immutable per round, and separate from production authority.

# Professional HTML prototype studio

Use this reference only for an `html-primary` round. Do not send this HTML
authoring contract to an image model: HTML authoring controls semantic HTML,
DOM structure, CSS behavior, responsive adaptation, and bounded executable
interaction rather than generating a static pixel composition.

## HTML authoring brief

Before editing the review carrier, write a compact implementation-neutral brief
covering:

- semantic HTML landmarks, content hierarchy, and the primary task;
- DOM/component anatomy and inspectable `data-ui-surface` /
  `data-ui-component` hooks;
- CSS tokens, typography roles, spacing rhythm, grid/layout logic, palette,
  shape language, and one signature element;
- responsive targets, container/window behavior, overflow, safe areas, and
  continuity of focus, selection, scroll, drafts, and overlays;
- interaction inputs, event/feedback order, keyboard/focus behavior, touch or
  pointer behavior, pending/cancel/repeat rules, and state transitions;
- representative content and applicable default, selected, loading, empty,
  error, permission, offline, success, and destructive states;
- accessibility semantics, contrast, target sizes, live announcements,
  reduced-motion equivalent, zoom/reflow, and forced-color behavior;
- self-contained constraints and the browser-capture acceptance matrix.

This is a visual review artifact, not production framework code. Do not ask the
user to choose React, SwiftUI, Compose, WinUI, or a CSS library merely to author
the concept.

## Author, run, and inspect

1. Run the design preview CLI from the shared manifest, then replace the entire
   seed with one complete current concept at `#direction-main`. Before rendering,
   freeze `html-primary`, `image_generation: unavailable`, the independently
   probed inspection/editing values, truthful inspection owner, and
   `html-authoring` strategy in `visual_collaboration`.
2. Use semantic HTML and modern native CSS deliberately. Keep the file
   self-contained: no framework, CDN, remote font, external runtime, network
   request, persistence, analytics, production data, or business logic.
3. Implement only bounded review interaction needed to expose navigation,
   component states, input/focus behavior, responsive modes, and motion/reduced
   motion. The artifact must not pretend to be the production app.
4. Run ready lint, open the real file at every representative target, take a
   browser capture, and inspect the rendered pixels rather than inferring the
   result from DOM/CSS source.
5. Repair hierarchy, typography, spacing, alignment, overflow, contrast,
   platform authenticity, state coverage, focus, and motion drift; then repeat
   browser capture.
6. If the session cannot inspect images/screenshots, provide the stable HTML
   deep link and make no visual-quality claim. The user owns visual critique,
   while structural lint still guards the machine contract.

Keep one concept per immutable round. Feedback revises the same direction in a
new file; it never creates three unrelated HTML alternatives and never mutates
a reviewed round. Do not generate three full boards; if direction ambiguity
remains, return to 2-3 textual choices in concept-calibration before authoring
another immutable review artifact.

Sources informing this authoring contract:

- https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md
- https://github.com/vercel-labs/web-interface-guidelines/blob/main/command.md
