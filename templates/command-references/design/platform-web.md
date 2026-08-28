Trigger: When the approved surface includes browser-delivered UI.
Purpose: Apply web-specific responsive, interaction, accessibility, performance, and component-system guidance.
Preserved Contract: Inherit live product style by default and require real-entrypoint evidence for browser behavior and smoothness.

# Web platform guidance

Load this reference for browser-delivered GUI surfaces.

- Design for reflow without loss of information or function at 320 CSS pixels;
  avoid two-dimensional page scrolling except where the content inherently
  requires it.
- Use semantic HTML first. Use buttons for actions and links for navigation;
  give controls accessible names and preserve heading structure.
- Make every interaction keyboard-operable with a visible focus indicator.
  Dialogs, tabs, menus, comboboxes, and similar custom widgets must follow the
  corresponding WAI-ARIA Authoring Practices behavior.
- Give pointer targets adequate size or spacing, provide non-gesture
  alternatives, and never disable zoom or paste.
- Make labels persistent, associate validation feedback with fields, focus the
  first actionable error when appropriate, and preserve user input.
- Test long/short content, localization, zoom, forced colors, reduced motion,
  loading, empty, partial, error, and offline states at representative widths.

Primary references:

- https://www.w3.org/WAI/WCAG22/Understanding/reflow.html
- https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum
- https://www.w3.org/WAI/tutorials/forms/
- https://www.w3.org/WAI/ARIA/apg/
- https://github.com/vercel-labs/web-interface-guidelines/blob/main/command.md
