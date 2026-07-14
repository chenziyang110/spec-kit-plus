# UI Brief

## Source Design System

- Root design system: DESIGN.md
- Design readiness: approved | narrow-existing-pattern-exception | blocked
- UI work type: existing-pattern | feature-extension | reference-implementation
- Relevant rules:
- Token and component constraints:

## Experience Core

- UI work type: existing-pattern | feature-extension | reference-implementation
- Surface type: landing | product-workspace | hybrid | existing-pattern-maintenance
- Platforms: web | mobile | desktop | tui | cli
- Subject:
- Audience:
- Single user job:

## Approved Direction

- Visual thesis:
- Content thesis:
- Interaction thesis:
- Signature element:
- Approved visual reference:
- Safe system choices:
- Deliberate creative risks, gain, and cost:

## Reference Inputs

- UI reference notes: ui-reference-notes.md | none
- Visual target: ui-target.html when present
- Original visual assets: stable paths when supplied
- Reference intents: one `ref + exact | preserve-structure | inspiration | extract-tokens | do-not-copy` record per source
- Ownership:

## Fidelity Contract

- Mode: approximate | high | inspiration
- Must match:
- May adapt:
- Must not copy:
- Human review condition:

## Screen Structure

- User job and experience intent:
- Recognizable visual or interaction signature:
- Real entry points:
- Layout:
- Regions:
- Navigation:
- Primary surface:

## Information Hierarchy

- First priority:
- Second priority:
- Supporting details:
- De-emphasized details:

## Real Content And Imagery

- Real content source and affected states:
- Image or illustration source, role, and responsive behavior:
- Missing asset recovery; do not substitute decorative placeholders silently:

## Components And States

- Components:
- Loading:
- Empty:
- Error:
- Selected:
- Disabled:
- Permission-limited:
- Success or failure feedback:

## Interactions

- Primary flow:
- Secondary flow:
- Keyboard and focus path:
- Feedback timing:

## Responsive Behavior

- Desktop or primary viewport:
- Mobile or narrow viewport:
- Overflow behavior:

## Accessibility And Keyboard Requirements

- Semantic structure:
- Focus visibility:
- Keyboard operation:
- Contrast intent:

## Must Preserve

- Layout structure:
- Information hierarchy:
- Component density:
- Visible data volume:
- Primary interactions:

## May Adapt

- Exact icons:
- Minor spacing:
- Copy:
- Framework-specific markup:

## Must Not

- Reinterpret the layout into a different pattern.
- Replace dense tables or workbench views with cards unless explicitly allowed.
- Add decorative gradients, unrelated hero sections, or visual treatment not present in the reference or brief.
- Copy third-party source code or protected brand expression.
- Treat ui-target.html as production source.

## Required Evidence

- Structure snapshot:
- Visual capture:
- Runtime diagnostics:
- Browser mapping: accessibility/DOM snapshot, viewport screenshot, console/runtime output
- Key state screenshots or captures:
- Keyboard and focus check:
- Browser console check for web UI:
- Accessibility check when interactive:
- Difference inventory against reference or prior surface:
- Accepted deviations and approver:
- Visual acceptance matrix: [entry point | viewport | state | expected result | evidence path]
- Human review requirement:

## Worker Contract

- Required references:
- Required packet fields:
- Required evidence kinds: `structure_snapshot`, `visual_capture`,
  `runtime_diagnostics`, `visual_comparison_or_human_review`
- Visual convergence loop: run real entry point -> capture representative
  viewport/state -> inspect against DESIGN.md/ui-brief/reference -> fix -> recapture
- Done condition: behavior checks and visual/interaction acceptance both pass
- Stop and reopen condition:
