# Windows platform guidance

Load this reference for Windows desktop GUI surfaces.

- Prefer WinUI/Fluent controls and familiar Windows patterns before designing a
  custom control. Make hierarchy calm, coherent, and task-focused.
- Design the logical reading, tab, and focus order before polishing visual
  order. Support keyboard, mouse, touchpad, touch, pen, and high-precision input
  as applicable.
- Demonstrate resize behavior, compact and expanded window states, high-DPI
  rendering, system text scaling, high contrast/forced colors, and active versus
  inactive windows.
- Use approximately 40 x 40 effective-pixel touch targets as a baseline; enlarge
  or separate frequent, edge-adjacent, destructive, or hard-to-undo actions.
- Put persistent form labels above controls, group related fields with spacing,
  retain user input through validation, and expose a clear correction path.
- Use elevation and layering to communicate hierarchy, not as decoration.

Primary references:

- https://learn.microsoft.com/en-us/windows/apps/design/
- https://learn.microsoft.com/en-us/windows/apps/design/design-principles
- https://learn.microsoft.com/en-us/windows/apps/develop/user-interface
- https://learn.microsoft.com/en-us/windows/apps/develop/input/guidelines-for-targeting
- https://learn.microsoft.com/en-us/windows/apps/design/accessibility/accessibility-overview
