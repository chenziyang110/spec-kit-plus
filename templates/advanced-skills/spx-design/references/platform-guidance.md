# Platform guidance

Read only the sections for selected target platforms. Keep shared intent, but
do not force shared interaction mechanics.

## Web

Require semantic controls, keyboard operation, visible focus, 320 CSS px
reflow, adequate targets/spacing, zoom, reduced motion, labels and actionable
errors, long/localized content, and WAI-ARIA patterns for custom widgets.

## iOS and iPadOS

Design for touch, safe areas, Dynamic Type, VoiceOver, interruptions, window and
orientation changes, and visible alternatives to gestures. Prefer system
patterns; aim for 44 pt controls. Let iPad reveal or reflow content instead of
stretching an iPhone frame.

## macOS

Design resizable windows, menu commands, shortcuts, precision pointer input,
focus order, multiple-window and active/inactive behavior, platform density,
and optional user-customizable toolbars. Prefer native controls; demonstrate
compact and spacious window states.

## Windows

Prefer WinUI/Fluent controls. Cover logical tab/focus order, keyboard/mouse/
touchpad/touch/pen input, resize, high DPI, text scaling, high contrast, active
window state, and roughly 40 effective-pixel touch targets.

## Android

Drive adaptation from app-window size classes and posture. Use reflow, reveal,
pane, and navigation changes rather than stretching; do not lock orientation or
resizing. Prefer Material adaptive patterns, 48 dp targets, accessible actions,
font scaling, and keyboard/mouse support on large screens.

Official sources: Apple HIG, Microsoft Windows App Design, Android Adaptive
Apps/Accessibility, and W3C WCAG/APG. The installed Classic `sp-design`
references carry the exact URLs; Advanced keeps this
compact execution equivalent without depending on the Classic passive bundle.
