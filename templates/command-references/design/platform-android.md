# Android platform guidance

Load this reference for Android phones, tablets, foldables, desktop windows, or
ChromeOS-hosted app surfaces.

- Design from the current app-window size, not a named physical device. Cover
  compact, medium, and expanded width/height classes plus relevant posture and
  input changes.
- Adapt with reflow, reveal, pane changes, and navigation changes. Do not stretch
  a phone layout across a large window.
- Prefer Material/Compose adaptive components and canonical list-detail or
  supporting-pane patterns where they match the job.
- Do not lock orientation or assume the window cannot resize. Preserve focus,
  scroll, selection, drafts, and overlays while the window changes.
- Provide at least 48 dp touch targets, accessible labels/actions, readable
  contrast, font scaling, and alternatives to gesture-only operations.
- Demonstrate bottom navigation versus rail/drawer changes, reachable dialogs,
  keyboard/mouse behavior on large screens, and loading/error/offline recovery.

Primary references:

- https://developer.android.com/develop/adaptive-apps/guides/support-different-display-sizes
- https://developer.android.com/develop/adaptive-apps/guides/adaptive-dos-and-donts
- https://developer.android.com/design/ui/mobile/guides/foundations/accessibility
- https://developer.android.com/guide/topics/ui/accessibility/views/apps-views
