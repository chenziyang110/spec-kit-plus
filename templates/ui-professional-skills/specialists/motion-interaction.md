# Motion Interaction

This specialist skill focuses on transitions, feedback, gestures, micro-interactions, and animated state changes.

## Apply when

- The user explicitly asks for animation, motion polish, or interaction feel.
- Motion is required to explain state change, hierarchy, or feedback.
- The UI has gestures, drawers, expanding panels, or other animated controls.

## Decisions to resolve

- What motion is functional versus decorative.
- Which states need entrance, exit, and feedback motion.
- How much reduced-motion support is required.
- What the pacing should feel like: calm, premium, playful, or immediate.
- For Web UI, prefer the live component's transition contract and native/CSS
  motion; route to the catalog's motion specialist only for choreography that
  those foundations cannot express reliably.

## Image-primary augmentation

- Use image-primary when motion intent can be communicated through frames or concept boards.
- Use separate images for before, during, and after states when needed.
- Keep the prompt about motion tone and transition purpose, not just speed.

## HTML-primary augmentation

- Use HTML-primary when the motion must be experienced live.
- Prototype one meaningful motion at a time so the user can judge it.
- Ask about motion purpose before choosing easing, duration, or choreography.

## Quality gate

- Pass only when motion clarifies the interface instead of distracting from it.
- Verify reduced-motion behavior, timing, interruption/cancellation, focus and
  scroll continuity, and response under representative rendering load.
- Reject motion that feels decorative, slow, or repetitive without purpose.
