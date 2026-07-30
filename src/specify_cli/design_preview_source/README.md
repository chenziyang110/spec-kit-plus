# Design preview source

This directory is the upstream-only Jinja source of the self-contained
`templates/design-preview-template.html` compatibility artifact. It is packaged
for the Python renderer but is not copied into generated projects. Edit the
focused partial that owns the behavior, then run:

```text
uv run python scripts/render-design-preview-template.py
```

Use `--check` to verify that the generated HTML is synchronized. Product
directions and implementation handoff data belong in `manifest.json`; the HTML
artifact itself is generated and must not be hand-edited.

`templates/design-capability-profiles.json` is the deterministic cross-platform
registry. It owns the minimum capabilities, specimen kinds, states, units, and
presentation targets for Web, mobile, desktop, CLI, TUI, content-led, and no-UI
routing. `runtime.js` renders selected visual profiles into the HTML review
carrier; it must not reinterpret a terminal or native profile as a Web product.
