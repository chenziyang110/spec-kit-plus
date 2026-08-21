# Design System

This specialist skill focuses on tokens, components, variants, states, and shared UI rules.

## Apply when

- The user needs consistency across many screens or product surfaces.
- The interface is starting to repeat patterns that should become shared components.
- The work depends on tokens, states, accessibility notes, or reusable primitives.

## Decisions to resolve

- What belongs in tokens versus component APIs versus page-specific styling.
- Which component states are required.
- How strict the component contract should be.
- What parts of the design system can vary across platforms.
- For Web UI, read `web-component-selection.md` and resolve the reuse ladder
  from inspected live components to a compatible mature library before
  approving any new primitive.
- Choose one primary component system; add a headless or specialist library
  only for an exact uncovered behavior, not as a second source of defaults.

## Image-primary augmentation

- Use image-primary to inspect component consistency, spacing, and state differences.
- Show variant and state families together when possible.
- Use image inspection to catch visual drift before it spreads into the system.

## HTML-primary augmentation

- Use HTML-primary when the system must be demonstrated through working components.
- Keep component behavior stable and explicit.
- Ask only the questions that affect shared naming, state coverage, or reuse.

## Quality gate

- Pass only when the system is reusable, consistent, and easy to extend.
- Verify tokens, variants, states, and a11y notes.
- Reject one-off styling that should be encoded as a component rule.
- Reject custom dialogs, menus, selects, grids, editors, or drag behavior when
  a compatible mature component covers the contract and no justified gap is
  recorded.
