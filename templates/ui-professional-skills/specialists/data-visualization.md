# Data Visualization

This specialist skill focuses on charts, graphs, KPI displays, and visual explanations of structured data.

## Apply when

- The user needs trends, comparisons, distributions, or operational visibility.
- The layout depends on chart selection, axis semantics, or label hierarchy.
- The user cares about reading data quickly and correctly.

## Decisions to resolve

- What the visual is supposed to answer.
- Which metrics and comparisons are primary.
- Whether the chart is exploratory, explanatory, or operational.
- How to show uncertainty, grouping, or scale.
- Whether an inspected live chart system already governs the surface; otherwise
  use the Web catalog to select a mature chart foundation for the real data
  volume and interaction contract.

## Image-primary augmentation

- Use image-primary to explore chart composition, legend placement, and readability.
- Make sure values, labels, and units are legible in the generated view.
- Generate separate chart-state images if the density or state changes materially.

## HTML-primary augmentation

- Use HTML-primary when real data interaction matters.
- Keep axes, scales, and filters honest and easy to inspect.
- Ask only the questions that affect metric semantics or chart selection.

## Quality gate

- Pass only when the chart is legible and truthful.
- Verify labeling, contrast, non-visual alternatives, state coverage,
  representative-data performance, and responsive behavior.
- Reject decorative charts that do not communicate the data clearly.
