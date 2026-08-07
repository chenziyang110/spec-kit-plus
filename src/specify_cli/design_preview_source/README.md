# Design preview source (freeform board)

This directory is the upstream Jinja source for `templates/design-preview-template.html`.

## Contract

Chrome + three freeform direction canvases. Agents author creative layout/type/motion
inside each `#direction-*` canvas (taste-skill-style freeform). Machine governance
stays in `#design-preview-manifest` JSON and ready lint.

```text
uv run python scripts/render-design-preview-template.py
```
