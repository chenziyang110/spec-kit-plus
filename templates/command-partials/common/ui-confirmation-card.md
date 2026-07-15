This is a conditional, independent UI confirmation card shared by Quick and
Debug. UI applicability includes any user-visible screen, component, layout,
navigation or interaction flow, visual state, responsive behavior, desktop or
mobile surface, accessibility presentation, TUI layout, or CLI presentation.
It does not require an external image.

Quick uses this card for an implementation proposal: the user confirms the
intended experience before implementation.
Debug uses this card for a target baseline: the reporter confirms what the
affected experience should be.
The card must not pre-approve a speculative fix or root-cause theory.

Render this card only when every row can be grounded in an approved project
design direction, an inspectable current product surface, or supplied source
material. `design_system.status: bootstrap` is structurally valid but is not an
approved visual direction. For a new or high-visibility direction, first route
to `sp-design`/`spx-design` and obtain an inspectable visual artifact. For
multi-surface or acceptance-heavy UI, route to `sp-specify`/`spx-specify`.
Do not render an incomplete UI Confirmation as if it were approval-ready.

Preserve original references rather than replacing them with prose. For each
reference, state its reference intent, such as preserve, adapt, or inspiration.
Name the real content and image sources that will be exercised; placeholder-only
content is not an adequate acceptance basis.

```markdown
## UI Confirmation

| Decision to confirm | UI proposal or target baseline |
| --- | --- |
| Confirmation purpose | [Quick implementation proposal, or Debug target baseline; name the affected UI surface] |
| User and primary job | [who uses this surface, the situation they are in, and the single job the experience must help them complete] |
| Design basis and source material | [approved DESIGN.md direction, inspectable current entry point, original references with reference intent, and real content or image sources] |
| Target experience | [visual, content, and interaction thesis plus the signature element or recognizable behavior to preserve or introduce] |
| Structure and visible change | [information hierarchy, layout, component placement, copy, and visible before-to-after change] |
| Interaction, states, and adaptation | [primary interaction, loading/empty/error/success/disabled/focus states, responsive or window adaptation, keyboard and accessibility behavior] |
| Design boundaries | Must preserve: [non-negotiable patterns or behavior]. May adapt: [implementation-flexible details]. Must not: [visual, content, or interaction regressions]. |
| Acceptance evidence | [real entry point, representative viewport/window and state matrix, structure snapshot, visual capture, runtime diagnostics, and visual comparison or explicit human review] |
```

Do not add a second reply prompt here. When this card follows a Quick or Debug
checkpoint, a single confirmation covers both the main checkpoint and this UI
decision; a correction may target only the UI rows.
