# General Interface

This domain covers broad UI work that does not yet belong to a narrower product shape or specialist skill.

## Apply when

- The request is a new interface, a redesign, or a cleanup, but the product shape is still broad or undecided.
- The user mentions web, desktop, mobile, or mixed-platform UI without naming a specialized surface.
- The task spans navigation, layout, interaction, copy, visual hierarchy, and responsiveness in one pass.
- The user wants the agent to ask questions before over-committing to a visual direction.

## Decisions to resolve

- Which platform or platforms matter first.
- Whether the work should feel compact, expressive, dense, or calm.
- What the single primary user job is.
- Which states need to be visible now versus hidden behind disclosure.
- Whether the surface should optimize for first-time understanding or repeated expert use.

## Image-primary augmentation

- Use image-primary when the agent can generate and inspect images.
- Ask one high-impact question, then show one current concept with a clear composition.
- Keep the concept anchored to real content and a single job; do not fill space with fake modules.
- Use image generation for visual direction, then use image inspection to refine hierarchy, spacing, and platform feel.

## HTML-primary augmentation

- Use HTML-primary when image generation is unavailable or the user explicitly wants a live prototype first.
- Keep the HTML prototype focused on one concept, one route, and one visible interaction path.
- Ask one question at a time when the answer changes the layout, platform, or information architecture.
- Prefer progressive disclosure in the UI itself instead of dumping all options onto the page.

## Quality gate

- Pass only when the surface reads as intentionally designed, not generic.
- Verify hierarchy, state coverage, keyboard access, and responsive behavior.
- Reject outputs that feel like a template with swapped colors.
- Escalate to a specialist skill if the request clearly centers on forms, charts, motion, a design system, accessibility, or conversational AI.
