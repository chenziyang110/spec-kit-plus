# Design preview source (iterative studio)

This directory is the upstream Jinja source for `templates/design-preview-template.html`.

## Contract

Chrome + one current concept canvas per immutable round. Agents replace the seed
with project-specific layout, type, motion, platform behavior, and real content;
feedback revises the same direction in a new round. Machine governance stays in
`#design-preview-manifest` JSON and ready lint.

```text
uv run python scripts/render-design-preview-template.py
```
