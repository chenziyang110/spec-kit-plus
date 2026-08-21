# Product Workspace

This domain covers the core working surface of a product: dashboards, editors, inspectors, operational consoles, and task-centric workspaces.

## Apply when

- The user is building an app where people do work, not just browse or buy.
- The surface includes tables, panels, editors, inspectors, filters, or multi-step workflows.
- Density, scannability, and repeat use matter more than pure visual flair.
- The design must support frequent keyboard use and fast state changes.

## Decisions to resolve

- What the main workspace is and what belongs in secondary panels.
- Which data should stay persistent versus collapse behind drawers or tabs.
- How dense the layout needs to be for real work.
- Which states are loading, empty, disabled, error, selected, or edited.
- Whether the page should optimize for single-task focus or multi-panel comparison.
- Which mature live or catalog component owns tables, overlays, editors,
  command surfaces, and virtualization without introducing competing systems.

## Image-primary augmentation

- Use image-primary for a workspace concept when the agent can inspect images.
- Show the main working state, not a marketing summary of the app.
- Include readable controls, panels, and data states that reflect real use.
- Generate separate detail images for dense tables, inspectors, or editing states if the full view is too small.

## HTML-primary augmentation

- Use HTML-primary when the agent cannot generate images or needs a live working demo.
- Start with the main working state and keep the rest progressively disclosed.
- Let the agent ask about data density, panel order, and control placement one decision at a time.
- Prefer truthful empty, loading, and error states over decorative filler.

## Quality gate

- Pass only when the workspace supports real work and still reads cleanly.
- Verify focus handling, keyboard paths, error recovery, and persistent state.
- Verify dense-state rendering, virtualization thresholds, interrupted async
  work, resize, and reduced-motion behavior at the real interaction scale.
- Reject layouts that prioritize visual novelty over operability.
- Escalate to the data-visualization, forms, accessibility, or design-system specialists when those are the main problem.
