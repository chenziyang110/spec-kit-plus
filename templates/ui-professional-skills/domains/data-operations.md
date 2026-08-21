# Data Operations

This domain covers analytics dashboards, observability, admin ops, reporting consoles, and other data-heavy operational surfaces.

## Apply when

- The main job is to read, compare, diagnose, or act on data.
- The surface uses charts, tables, filters, KPI cards, logs, or operational alerts.
- The user needs fast scanability and clear state semantics.
- The product must work for repeated expert use, not only first-time learning.

## Decisions to resolve

- What the canonical metric, table, or signal is.
- Which comparisons matter most: time, cohort, segment, severity, or source.
- Which states are healthy, warning, incident, stale, or empty.
- How much density the user needs before the UI becomes hard to read.
- Whether the surface is for monitoring, investigation, reporting, or action.

## Image-primary augmentation

- Use image-primary when the agent can inspect visuals and compare charts or table density.
- Keep the visual treatment honest to the data shape and do not fake numbers or trends.
- Use separate board images for dense tables, charts, and panel states if the main view gets unreadable.
- If the user cares about readability on a specific screen size, generate that size explicitly.

## HTML-primary augmentation

- Use HTML-primary when the surface needs real sorting, filtering, or interactive state changes.
- Keep data realistic, stable, and easy to inspect.
- Ask one question at a time about metrics, grouping, or severity semantics when the answer changes the layout.
- Prefer progressive disclosure for advanced filters and deep diagnostics.

## Quality gate

- Pass only when the data is legible, comparable, and stateful.
- Verify chart labels, table alignment, empty states, and responsive collapse.
- Reject decorative dashboards that do not help decision-making.
- Escalate to the design-system, accessibility, or forms specialists if the problem is really about component behavior or input flow.

